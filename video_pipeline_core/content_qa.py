#!/usr/bin/env python3
"""content_qa.py — VLM 內容對題 VERIFY (describe + primary + related)"""
import argparse, base64, json, os, sys, urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")


def call_ollama_full(model, prompt, image_path, num_predict=10):
    import time
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    body = json.dumps({
        "model": model, "prompt": prompt, "images": [b64], "stream": False,
        "options": {"temperature": 0.1, "num_predict": num_predict},
    }).encode()
    # 3 attempts with backoff (2/4s) — tolerate transient ollama errors / model load.
    last_err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/generate", data=body,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=240) as r:
                return json.loads(r.read().decode()).get("response", "").strip()
        except Exception as e:
            last_err = e
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    raise last_err


def yn(text):
    t = text.strip(); tl = t.lower()
    if t[:1] in ("是", "對") or tl.startswith("yes"): return "yes"
    if t[:1] in ("否", "不", "沒") or tl.startswith("no"): return "no"
    if "部分" in t or "somewhat" in tl or "partial" in tl or "kind of" in tl or "有點" in t:
        return "somewhat"
    # negation must beat the substring it contains (不符合 contains 符合)
    if "不符" in t or "沒有" in t or "no" in tl: return "no"
    if "符合" in t or "相符" in t or "yes" in tl: return "yes"
    return "unknown"


def rubric_score(primary, related):
    """Map (primary, related) verdicts → 0-100 content-alignment score (D3).

    Graded by the strongest positive signal. Two refinements over the original
    100/60/40/10/30 mapping:
      * `somewhat` on the PRIMARY question (subject substantially present) now
        earns 75 instead of collapsing to the `related` tier.
      * Unparseable/`unknown` output is treated CONSERVATIVELY (15) instead of
        30 — the original ranked an ambiguous VLM answer *above* a clear `no`
        (10), rewarding noise. Ambiguity should never beat an explicit verdict.
    Gate threshold stays 60, so only yes/somewhat-primary/related-yes pass.
    """
    if primary == "yes":        return 100.0   # subject is the clear focus
    if primary == "somewhat":   return 75.0    # subject substantially present
    if related == "yes":        return 60.0    # on-topic context (passes gate)
    if related == "somewhat":   return 40.0    # loosely related → repick
    if related == "no":         return 10.0    # off-topic
    return 15.0                                 # unknown/unparseable → conservative


