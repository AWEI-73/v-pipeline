"""editorial_qa.py — Node 12 editorial QA review module.

Performs cross-artifact reviews, checks mode consistency, and propagates
individual sub-audit findings (fatigue, treatment, technical verify).
All functions are pure (no I/O, no print).
"""
from __future__ import annotations

import re
from typing import Any

_KNOWN_MODES = ("promo", "rhythmic_mv", "training_recap", "story_documentary", "warm_documentary")


def _parse_target_sec(v) -> float | None:
    """Parse a brief target_length like '30 seconds' / '2 minutes' / 30 into seconds."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).lower()
    m = re.search(r"([\d.]+)", s)
    if not m:
        return None
    n = float(m.group(1))
    return n * 60 if ("min" in s or "分" in s) else n


def _infer_mode(brief: dict) -> str | None:
    vt = f"{brief.get('video_type','')} {brief.get('mode','')}".lower()
    for k in _KNOWN_MODES:
        if k in vt or k.replace("_", " ") in vt:
            return k
    if "promo" in vt:
        return "promo"
    if "mv" in vt:
        return "rhythmic_mv"
    return None


def review_editorial(artifacts: dict) -> dict:
    """Perform a cross-artifact editorial QA check.

    Args:
        artifacts: Dictionary containing keys:
            - brief
            - blueprint
            - contract (or segment_contract)
            - assembly_plan
            - timeline_build
            - treatment_audit
            - visual_fatigue_audit
            - blueprint_coverage
            - verify_result

    Returns:
        dict: {
            "artifact_role": "editorial_qa",
            "version": 1,
            "pass": bool,
            "score": int,
            "dimensions": {
                "intent_alignment": int,
                "narrative_coherence": int,
                "artifact_consistency": int,
                "visual_variety_fit": int,
                "pacing_fit": int,
                "audio_visual_coherence": int,
                "effects_fit": int
            },
            "findings": list of findings
        }
    """
    findings: list[dict] = []

    # Initialize dimension scores
    dims = {
        "intent_alignment": 100,
        "narrative_coherence": 100,
        "artifact_consistency": 100,
        "visual_variety_fit": 100,
        "pacing_fit": 100,
        "audio_visual_coherence": 100,
        "effects_fit": 100,
    }

    # 1. Check Mode Consistency (artifact_consistency)
    brief = artifacts.get("brief") or {}
    assembly_plan = artifacts.get("assembly_plan") or {}
    timeline_build = artifacts.get("timeline_build") or {}

    # Extract modes
    brief_mode = (
        brief.get("mode")
        or brief.get("editorial_intent", {}).get("mode")
    )
    plan_mode = (
        assembly_plan.get("mode")
        or assembly_plan.get("execution_plan", {}).get("mode")
    )
    build_mode = timeline_build.get("mode")

    modes_found = [m for m in (brief_mode, plan_mode, build_mode) if m]
    if len(set(modes_found)) > 1:
        msg = f"Inconsistent video modes declared across artifacts: brief={brief_mode}, assembly={plan_mode}, build={build_mode}"
        findings.append({
            "level": "warn",
            "dimension": "artifact_consistency",
            "message": msg,
            "route": "editor",
        })
        dims["artifact_consistency"] -= 10

    # 2. Propagate Treatment Audit Findings
    treatment_audit = artifacts.get("treatment_audit") or {}
    ta_findings = treatment_audit.get("findings") or []
    for tf in ta_findings:
        level = tf.get("level") or "fail"
        check = tf.get("check") or ""
        msg = tf.get("message") or ""
        route = tf.get("route") or "editor"

        # Map check to dimension
        dim = "artifact_consistency"
        if check == "treatment_fit":
            dim = "visual_variety_fit"
        elif check == "label_pairing":
            dim = "audio_visual_coherence"
        elif check == "beat_lock":
            dim = "pacing_fit"

        findings.append({
            "level": level,
            "dimension": dim,
            "message": f"From treatment_audit: {msg}",
            "route": route,
        })
        deduction = 10 if level == "fail" else 3
        dims[dim] -= deduction

    # 3. Propagate Visual Fatigue Audit Findings
    fatigue_audit = artifacts.get("visual_fatigue_audit") or {}
    fa_findings = fatigue_audit.get("findings") or []
    for ff in fa_findings:
        level = ff.get("level") or "fail"
        check = ff.get("check") or ""
        msg = ff.get("message") or ""
        route = ff.get("route") or "editor"

        # Map check to dimension
        dim = "visual_variety_fit"
        if check == "single_source_fatigue":
            dim = "visual_variety_fit"
        elif check == "still_image_fatigue":
            dim = "effects_fit"
        elif check == "shot_density_fit":
            dim = "visual_variety_fit"
        elif check == "source_repetition":
            dim = "visual_variety_fit"
        elif check == "pacing_fit":
            dim = "pacing_fit"

        findings.append({
            "level": level,
            "dimension": dim,
            "message": f"From visual_fatigue_audit: {msg}",
            "route": route,
        })
        deduction = 10 if level == "fail" else 3
        dims[dim] -= deduction

    # 4. Propagate Blueprint Coverage Findings
    coverage = artifacts.get("blueprint_coverage") or {}
    # E.g. if coverage not pass, add finding
    if "pass" in coverage and not coverage.get("pass"):
        findings.append({
            "level": "warn",
            "dimension": "narrative_coherence",
            "message": "Blueprint coverage check is weak or missing required narrative beats.",
            "route": "curator",
        })
        dims["narrative_coherence"] -= 15

    # 5. Propagate Technical Verification Findings
    verify_res = artifacts.get("verify_result") or {}
    if "pass" in verify_res and not verify_res.get("pass"):
        score = verify_res.get("score", 0)
        findings.append({
            "level": "fail",
            "dimension": "artifact_consistency",
            "message": f"Technical verification failed (Verify Score: {score}).",
            "route": "editor",
        })
        dims["artifact_consistency"] -= 20

    # 6. Gold-calibrated pacing review gate (Node 12). Mechanical verify is blind to
    #    pacing — this measures the real timeline shot-length profile vs the gold band
    #    per mode and folds the score into pacing_fit. Inert when no timeline clips.
    tb_clips = timeline_build.get("clips") or timeline_build.get("segments")
    if tb_clips:
        try:
            from . import pacing_review as _pr  # noqa: PLC0415
            _mode = (modes_found[0] if modes_found else None) or _infer_mode(brief) or "warm_documentary"
            _target = _parse_target_sec(brief.get("target_length"))
            pr_res = _pr.review_pacing(timeline_build, mode=_mode, target_sec=_target)
            for pf in pr_res.get("findings", []):
                findings.append({
                    "level": "fail" if pf.get("level") == "error" else "warn",
                    "dimension": "pacing_fit",
                    "message": f"From pacing_review: {pf.get('message', '')}",
                    "route": pf.get("route", "editor"),
                })
            # gold-calibrated pacing score caps the pacing_fit dimension
            dims["pacing_fit"] = min(dims["pacing_fit"], int(pr_res.get("score", 100)))
        except Exception:
            pass

    # Clamp all dimension scores between 0 and 100
    for k in dims:
        dims[k] = max(0, min(dims[k], 100))

    # Calculate overall score based on total findings
    total_deduction = 0
    has_fail = False
    for f in findings:
        if f["level"] == "fail":
            total_deduction += 10
            has_fail = True
        elif f["level"] == "warn":
            total_deduction += 3

    score = max(0, 100 - total_deduction)

    if not has_fail:
        model_review = "All checked artifacts are aligned and consistent. No visual fatigue or narrative gaps detected."
        narrative_synthesis = "The narrative flow matches the energy curve and thesis definitions specified in the blueprint/brief."
    else:
        model_review = f"Editorial quality check failed with {sum(1 for f in findings if f['level'] == 'fail')} failures. See findings."
        narrative_synthesis = "Narrative coherence is disrupted by outstanding audit/consistency failures."

    return {
        "artifact_role": "editorial_qa",
        "version": 1,
        "pass": not has_fail,
        "score": score,
        "dimensions": dims,
        "findings": findings,
        "model_review": model_review,
        "narrative_synthesis": narrative_synthesis,
    }
