"""blueprint.py — Narrative Blueprint gate (WHY layer).

Pure functions for the top-of-pipeline narrative spine described in
docs/narrative-blueprint-spec.md:

  blueprint.json  thesis + ordered beats[] (stable ids)  ->  the film's soul handle
  two-way trace gate:
    forward : every segment.core.blueprint_ref must name a real beat id
    backward: every beat id must be realized by >= 1 segment (else BLOCKING)

No I/O except the thin write_* helper; everything else is a pure function so it can
be unit-tested and consumed by Node 11/12 without side effects.
"""
import json
from pathlib import Path


def _segments(contract):
    if isinstance(contract, dict):
        return contract.get("segments") or []
    if isinstance(contract, list):
        return contract
    return []


def _seg_id(seg, i):
    return seg.get("segment", i + 1) if isinstance(seg, dict) else i + 1


def _refs(seg):
    """Normalize core.blueprint_ref to a list of non-empty string beat ids."""
    core = (seg.get("core") or {}) if isinstance(seg, dict) else {}
    raw = core.get("blueprint_ref")
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        return []
    return [str(r).strip() for r in raw if str(r).strip()]


def validate_blueprint(bp):
    """Validate blueprint.json shape. Returns {ok, errors, warnings}.

    Requires a non-empty thesis and a non-empty beats[] where each beat has a
    unique, non-empty id. role/summary are recommended (warn), not required.
    """
    errors, warnings = [], []
    if not isinstance(bp, dict):
        return {"ok": False, "errors": ["blueprint 必須是 JSON 物件"], "warnings": []}

    if not str(bp.get("thesis") or "").strip():
        errors.append("blueprint.thesis 必填(一句話:這支片在講什麼)")

    beats = bp.get("beats")
    if not isinstance(beats, list) or not beats:
        errors.append("blueprint.beats 必填且至少 1 個 beat")
        beats = []

    seen = set()
    for i, beat in enumerate(beats):
        if not isinstance(beat, dict):
            errors.append(f"beats[{i}] 必須是物件")
            continue
        bid = str(beat.get("id") or "").strip()
        if not bid:
            errors.append(f"beats[{i}] 缺 id(beat 需要穩定 anchor id)")
            continue
        if bid in seen:
            errors.append(f"beats id 重複:{bid}")
        seen.add(bid)
        if not str(beat.get("summary") or "").strip():
            warnings.append(f"beat {bid} 建議補 summary(一句話描述)")
        if not str(beat.get("role") or "").strip():
            warnings.append(f"beat {bid} 建議補 role(setup/develop/turn/resolve)")

    if not str(bp.get("thesis_anchor") or bp.get("intended_feeling") or "").strip():
        warnings.append("blueprint 建議補 intended_feeling(整片要留下的感覺)")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def beat_coverage(blueprint, contract):
    """Two-way trace gate between blueprint beats and contract segments.

    Pure. Returns:
      {
        artifact_role, version, pass,
        beat_ids, realized, dropped,          # backward direction
        orphan_segments, invalid_refs,        # forward direction
        findings: [{check, level, message, route}]
      }

    dropped beat   -> blocking (level=error): the film lost a promised beat.
    invalid_ref    -> blocking (level=error): a segment cites a non-existent beat.
    orphan segment -> warn: a segment serves no beat (often scope creep).
    """
    beats = blueprint.get("beats") if isinstance(blueprint, dict) else None
    beat_ids = [str(b.get("id")).strip() for b in (beats or [])
                if isinstance(b, dict) and str(b.get("id") or "").strip()]
    beat_id_set = set(beat_ids)

    realized = set()
    orphan_segments = []
    invalid_refs = []  # [(segment_id, bad_ref)]
    findings = []

    segs = _segments(contract)
    for i, seg in enumerate(segs):
        sid = _seg_id(seg, i)
        refs = _refs(seg)
        if not refs:
            orphan_segments.append(sid)
            findings.append({
                "check": "orphan_segment", "level": "warn", "segment": sid,
                "message": f"段 {sid} 沒有 core.blueprint_ref,不服務任何 beat",
                "route": "revise:director",
            })
            continue
        for ref in refs:
            if ref in beat_id_set:
                realized.add(ref)
            else:
                invalid_refs.append((sid, ref))
                findings.append({
                    "check": "invalid_ref", "level": "error", "segment": sid,
                    "message": f"段 {sid} 的 blueprint_ref='{ref}' 不存在於 blueprint.beats",
                    "route": "revise:director",
                })

    dropped = [bid for bid in beat_ids if bid not in realized]
    for bid in dropped:
        findings.append({
            "check": "dropped_beat", "level": "error", "beat": bid,
            "message": f"beat '{bid}' 沒有任何段實現 — 影片掉了一個敘事轉折",
            "route": "node_3_contract",
        })

    ok = not dropped and not invalid_refs
    return {
        "artifact_role": "blueprint_coverage",
        "version": 1,
        "pass": ok,
        "beat_ids": beat_ids,
        "realized": sorted(realized),
        "dropped": dropped,
        "orphan_segments": orphan_segments,
        "invalid_refs": [{"segment": s, "ref": r} for s, r in invalid_refs],
        "findings": findings,
        "next_action": None if ok else "revise:director",
    }


def write_blueprint_coverage(blueprint, contract, out_path):
    """Compute beat_coverage and write blueprint_coverage.json. Returns the result."""
    result = beat_coverage(blueprint, contract)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


def check_run(run_dir):
    """Runtime gate: if a run has blueprint.json + segment_contract.json, compute
    coverage and write blueprint_coverage.json; otherwise return None (inert).

    Returns the coverage dict (or a validate-failure dict) so the orchestrator can
    block on a dropped/invalid beat. A run with no blueprint is unaffected.
    """
    rd = Path(run_dir)
    bp_path = rd / "blueprint.json"
    contract_path = rd / "segment_contract.json"
    if not bp_path.exists() or not contract_path.exists():
        return None
    try:
        with bp_path.open(encoding="utf-8") as f:
            bp = json.load(f)
        with contract_path.open(encoding="utf-8") as f:
            contract = json.load(f)
    except Exception:
        return None

    v = validate_blueprint(bp)
    if not v["ok"]:
        result = {
            "artifact_role": "blueprint_coverage", "version": 1, "pass": False,
            "stage": "validate_blueprint",
            "findings": [{"check": "invalid_blueprint", "level": "error",
                          "message": e, "route": "revise:director"} for e in v["errors"]],
            "next_action": "revise:director",
        }
    else:
        result = beat_coverage(bp, contract)

    out = rd / "blueprint_coverage.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result
