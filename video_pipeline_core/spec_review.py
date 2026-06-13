"""spec_review.py — pre-BUILD whole-SPEC review gate (roadmap C0).

Schema validation says the contract is *well-formed*; this gate says the project
is *executable as intended*. It cross-checks brief + contract against the
battle-tested failure modes from real runs (ai-video soul-v3/v5, stock_story_e2e
convergence) BEFORE runtime enters BUILD, and emits a standing report artifact:

    spec_review.json
      ready_for_build : true | false
      blocking[]      : must be fixed at SPEC (route revise:director)
      warnings[]      : will degrade quality / disable guards, but can run
      next_action     : "revise:director(spec_review)" | None

Rules (each one is a real incident, not speculation):
  B1 pacing_conflict      — 1-material treatment vs multi-shot pacing (soul-v3 monotony)
  B2 must_include × stock — stock_first refuses must_include → segment silently
                            dropped → script_coverage fail (convergence dry-run)
  B3 subtitle:auto silent — ASR on a no-speech segment → subtitle_accuracy 0
                            (convergence dry-run)
  W1 CG-bait query        — hologram/abstract/data-stream queries return dark 3D
                            renders that fight warm tones (ai-video v3)
  W2 missing target_length— duration cap can't engage; music length becomes the
                            runtime (soul-v5: 45s film stretched to 123s)
  W3 implicit mode trap   — video_type "mv" infers rhythmic_mv (max_hold 6s) even
                            when contract pacing is documentary [4,8] (soul-v5)
  W4 soul w/o design      — editing_intent declared but no editorial_design.json:
                            visual_fatigue/editorial_qa silently skip (soul-v3)

Perfunctory-SPEC detection (anti-laziness; soul-v3/v5 were copy-paste contracts:
4/5 identical content_patterns, 5/5 identical pacing, identical seq_grammar —
and the facet gate passed them because it only counts field PRESENCE):
  W5 uniform_pacing       — every segment declares the exact same pacing: no
                            rhythm design (bookends should hold longer than montage)
  W6 weak/dup visual_desc — too short to give VLM/stock matching anything, or
                            duplicated across segments (same picture twice)
  W7 trivial_reasons      — reasons are design rationale, not format filler:
                            mostly-identical or placeholder-length reasons
  W8 duplicate_search_query — same query on multiple segments → same stock clip
  B4 perfunctory_spec     — >=3 of the above co-occur on a >=4-segment film:
                            this is a template fill, not a design → blocking

Pure (no I/O, no print).
"""
from __future__ import annotations

# Stock libraries return dark, abstract 3D renders for these; see skills/curator.md
_CG_BAIT_TOKENS = ("hologram", "abstract", "data stream", "digital network",
                   "futuristic background", "cyberspace")


def _parse_target_sec(v):
    from .editorial_qa import _parse_target_sec as _p  # noqa: PLC0415
    return _p(v)


def _segments(contract):
    if isinstance(contract, dict):
        return contract.get("segments") or []
    return contract or []


def _is_stock_first(contract):
    if not isinstance(contract, dict):
        return False
    cfg = contract.get("run_config") or {}
    return (contract.get("material_source_mode") == "stock_first"
            or cfg.get("material_source_mode") == "stock_first")


def _seg_id(seg, idx):
    return seg.get("segment", idx + 1)


