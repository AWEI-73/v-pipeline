"""visual_audit.py — Node 12 visual evidence audit (P1-B).

Consumes keyframe-grid metadata and produces ``visual_audit.json``. Two layers:

* mechanical_findings — deterministic, no model (e.g. missing keyframes).
* model_review        — optional. Runs only when a reviewer callable is supplied;
                        provider/model lineage is read from the project's model
                        routes, never hardcoded. Mechanical-only mode works with
                        no VLM available.

VLM findings are review evidence; they cannot invent SPEC requirements.

Source: technique inspired by https://github.com/Hao0321/video-autopilot-kit
(MIT); reimplemented for this project's artifact contracts.
"""
import json
from pathlib import Path


def _mech_finding(check, level, message, *, fix_class="human", next_route=None):
    return {
        "check": check,
        "level": level,
        "message": message,
        "fix_class": fix_class,
        "next_route": next_route,
    }


def _resolve_lineage(model_routes, role):
    routes = (model_routes or {}).get("routes", {}) if isinstance(model_routes, dict) else {}
    route = routes.get(role) or {}
    return route.get("provider"), route.get("model")


def audit_visual(grid_meta, *, model_routes=None, reviewer=None,
                 role="verify_vlm", min_samples=1):
    """Build the visual-audit payload from keyframe-grid metadata.

    ``reviewer`` (if given) is called as ``reviewer(grid_meta)`` and must return a
    list of finding dicts (each may include ``level``/``cell``/``timestamp_sec``/
    ``note``). It is injected so the audit never assumes a particular VLM backend.
    """
    grid_meta = grid_meta or {}
    samples = grid_meta.get("samples") or []
    sample_count = grid_meta.get("sample_count", len(samples))

    mechanical_findings = []
    if not samples:
        mechanical_findings.append(_mech_finding(
            "keyframes_present", "fail",
            "no keyframes were extracted from the render candidate",
            fix_class="human", next_route="node_13_rerender",
        ))
    elif sample_count < int(min_samples):
        mechanical_findings.append(_mech_finding(
            "keyframe_coverage", "warn",
            f"only {sample_count} keyframe(s) extracted (expected >= {int(min_samples)})",
        ))

    model_review = None
    if reviewer is not None:
        provider, model = _resolve_lineage(model_routes, role)
        findings = list(reviewer(grid_meta) or [])
        model_review = {
            "provider": provider,
            "model": model,
            "findings": findings,
        }

    has_fail = any(f.get("level") == "fail" for f in mechanical_findings)
    if model_review:
        has_fail = has_fail or any(
            f.get("level") == "fail" for f in model_review["findings"])

    next_action = None
    if has_fail:
        if any(f["level"] == "fail" for f in mechanical_findings):
            next_action = "node_13_rerender"
        else:
            next_action = "director_or_curator"

    return {
        "artifact_role": "visual_audit",
        "version": 1,
        "pass": not has_fail,
        "grid": grid_meta.get("grid"),
        "grid_path": grid_meta.get("grid_path"),
        "samples": samples,
        "mechanical_findings": mechanical_findings,
        "model_review": model_review,
        "next_action": next_action,
    }


def write_visual_audit(grid_meta, out_path, **kwargs):
    """Audit ``grid_meta`` and write the stable ``visual_audit.json``."""
    result = audit_visual(grid_meta, **kwargs)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return {"ok": True, "visual_audit": str(out_path), "result": result}
