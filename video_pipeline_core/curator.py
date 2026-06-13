"""curator.py — 小編(素材入庫/理解/比對),從 video_tools 解耦。
ingest-meta / caption-meta / material-map / match-mv + classify_asset 等。
共用原語取自 vt_core,避免循環匯入。"""
import os
import sys
import json
import subprocess
from .vt_core import FFMPEG, FFPROBE, run, ToolError  # noqa: F401

PHOTO_EXTS = {'.jpg', '.jpeg', '.png', '.heic', '.heif'}
VIDEO_EXTS = {'.mp4', '.mov', '.m4v', '.avi', '.mkv'}


def classify_asset(width, height, duration_sec=None, is_photo=False,
                   target_orientation="horizontal", min_short_side=1080,
                   min_clip_sec=3.0):
    """純函式：素材入庫漏斗 Stage 1（機械判斷,零 agent/VLM）。

    通用引擎 + 每案政策：參數帶結訓預設(橫式 / ≥1080 / ≥3s),做別的片型
    （直式 shorts、其他案子）只要傳不同政策值,引擎不動。

    回傳 {kind, orientation, res_short, usable, reasons}:
      kind         : photo / short(<5s) / clip(5-30s) / long(30-120s) / verylong(>120s)
      orientation  : horizontal / vertical / square / unknown
      usable=False 的 reasons：方向不符 / 解析度過低 / 影片過短。
    （square 視為相容任一方向,不擋。）"""
    w, h = int(width or 0), int(height or 0)
    orientation = "unknown"
    if w and h:
        orientation = "vertical" if h > w else ("square" if h == w else "horizontal")
    short = min(w, h) if (w and h) else 0

    if is_photo or duration_sec is None:
        kind = "photo" if is_photo else "video"
    elif duration_sec < 5:
        kind = "short"
    elif duration_sec < 30:
        kind = "clip"
    elif duration_sec < 120:
        kind = "long"
    else:
        kind = "verylong"

    reasons = []
    if (target_orientation and orientation not in ("unknown", "square")
            and orientation != target_orientation):
        reasons.append(f"orientation={orientation}!={target_orientation}")
    if short and short < min_short_side:
        reasons.append(f"res_short={short}<{min_short_side}")
    if (not is_photo) and duration_sec is not None and duration_sec < min_clip_sec:
        reasons.append(f"too_short={round(duration_sec, 1)}s<{min_clip_sec}")
    return {"kind": kind, "orientation": orientation, "res_short": short,
            "usable": len(reasons) == 0, "reasons": reasons}


def _parse_res(resolution_str):
    """'1920x1080' → (1920, 1080);失敗回 (0,0)。"""
    try:
        w, h = str(resolution_str).lower().split("x")
        return int(w), int(h)
    except Exception:
        return 0, 0


def _classify_entry(entry):
    """從 ingest entry(含 metadata.resolution/duration_sec)算 classify_asset 結果。"""
    meta = entry.get("metadata") or {}
    w, h = _parse_res(meta.get("resolution"))
    return classify_asset(w, h, duration_sec=meta.get("duration_sec"),
                          is_photo=(entry.get("type") == "photo"))


def caption_asset(model, image_path):
    """(I/O) 用本地 VLM 描述圖片「實際拍到什麼」（中文、具體）。小編語意歸類的核心。"""
    from . import content_qa  # noqa: PLC0415 — lazy
    return content_qa.call_ollama_full(
        model, "用一句話描述這張圖實際拍到什麼？要具體（人/動作/場景），用中文。",
        image_path, num_predict=64).replace("\n", " ").strip()


def format_material_map(files):
    """純函式:material_db 的 files → 人看得懂的素材地圖(依資料夾分群)。"""
    from collections import defaultdict
    groups = defaultdict(list)
    for e in files:
        tags = e.get("tags_from_path") or []
        groups["/".join(tags) if tags else "(root)"].append(e)
    lines = []
    for g in sorted(groups):
        items = groups[g]
        usable = sum(1 for e in items if (e.get("classify") or {}).get("usable"))
        lines.append(f"## {g}  （{len(items)} 檔，{usable} 可用）")
        for e in items[:8]:
            c = e.get("classify") or {}
            cap = e.get("vlm_caption") or "（未 caption）"
            flag = "" if c.get("usable") else f"  ⚠️{','.join(c.get('reasons', []))}"
            lines.append(f"  - [{e.get('type')}/{c.get('kind')}] "
                         f"{os.path.basename(e.get('path', ''))}: {cap}{flag}")
        if len(items) > 8:
            lines.append(f"  …（+{len(items) - 8} 檔）")
    return "\n".join(lines)