def score_segment(model, image_path, verify_desc, zh_title, verbose=False):
    """Score content alignment by matching the image against a Chinese VISUAL
    description (visual_desc, else narration), not the keyword query. A concrete
    visual spec is what 4b can actually judge; a CJK keyword in an English
    template — or a poetic narration — both mislead it (D5)."""
    desc = call_ollama_full(
        model, "Describe what is shown in this image in one concise English sentence.",
        image_path, num_predict=60).replace("\n", " ").strip()
    p_raw = call_ollama_full(
        model, f"這張圖的畫面，是否就是以下描述的主要內容？\n"
               f"畫面：「{verify_desc}」\n只回答 是 或 否。",
        image_path, num_predict=16).strip()
    primary = yn(p_raw)
    r_raw = call_ollama_full(
        model, f"這張圖適不適合當以下畫面描述的配圖？\n"
               f"畫面：「{verify_desc}」\n只回答 是、否、或 部分。",
        image_path, num_predict=16).strip()
    related = yn(r_raw)
    score = rubric_score(primary, related)
    return float(score), desc[:140], f"primary={primary}, related={related}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--model", default="qwen3-vl:4b-instruct")
    ap.add_argument("--weight", type=float, default=0.30)
    ap.add_argument("--no-strict", action="store_true", help="disable strict segment-level gate (rely on average score only)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    out = args.outdir
    with open(f"{out}/script.json", encoding="utf-8") as f: script = json.load(f)
    per_seg = []
    print(f"[content_qa] model={args.model}, {len(script)} segments", file=sys.stderr)
    for s in script:
        n = s["segment"]
        if s.get("kind") == "title" or s.get("source") == "local":
            reason = ("title_sequence" if s.get("kind") == "title"
                      else "local_material")
            per_seg.append({"segment": n, "title": s.get("title", ""),
                            "score": None, "reason": reason}); continue
        img = f"{out}/final_frame_{n}.jpg"
        if not os.path.exists(img):
            per_seg.append({"segment": n, "score": None, "reason": "frame_missing"}); continue
        score, desc, reason = score_segment(
            args.model, img, s.get("visual_desc") or s.get("text", ""), s["title"], args.verbose)
        per_seg.append({
            "segment": n, "title": s["title"], "score": score,
            "image_desc": desc, "reason": reason,
            "query": s["search_query"], "narration": s["text"][:60],
        })
        flag = " ⚠️" if score < 60 else ""
        print(f"  seg{n} [{s['title']}] → {score:.0f}{flag}  ({desc[:60]})", file=sys.stderr)

    scores = [p["score"] for p in per_seg if p["score"] is not None]
    avg = sum(scores) / len(scores) if scores else 0
    mn = min(scores) if scores else 0
    low_segs = [p for p in per_seg if p["score"] is not None and p["score"] < 60]

    with open(f"{out}/content_qa.json", "w", encoding="utf-8") as f:
        json.dump({
            "model": args.model, "weight": args.weight,
            "summary": {"avg_score": round(avg, 1), "min_score": round(mn, 1),
                        "low_count": len(low_segs), "total_segments": len(per_seg)},
            "segments": per_seg,
        }, f, ensure_ascii=False, indent=2)

    qa_path = f"{out}/qa_report.json"
    if os.path.exists(qa_path):
        with open(qa_path, encoding="utf-8") as f: qa = json.load(f)
        note_parts = [f"avg={avg:.1f}, min={mn:.1f}"]
        if low_segs:
            low_str = ', '.join('seg{0}={1:.0f}'.format(p['segment'], p['score']) for p in low_segs)
            note_parts.append(f"low: {low_str}")
        new_dim = {
            "score": round(avg, 1), "weight": args.weight,
            "note": " | ".join(note_parts),
            "fix_target": "curator" if low_segs else None,
            "issues": [{"segment": p["segment"], "score": p["score"],
                        "image_desc": p.get("image_desc", "")} for p in low_segs],
        }
        qa["dimensions"]["content_alignment"] = new_dim
        other_keys = [k for k in qa["dimensions"] if k != "content_alignment"]
        if "_original_weights" not in qa:
            qa["_original_weights"] = {k: qa["dimensions"][k].get("weight", 0) for k in other_keys}
        remaining = 1.0 - args.weight
        orig_sum = sum(qa["_original_weights"][k] for k in other_keys)
        for k in other_keys:
            qa["dimensions"][k]["weight"] = round(qa["_original_weights"][k] / orig_sum * remaining, 3)
        total = sum(d["score"] * d["weight"] for d in qa["dimensions"].values())
        qa["score"] = round(total, 1)
        qa["pass"] = qa["score"] >= qa.get("threshold", 80)
        if not args.no_strict and low_segs:
            qa["pass"] = False
        qa["issues"] = []
        for k, d in qa["dimensions"].items():
            is_issue = d["score"] < 80 or (k == "content_alignment" and not args.no_strict and low_segs)
            if is_issue:
                qa["issues"].append({"dimension": k, "score": d["score"],
                                     "detail": d.get("note", ""),
                                     "fix_target": d.get("fix_target")})
        with open(qa_path, "w", encoding="utf-8") as f: json.dump(qa, f, ensure_ascii=False, indent=2)
        print(f"\n[content_qa] qa_report updated: score={qa['score']:.1f} pass={qa['pass']} "
              f"(content_alignment={avg:.1f})", file=sys.stderr)

    print(json.dumps({
        "status": "ok", "model": args.model,
        "avg_score": round(avg, 1), "min_score": round(mn, 1),
        "low_segments": [p["segment"] for p in low_segs],
        "total_segments": len(per_seg),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