def review_spec(contract, brief=None, *, has_editorial_design=False, supply_review=None):
    """Cross-check the whole project SPEC for executability. Returns the
    spec_review payload (see module docstring)."""
    brief = brief or {}
    segs = _segments(contract)
    blocking: list[dict] = []
    warnings: list[dict] = []

    target_sec = _parse_target_sec(brief.get("target_length"))
    stock_first = _is_stock_first(contract)

    # --- B6: requested script duration exceeds evidenced material supply -----
    supply_by_segment = {
        item.get("segment"): item for item in (supply_review or {}).get("segments") or []
    }
    for idx, seg in enumerate(segs):
        sid = _seg_id(seg, idx)
        supply = supply_by_segment.get(sid)
        if not supply:
            continue
        requested_sec = float(
            seg.get("requested_duration_sec")
            or seg.get("duration_sec")
            or supply.get("requested_duration_sec")
            or 0
        )
        max_sec = float(supply.get("max_honest_duration_sec") or 0)
        if requested_sec > max_sec:
            blocking.append({
                "rule": "script_overreach",
                "tier": 1,
                "segment": sid,
                "requested_duration_sec": requested_sec,
                "max_honest_duration_sec": max_sec,
                "message": f"seg{sid}: script promises {requested_sec:g}s but material "
                           f"supply supports at most {max_sec:g}s",
                "fix": "shorten/merge the segment, await material, or request a reshoot",
            })

    # --- B5: requested capability is not executable by this runtime ---------
    from .capability_manifest import build_capability_manifest, supported_capabilities
    manifest = build_capability_manifest()
    supported = supported_capabilities(manifest)
    unsupported = set(manifest.get("unsupported") or [])
    requested = list(contract.get("required_capabilities") or []) if isinstance(contract, dict) else []
    for seg in segs:
        requested.extend(seg.get("required_capabilities") or [])
    for capability in sorted(set(requested)):
        if capability in unsupported or capability not in supported:
            blocking.append({
                "rule": "out_of_capability",
                "tier": 1,
                "capability": capability,
                "message": f"SPEC requires unsupported capability '{capability}'",
                "fix": "remove/downgrade the requirement or implement and expose it in capability_manifest",
            })

    # --- W2: no target_length → music length becomes the runtime -------------
    if not target_sec:
        warnings.append({
            "rule": "missing_target_length",
            "message": "brief.target_length missing/unparsable — the timeline will "
                       "be as long as the music (soul-v5: 45s film became 123s)",
            "fix": "set brief.target_length (e.g. '45 seconds')",
        })

    # --- W3: implicit mode trap ----------------------------------------------
    vt = str(brief.get("video_type") or "").lower()
    if brief and not brief.get("mode") and "mv" in vt:
        def _doc_paced(seg):
            p = (seg.get("pacing") or {}).get("preferred_shot_sec")
            return isinstance(p, (list, tuple)) and len(p) >= 2 and float(p[1]) >= 6
        if any(_doc_paced(seg) for seg in segs):
            warnings.append({
                "rule": "implicit_mode_trap",
                "message": "video_type 'mv' infers pacing mode rhythmic_mv (max_hold 6s) "
                           "but contract pacing looks documentary (preferred_shot_sec "
                           "upper >= 6s) — holds will fail the pacing gate",
                "fix": "declare brief.mode explicitly (e.g. 'warm_documentary')",
            })

    # --- W4: soul declared but no editorial_design ----------------------------
    soul_declared = any(
        seg.get("editing_intent") or seg.get("material_treatment") or seg.get("sequence_grammar")
        for seg in segs
    )
    if soul_declared and not has_editorial_design:
        warnings.append({
            "rule": "soul_without_editorial_design",
            "message": "contract declares editing intent but no editorial_design.json — "
                       "editing_policy stays inactive, visual_fatigue_audit and "
                       "editorial_qa will silently skip (soul-v3)",
            "fix": "provide editorial_design.json (blueprint-interview output)",
        })

    # Per-segment weights for pacing-conflict budgets (mirrors contract_adapter)
    from .contract_adapter import _seg_weight  # noqa: PLC0415
    weights = [_seg_weight(seg.get("core") or {}, seg.get("editing_grammar") or {})
               for seg in segs]
    wsum = sum(weights) or 1.0

    for idx, seg in enumerate(segs):
        sid = _seg_id(seg, idx)
        mat = seg.get("material_fit") or {}
        aud = seg.get("audio") or {}
        txt = seg.get("text_layer")
        src = seg.get("source")

        # --- B1: pacing conflict (only computable when target known) ---------
        if target_sec and (seg.get("editing_intent") or seg.get("material_treatment")):
            from . import material_treatment  # noqa: PLC0415
            seg_view = {
                "editing_intent": seg.get("editing_intent") or {},
                "material_treatment": seg.get("material_treatment") or {},
                "core": seg.get("core") or {},
                "pacing": seg.get("pacing"),
                "duration_sec": round(target_sec * weights[idx] / wsum, 3),
            }
            resolved = material_treatment.resolve_treatment(seg_view, beat_count=8)
            if resolved.get("pacing_conflict"):
                blocking.append({
                    "rule": "pacing_conflict", "segment": sid,
                    "message": f"seg{sid}: {resolved['reason']}",
                    "fix": "change editing_intent.content_pattern (multi-shot sections "
                           "use process/enumeration/action/bridge) or fix pacing",
                })

        # --- B2: must_include on a stock-bound segment ------------------------
        if stock_first and mat.get("must_include") and src not in ("local", "generated"):
            blocking.append({
                "rule": "must_include_stock_conflict", "segment": sid,
                "message": f"seg{sid}: must_include '{mat.get('must_include')}' on a "
                           "stock-bound segment — stock_first refuses must_include, the "
                           "segment gets NO source and is silently dropped",
                "fix": "remove must_include (conceptual segment) or set source "
                       "local/generated with the real material",
            })

        # --- B3: subtitle:auto on a segment with no real speech ---------------
        sub_mode = txt.get("subtitle") if isinstance(txt, dict) else None
        if sub_mode == "auto" and aud.get("role") not in ("duck", "diegetic"):
            blocking.append({
                "rule": "subtitle_auto_no_speech", "segment": sid,
                "message": f"seg{sid}: text_layer.subtitle='auto' but audio.role is "
                           f"'{aud.get('role')}' — ASR runs on the segment's original "
                           "audio; silent/stock segments score subtitle_accuracy 0",
                "fix": "only use subtitle:'auto' on real-speech segments "
                       "(audio.role duck/diegetic), else give explicit text or none",
            })

        # --- W1: CG-bait search query -----------------------------------------
        q = str(mat.get("search_query") or "").lower()
        bait = [t for t in _CG_BAIT_TOKENS if t in q]
        if bait:
            warnings.append({
                "rule": "cg_bait_query", "segment": sid,
                "message": f"seg{sid}: search_query contains {bait} — stock libraries "
                           "return dark 3D renders for these (ai-video v3 black-on-black)",
                "fix": "name a visible physical scene + tone words (bright/warm/sunlit); "
                       "concepts with no physical proxy go to the generated route",
            })

    # --- Perfunctory-SPEC detection (W5-W8, B4) -------------------------------
    laziness_signals = []
    n = len(segs)

    if n >= 4:
        # W5: identical pacing on every segment = no rhythm design
        import json as _json  # noqa: PLC0415
        pacings = [seg.get("pacing") for seg in segs]
        if all(p for p in pacings) and len({_json.dumps(p, sort_keys=True) for p in pacings}) == 1:
            laziness_signals.append("uniform_pacing")
            warnings.append({
                "rule": "uniform_pacing",
                "message": f"all {n} segments declare the exact same pacing — bookends "
                           "should hold longer than montage middles; identical pacing "
                           "everywhere is template fill, not rhythm design (soul-v5)",
                "fix": "differentiate pacing by section_role (opening/closing hold "
                       "longer; develop/climax cut faster)",
            })

    descs = [str((seg.get("material_fit") or {}).get("visual_desc") or "").strip()
             for seg in segs]
    weak = [(_seg_id(seg, i), d) for i, (seg, d) in enumerate(zip(segs, descs)) if 0 < len(d) < 6]
    dups = {d for d in descs if d and descs.count(d) > 1}
    if weak or dups:
        laziness_signals.append("weak_or_dup_visual_desc")
        detail = []
        if weak:
            detail.append(f"too-short visual_desc on seg {[sid for sid, _ in weak]}")
        if dups:
            detail.append(f"duplicated visual_desc {sorted(dups)[:3]}")
        warnings.append({
            "rule": "weak_or_dup_visual_desc",
            "message": "; ".join(detail) + " — VLM scoring and stock matching are only "
                       "as good as the description; a 4-char or copy-pasted desc "
                       "starves them",
            "fix": "write a concrete, segment-specific visual description "
                   "(subject + action + place + light/mood)",
        })

    reasons = []
    for seg in segs:
        for key in ("material_fit", "audio", "visual_style", "editing_grammar"):
            r = (seg.get(key) or {}).get("reason") if isinstance(seg.get(key), dict) else None
            if r is not None:
                reasons.append(str(r).strip())
    if reasons:
        trivial = [r for r in reasons if len(r) < 4]
        if (len(trivial) >= len(reasons) / 2) or (len(reasons) >= 4 and len(set(reasons)) == 1):
            laziness_signals.append("trivial_reasons")
            warnings.append({
                "rule": "trivial_reasons",
                "message": f"{len(trivial)}/{len(reasons)} facet reasons are placeholder-"
                           "length or all identical — reasons are the design rationale "
                           "the reviewer/route relies on, not format filler",
                "fix": "state WHY for each facet choice (what the segment needs, "
                       "what was rejected)",
            })

    queries = [str((seg.get("material_fit") or {}).get("search_query") or "").strip().lower()
               for seg in segs]
    dup_q = {q for q in queries if q and queries.count(q) > 1}
    if dup_q:
        laziness_signals.append("duplicate_search_query")
        warnings.append({
            "rule": "duplicate_search_query",
            "message": f"duplicated search_query across segments: {sorted(dup_q)[:3]} — "
                       "the same stock clip will fill multiple segments (monotony + "
                       "broll repeats)",
            "fix": "give each segment its own concrete query (or route to local/"
                   "generated material)",
        })

    if n >= 4 and len(laziness_signals) >= 3:
        blocking.append({
            "rule": "perfunctory_spec",
            "message": f"{len(laziness_signals)} laziness signals co-occur "
                       f"({', '.join(laziness_signals)}) on a {n}-segment film — this "
                       "SPEC is a template fill, not a design; downstream gates can't "
                       "rescue a hollow contract",
            "fix": "differentiate per segment: content_pattern by section_role, pacing "
                   "by rhythm, concrete visual_desc/search_query, real reasons",
        })

    from .creative_exception import acknowledge, matching_exception  # noqa: PLC0415
    seg_by_id = {_seg_id(seg, idx): seg for idx, seg in enumerate(segs)}
    remaining_blocking = []
    for finding in blocking:
        exception = matching_exception(
            finding["rule"],
            seg_by_id.get(finding.get("segment")),
        )
        if exception:
            warnings.append(acknowledge(finding, exception))
        else:
            remaining_blocking.append(finding)
    blocking = remaining_blocking

    tier_by_rule = {
        "out_of_capability": 1,
        "script_overreach": 1,
        "must_include_stock_conflict": 1,
        "subtitle_auto_no_speech": 1,
        "pacing_conflict": 2,
        "perfunctory_spec": 2,
        "missing_target_length": 3,
    }
    for finding in blocking + warnings:
        finding.setdefault("tier", tier_by_rule.get(finding.get("rule"), 2))

    ready = not blocking
    return {
        "artifact_role": "spec_review",
        "version": 1,
        "ready_for_build": ready,
        "blocking": blocking,
        "warnings": warnings,
        "next_action": None if ready else "revise:director(spec_review)",
        "stats": {"segments": len(segs), "blocking": len(blocking),
                  "warnings": len(warnings), "stock_first": stock_first,
                  "target_sec": target_sec, "laziness_signals": laziness_signals,
                  "required_capabilities": sorted(set(requested))},
    }