def _exif_data(image_path: str) -> dict:
    """讀照片 EXIF（PIL + pillow-heif），失敗回空 dict"""
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            pass

        with Image.open(image_path) as img:
            width, height = img.size
            data = {"resolution": f"{width}x{height}"}
            exif = img._getexif() if hasattr(img, '_getexif') else None
            if exif:
                ex = {TAGS.get(k, k): v for k, v in exif.items()}
                data["datetime"] = str(ex.get('DateTime', '')).strip() or None
                make = str(ex.get('Make', '')).strip()
                model = str(ex.get('Model', '')).strip()
                data["camera"] = f"{make} {model}".strip() or None
                gps = ex.get('GPSInfo')
                if gps: data["gps_info"] = "present"
            return data
    except Exception as e:
        return {"error": str(e)[:100]}


def _convert_heic(src: str, dst: str) -> bool:
    """HEIC → JPG。優先用 Pillow + pillow-heif，回傳成功與否"""
    try:
        from PIL import Image
        from pillow_heif import register_heif_opener
        register_heif_opener()
        with Image.open(src) as img:
            img.convert('RGB').save(dst, 'JPEG', quality=92)
        return True
    except Exception:
        return False


def _video_info(path: str) -> dict:
    """ffprobe 抓影片 metadata"""
    try:
        res = subprocess.run([
            FFPROBE, '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration,codec_name,r_frame_rate',
            '-show_entries', 'format=duration,bit_rate',
            '-of', 'json', path
        ], capture_output=True, text=True, timeout=30)
        info = json.loads(res.stdout)
        out = {}
        if info.get('streams'):
            s = info['streams'][0]
            out["resolution"] = f"{s.get('width')}x{s.get('height')}"
            out["codec"] = s.get('codec_name')
            out["framerate"] = s.get('r_frame_rate')
        fmt = info.get('format', {})
        if fmt.get('duration'):
            out["duration_sec"] = round(float(fmt['duration']), 2)
        return out
    except Exception as e:
        return {"error": str(e)[:100]}


def _extract_keyframes(video_path: str, out_dir: str, file_id: str,
                       count: int = 3) -> list:
    """從影片均勻抽 N 張 keyframe，回傳 [{timestamp_sec, image_path}]"""
    info = _video_info(video_path)
    dur = info.get('duration_sec') or 0
    if dur <= 0:
        return []
    keyframes = []
    for i in range(count):
        # 抽 20%、50%、80% 位置
        t = dur * (0.2 + 0.3 * i)
        kf_path = os.path.join(out_dir, f"{file_id}_kf{i+1}.jpg")
        if not os.path.exists(kf_path):
            res = subprocess.run([
                FFMPEG, '-y', '-ss', str(t), '-i', video_path,
                '-frames:v', '1', '-q:v', '3', '-vf', 'scale=512:-1',
                kf_path
            ], capture_output=True, timeout=30)
            if res.returncode != 0:
                continue
        if os.path.exists(kf_path):
            keyframes.append({
                "timestamp_sec": round(t, 2),
                "image_path": kf_path,
            })
    return keyframes


def _ingest_work_dirs(src, out_db, work_dir=None):
    """純函式:決定衍生檔(.converted / .keyframes)放哪。
    **不污染來源**:預設放在輸出 db 的目錄(或顯式 --work-dir);
    只有當 db 就寫在 src 裡(沒給 --out)才落在 src。回 (cnv_dir, kf_dir)。"""
    base = work_dir or os.path.dirname(os.path.abspath(out_db)) or src
    return os.path.join(base, ".converted"), os.path.join(base, ".keyframes")


def cmd_ingest_meta(args):
    """掃本地素材庫，提取 metadata + 抽 keyframe → materials_db.json"""
    src = args.src
    if not os.path.isdir(src):
        raise ToolError(f"source not found: {src}")

    out_db = args.out or os.path.join(src, "materials_db.json")
    # 衍生檔放輸出目錄/--work-dir,不寫進來源素材夾(避免污染唯讀素材)
    cnv_dir, kf_dir = _ingest_work_dirs(src, out_db, getattr(args, "work_dir", None))
    os.makedirs(cnv_dir, exist_ok=True)
    os.makedirs(kf_dir, exist_ok=True)

    files = []
    fid_counter = 0
    skipped = []

    for root, _, fnames in sorted(os.walk(src)):
        rel = os.path.relpath(root, src)
        if rel != "." and (rel.startswith('.') or f"{os.sep}." in rel):
            continue
        tags = [p for p in rel.split(os.sep) if p and p != '.']

        for f in sorted(fnames):
            ext = os.path.splitext(f)[1].lower()
            full = os.path.join(root, f)

            if ext in PHOTO_EXTS:
                fid_counter += 1
                fid = f"f{fid_counter:04d}"
                display = full
                converted = None
                if ext in {'.heic', '.heif'}:
                    converted = os.path.join(cnv_dir, f"{fid}.jpg")
                    if not os.path.exists(converted):
                        if not _convert_heic(full, converted):
                            skipped.append({"path": full, "reason": "heic convert failed"})
                            continue
                    display = converted

                exif = _exif_data(display)
                entry = {
                    "id": fid,
                    "path": full,
                    "display_path": display,
                    "type": "photo",
                    "format": ext.lstrip('.'),
                    "converted_to": converted,
                    "tags_from_path": tags,
                    "size_bytes": os.path.getsize(full),
                    "metadata": exif,
                    "vision_score": None,
                }
                files.append(entry)

            elif ext in VIDEO_EXTS:
                fid_counter += 1
                fid = f"f{fid_counter:04d}"
                info = _video_info(full)
                kfs = _extract_keyframes(full, kf_dir, fid, count=3)
                entry = {
                    "id": fid,
                    "path": full,
                    "type": "video",
                    "format": ext.lstrip('.'),
                    "tags_from_path": tags,
                    "size_bytes": os.path.getsize(full),
                    "metadata": info,
                    "keyframes": kfs,
                    "vision_score": None,
                }
                files.append(entry)

    for entry in files:                       # 機械歸類(橫/直/解析度/時長 + usable)
        entry["classify"] = _classify_entry(entry)

    from datetime import datetime
    db = {
        "ingested_at": datetime.now().isoformat(),
        "source_dir": os.path.abspath(src),
        "total": len(files),
        "skipped": skipped,
        "files": files,
    }

    with open(out_db, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    photos = sum(1 for x in files if x['type'] == 'photo')
    videos = sum(1 for x in files if x['type'] == 'video')
    total_keyframes = sum(len(x.get('keyframes', [])) for x in files if x['type'] == 'video')

    print(json.dumps({
        "status": "ok",
        "db": out_db,
        "total": len(files),
        "photos": photos,
        "videos": videos,
        "keyframes_extracted": total_keyframes,
        "heic_converted": sum(1 for x in files if x.get('converted_to')),
        "skipped": len(skipped),
    }, ensure_ascii=False))


def _cjk_bigrams(s):
    s = "".join(ch for ch in (s or "") if not ch.isspace())
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _caption_match_score(desc, caption):
    """需求 desc × 供給 caption 的便宜中文比對:desc 字 bigram 有多少出現在 caption。0~1。"""
    a, b = _cjk_bigrams(desc), _cjk_bigrams(caption)
    return round(len(a & b) / len(a), 3) if a else 0.0


def match_script_to_material(segments, files, restrict_to_hint=True, montage_picks=5):
    """純函式:需求(段 visual_desc/material_hint/must_include) × 供給(material_db files:
    vlm_caption/classify/path) → 每段配 clip + 缺口。**用既有 caption 文字比對,不跑 VLM**。
    回傳 {assignments:[{segment, picks, gap, must_include}], gaps:[...]}。"""
    usable = [f for f in files if (f.get("classify") or {}).get("usable")]
    assignments, gaps = [], []
    for s in segments:
        n = s.get("segment")
        desc = s.get("visual_desc", "")
        hint = (s.get("material_hint") or "").replace("/", os.sep)
        must = s.get("must_include")
        scored = []
        for f in usable:
            path = f.get("path", "")
            hint_hit = bool(hint) and hint in path
            if hint and restrict_to_hint and not hint_hit:
                continue
            score = _caption_match_score(desc, f.get("vlm_caption")) + (0.5 if hint_hit else 0)
            # A zero-score local candidate is not evidence. Keeping it would
            # silently bypass GAP and let unrelated material represent a real
            # course/event (the 2026-06-13 live-line incident).
            if score <= 0:
                continue
            scored.append({"path": path, "score": round(score, 3),
                           "caption": f.get("vlm_caption"), "hint_hit": hint_hit})
        scored.sort(key=lambda x: -x["score"])
        # montage/快剪段挑多支(否則 1 clip 被切成多刀);其餘 1 支
        is_montage = s.get("layout") == "montage" or s.get("pace") == "fast"
        picks = scored[:montage_picks] if is_montage else scored[:1]
        gap = len(picks) == 0
        if gap:
            g = {"segment": n, "reason": f"沒有可用素材對應「{desc[:18]}」(hint={s.get('material_hint')})",
                 "must_include": bool(must)}
            gaps.append(g)
        assignments.append({"segment": n, "visual_desc": desc,
                            "material_hint": s.get("material_hint"), "must_include": must,
                            "picks": picks, "gap": gap})
    return {"assignments": assignments, "gaps": gaps}


def build_material_coverage(segments, files):
    """Build the canonical Node 2 coverage artifact from existing match evidence."""
    matched = match_script_to_material(segments, files)
    missing = [gap for gap in matched["gaps"] if gap.get("must_include")]
    weak = [gap for gap in matched["gaps"] if not gap.get("must_include")]
    return {
        "artifact_role": "material_coverage_map",
        "version": 1,
        "assignments": matched["assignments"],
        "gaps": matched["gaps"],
        "covered": [item for item in matched["assignments"] if not item.get("gap")],
        "weak": weak,
        "missing": missing,
        "blocking": missing,
    }


def cmd_match_mv(args):
    """需求×供給比對:MV 劇本 × materials_db → clip_list(每段配 clip + 缺口)。"""
    with open(args.script, encoding="utf-8") as f:
        script = json.load(f)
    with open(args.db, encoding="utf-8") as f:
        db = json.load(f)
    segs = script.get("segments", []) if isinstance(script, dict) else script
    res = match_script_to_material(segs, db.get("files", []))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    matched = sum(1 for a in res["assignments"] if not a["gap"])
    print(json.dumps({"status": "ok", "segments": len(res["assignments"]),
                      "matched": matched, "gaps": len(res["gaps"]),
                      "must_include_gaps": sum(1 for g in res["gaps"] if g.get("must_include"))},
                     ensure_ascii=False))
    for a in res["assignments"]:
        tag = "GAP" if a["gap"] else f"{a['picks'][0]['score']}"
        cap = (a["picks"][0]["caption"][:30] if a["picks"] else "—")
        print(f"  seg{a['segment']} [{tag}] {a['visual_desc'][:16]} → {cap}", file=sys.stderr)


def cmd_caption_meta(args):
    """小編語意歸類:對 materials_db 每個素材跑本地 VLM,填 vlm_caption(實際內容)。
    分離的慢步驟(ingest 機械快、caption 慢),只跑沒 caption 的。"""
    with open(args.db, encoding="utf-8") as f:
        db = json.load(f)
    review_dir = getattr(args, "visual_review_dir", None)
    if review_dir:
        pending = [entry for entry in db.get("files", []) if not entry.get("vlm_caption")]
        if not pending:
            print(json.dumps({
                "status": "ok", "db": args.db, "captioned": 0,
            }, ensure_ascii=False))
            return
        os.makedirs(review_dir, exist_ok=True)
        request_path = os.path.join(review_dir, "material_visual_review_request.json")
        verdict_path = os.path.join(review_dir, "material_visual_review_verdict.json")
        if os.path.exists(verdict_path):
            with open(verdict_path, encoding="utf-8-sig") as f:
                verdict = json.load(f)
            before = sum(bool(entry.get("vlm_caption")) for entry in db.get("files", []))
            apply_material_review_verdict(db, verdict)
            after = sum(bool(entry.get("vlm_caption")) for entry in db.get("files", []))
            with open(args.db, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
            print(json.dumps({
                "status": "ok", "db": args.db, "captioned": after - before,
                "verdict": verdict_path,
            }, ensure_ascii=False))
            return
        request = build_material_review_request(db, review_dir)
        with open(request_path, "w", encoding="utf-8") as f:
            json.dump(request, f, ensure_ascii=False, indent=2)
        print(json.dumps({
            "status": "awaiting_review", "db": args.db, "request": request_path,
            "verdict": verdict_path, "next_action": "await_material_visual_review",
            "assets": len(request.get("assets") or []),
        }, ensure_ascii=False))
        return
    model = args.model or "qwen3-vl:4b-instruct"
    limit = args.limit or 0
    done = 0
    for e in db.get("files", []):
        if e.get("vlm_caption"):
            continue
        if e.get("type") == "photo":
            img = e.get("display_path") or e.get("path")
        else:
            kfs = e.get("keyframes") or []
            img = kfs[0].get("image_path") if kfs else None
        if not img or not os.path.exists(img):
            continue
        try:
            e["vlm_caption"] = caption_asset(model, img)
            done += 1
        except Exception as ex:
            e["vlm_caption"] = None
            e["caption_error"] = str(ex)[:80]
        if limit and done >= limit:
            break
    with open(args.db, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print(json.dumps({"status": "ok", "db": args.db, "captioned": done}, ensure_ascii=False))


def build_material_review_request(db, out_dir, _gridfn=None):
    """Build deterministic visual evidence for agent-authored material captions."""
    if _gridfn is None:
        from .keyframe_grid import generate_keyframe_grid as _gridfn
    out_dir = os.path.join(str(out_dir), "material_review")
    assets = []
    template = []
    for entry in (db or {}).get("files", []):
        asset_id = entry.get("id")
        if not asset_id or entry.get("vlm_caption"):
            continue
        if entry.get("type") == "video":
            montage = os.path.join(out_dir, f"{asset_id}.jpg")
            evidence = _gridfn(entry.get("path"), montage, sample_count=12)
            montage = evidence.get("grid_path") or montage
            samples = evidence.get("samples") or []
        else:
            montage = entry.get("display_path") or entry.get("path")
            samples = []
        assets.append({
            "id": asset_id,
            "type": entry.get("type"),
            "source": entry.get("path"),
            "montage": montage,
            "samples": samples,
        })
        template.append({"id": asset_id, "caption": None, "notes": None})
    return {
        "artifact_role": "material_visual_review_request",
        "version": 1,
        "next_action": "await_material_visual_review",
        "assets": assets,
        "verdict_template": {"assets": template},
    }


def apply_material_review_verdict(db, verdict):
    """Apply agent-authored captions while preserving explicit lineage."""
    indexed = {}
    for item in (verdict or {}).get("assets", []):
        asset_id = item.get("id")
        caption = item.get("caption")
        if not asset_id or not isinstance(caption, str) or not caption.strip():
            raise ValueError("material visual review verdict requires id and non-empty caption")
        indexed[asset_id] = item
    pending_ids = {
        entry.get("id") for entry in (db or {}).get("files", [])
        if entry.get("id") and not entry.get("vlm_caption")
    }
    missing = sorted(pending_ids - set(indexed))
    if missing:
        raise ValueError(f"material visual review verdict missing pending asset(s): {missing}")
    for entry in (db or {}).get("files", []):
        item = indexed.get(entry.get("id"))
        if not item:
            continue
        entry["vlm_caption"] = item["caption"].strip()
        entry["caption_source"] = "agent_visual_review"
        entry["caption_notes"] = item.get("notes")
    return db


def cmd_material_map(args):
    """讀 materials_db → 人看得懂的素材地圖(依資料夾分群 + 可用/caption)。"""
    with open(args.db, encoding="utf-8") as f:
        db = json.load(f)
    if getattr(args, "maps_dir", None):
        from .material_map import write_material_maps
        maps = write_material_maps(db, args.maps_dir)
        update_db = getattr(args, "update_db", None)
        if update_db:
            with open(update_db, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
        print(json.dumps({
            "ok": True,
            "maps_dir": args.maps_dir,
            "maps": len(maps),
            "materials_db": update_db,
        }, ensure_ascii=False, indent=2))
        return
    txt = format_material_map(db.get("files", []))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(txt)
    print(txt)
