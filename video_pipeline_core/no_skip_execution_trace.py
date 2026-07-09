"""No-skip execution trace checks for preview/rehearsal candidates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


TRACE_CLASSIFICATIONS = {
    "pipeline_tool_generated",
    "run_local_worker_generated",
    "copied_from_prior",
    "missing_owner_tool",
    "unknown",
}

CANONICAL_GATE_ARTIFACTS = (
    "visual_selection_gate.json",
    "title_effect_lifecycle_qa.json",
    "rendered_product_qa.json",
    "final_artifact_check.json",
    "delivery_gate.json",
    "pipeline_home.json",
)

PIPELINE_TOOLS = {
    "story_script_package": [
        "tools/film_canon_route.py",
        "tools/write_product_route_review_decision.py",
    ],
    "visual_selection": ["tools/visual_selection_gate.py"],
    "effect_factory": ["tools/title_effect_lifecycle_qa.py"],
    "soundtrack_audio_handoff": [
        "tools/soundtrack_flow_acceptance.py",
        "tools/pipeline_home.py",
    ],
    "render_build": [
        "tools/material_first_render.py",
        "tools/workbench_draft_rerender.py",
    ],
    "rendered_product_qa": ["tools/rendered_product_qa.py"],
    "delivery_gate": ["tools/write_delivery_gate_report.py"],
}


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _trace_entries(root: Path) -> dict[str, dict[str, Any]]:
    trace = _load_json(root / "pipeline_execution_trace.json")
    entries: dict[str, dict[str, Any]] = {}
    for item in (trace or {}).get("entries") or []:
        if not isinstance(item, dict):
            continue
        artifact = str(item.get("artifact") or item.get("output") or "").replace("\\", "/")
        if artifact:
            entries[Path(artifact).name] = item
            entries[artifact] = item
    return entries


def _command_results(root: Path) -> dict[str, dict[str, Any]]:
    payload = _load_json(root / "command_results.json") or {}
    results: dict[str, dict[str, Any]] = {}
    for item in payload.get("commands") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        if name:
            results[name] = item
    return results


def _source_run_refs(root: Path) -> list[Path]:
    manifest = _load_json(root / "source_run_manifest.json") or {}
    refs: list[Path] = []
    for key in ("previous_alignment_run", "previous_run", "source_run", "copied_from_run"):
        value = manifest.get(key)
        if isinstance(value, str) and value.strip():
            path = Path(value)
            refs.append(path if path.is_absolute() else Path.cwd() / path)
    return refs


def _matches_prior_artifact(root: Path, artifact_path: Path) -> bool:
    try:
        current = artifact_path.read_bytes()
    except OSError:
        return False
    for prior in _source_run_refs(root):
        candidate = prior / artifact_path.name
        try:
            if candidate.is_file() and candidate.read_bytes() == current:
                return True
        except OSError:
            continue
    return False


def _known_pipeline_source(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value.replace("\\", "/")
    return normalized.startswith("tools/") or normalized.startswith("video_pipeline_core/")


def classify_artifact(root: str | Path, artifact: str | Path) -> dict[str, Any]:
    root = Path(root)
    artifact_path = Path(artifact)
    if not artifact_path.is_absolute():
        artifact_path = root / artifact_path
    name = artifact_path.name
    trace_entry = _trace_entries(root).get(name) or _trace_entries(root).get(_rel(root, artifact_path))
    payload = _load_json(artifact_path) if artifact_path.suffix.lower() == ".json" else None

    if trace_entry:
        classification = str(trace_entry.get("classification") or "unknown")
        if classification not in TRACE_CLASSIFICATIONS:
            classification = "unknown"
        return {
            "artifact": _rel(root, artifact_path),
            "classification": classification,
            "trace_entry": trace_entry,
            "source_tool": trace_entry.get("source_tool"),
            "command": trace_entry.get("command"),
        }

    if isinstance(payload, Mapping):
        generated_by = payload.get("generated_by") or payload.get("source_tool")
        if _known_pipeline_source(generated_by):
            return {
                "artifact": _rel(root, artifact_path),
                "classification": "pipeline_tool_generated",
                "source_tool": generated_by,
                "command": payload.get("command"),
            }

    commands = _command_results(root)
    if name == "pipeline_home.json" and "pipeline_home" in commands:
        return {
            "artifact": _rel(root, artifact_path),
            "classification": "pipeline_tool_generated",
            "source_tool": "tools/pipeline_home.py",
            "command": commands["pipeline_home"].get("command"),
        }

    if artifact_path.is_file() and _matches_prior_artifact(root, artifact_path):
        return {
            "artifact": _rel(root, artifact_path),
            "classification": "copied_from_prior",
            "source_tool": None,
            "command": None,
        }

    return {
        "artifact": _rel(root, artifact_path),
        "classification": "unknown",
        "source_tool": None,
        "command": None,
    }


def build_pipeline_tool_inventory(repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    owners: list[dict[str, Any]] = []
    missing_nodes: list[dict[str, Any]] = []
    for owner, tools in PIPELINE_TOOLS.items():
        tool_entries = []
        owner_has_tool = False
        for tool in tools:
            exists = (root / tool).is_file()
            owner_has_tool = owner_has_tool or exists
            tool_entries.append({"path": tool, "exists": exists})
        entry = {
            "owner": owner,
            "tools": tool_entries,
            "status": "available" if owner_has_tool else "missing_pipeline_node",
        }
        owners.append(entry)
        if not owner_has_tool:
            missing_nodes.append({
                "owner": owner,
                "rule": "missing_pipeline_node",
                "message": f"no pipeline owner tool found for {owner}",
            })
    return {
        "artifact_role": "pipeline_tool_inventory",
        "version": 1,
        "owners": owners,
        "missing_pipeline_nodes": missing_nodes,
    }


def audit_run_gate_authenticity(run: str | Path) -> dict[str, Any]:
    root = Path(run)
    artifacts: list[dict[str, Any]] = []
    for name in CANONICAL_GATE_ARTIFACTS:
        path = root / name
        if path.exists():
            artifacts.append(classify_artifact(root, name))
        else:
            artifacts.append({
                "artifact": name,
                "classification": "missing_owner_tool" if name == "rendered_product_qa.json" else "unknown",
                "exists": False,
            })
    return {
        "artifact_role": "gate_authenticity_audit",
        "version": 1,
        "run": str(root),
        "artifacts": artifacts,
    }


def _has_candidate_video(root: Path) -> bool:
    return any(
        (root / name).is_file() and (root / name).stat().st_size > 0
        for name in ("final.mp4", "final_copyedit_rehearsal.mp4", "delivery_candidate.mp4", "verified_preview.mp4")
    )


def _block(rule: str, artifact: str, message: str, next_action: str = "repair_pipeline_execution_trace") -> dict[str, Any]:
    return {
        "rule": rule,
        "artifact": artifact,
        "message": message,
        "next_action": next_action,
    }


def _has_rendered_frame_evidence(payload: Mapping[str, Any] | None) -> bool:
    if not isinstance(payload, Mapping):
        return False
    if payload.get("contact_sheet") or payload.get("representative_frame"):
        return True
    for key in ("frame_evidence", "frame_evidence_refs", "rendered_frame_evidence", "sampled_frames"):
        value = payload.get(key)
        if isinstance(value, list) and value:
            return True
        if isinstance(value, str) and value.strip():
            return True
    return False


def evaluate_no_skip_contract(run: str | Path) -> dict[str, Any]:
    root = Path(run)
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    trace = _load_json(root / "pipeline_execution_trace.json")
    gate_audit = audit_run_gate_authenticity(root)

    if _has_candidate_video(root) and trace is None:
        blocking.append(_block(
            "missing_pipeline_execution_trace",
            "pipeline_execution_trace.json",
            "rendered rehearsal candidate requires pipeline_execution_trace.json",
        ))

    for artifact in gate_audit["artifacts"]:
        name = artifact.get("artifact")
        if name not in CANONICAL_GATE_ARTIFACTS or artifact.get("exists") is False:
            continue
        classification = artifact.get("classification")
        if classification == "pipeline_tool_generated":
            continue
        if classification == "run_local_worker_generated":
            blocking.append(_block(
                "self_authored_gate_artifact",
                str(name),
                "canonical gate artifact was generated by a run-local worker instead of a pipeline owner tool",
            ))
        elif classification == "copied_from_prior":
            blocking.append(_block(
                "copied_gate_artifact",
                str(name),
                "canonical gate artifact was copied from a prior run and must be regenerated by its owner tool",
            ))
        else:
            blocking.append(_block(
                "unknown_gate_authenticity",
                str(name),
                "canonical gate artifact lacks generated_by/source_tool/trace evidence",
            ))

    rendered_qa = _load_json(root / "rendered_product_qa.json")
    if _has_candidate_video(root):
        if rendered_qa is None:
            blocking.append(_block(
                "rendered_product_qa_missing",
                "rendered_product_qa.json",
                "rendered rehearsal candidate requires rendered product QA with frame/contact-sheet evidence",
                "run_rendered_product_qa",
            ))
            if not (Path.cwd() / "tools" / "rendered_product_qa.py").is_file():
                blocking.append(_block(
                    "missing_pipeline_node",
                    "tools/rendered_product_qa.py",
                    "rendered product QA owner tool is not available",
                    "create_rendered_product_qa_owner_tool",
                ))
        else:
            if rendered_qa.get("pass") is not True:
                blocking.append(_block(
                    "rendered_product_qa_not_passed",
                    "rendered_product_qa.json",
                    "rendered product QA did not pass",
                    "repair_rendered_product_quality",
                ))
            if not _has_rendered_frame_evidence(rendered_qa):
                blocking.append(_block(
                    "rendered_product_qa_lacks_frame_evidence",
                    "rendered_product_qa.json",
                    "rendered product QA must include rendered frame or contact-sheet evidence",
                    "sample_rendered_candidate_frames",
                ))

    title_qa = _load_json(root / "title_effect_lifecycle_qa.json")
    if title_qa is not None and title_qa.get("pass") is True and not _has_rendered_frame_evidence(title_qa):
        blocking.append(_block(
            "title_effect_qa_lacks_rendered_frame_evidence",
            "title_effect_lifecycle_qa.json",
            "title/effect lifecycle QA cannot be timing-only for rendered rehearsal candidates",
            "sample_title_effect_rendered_frames",
        ))

    return {
        "artifact_role": "no_skip_contract_decision",
        "version": 1,
        "pass": not blocking,
        "blocking": blocking,
        "warnings": warnings,
        "next_action": None if not blocking else blocking[0]["next_action"],
        "gate_authenticity": gate_audit,
    }


def build_failed_rehearsal_execution_trace(run: str | Path) -> dict[str, Any]:
    root = Path(run)
    artifacts = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = _rel(root, path)
        if path.suffix.lower() in {".mp4", ".wav", ".jpg", ".jpeg", ".png"}:
            classification = "run_local_worker_generated"
            trace_info: dict[str, Any] = {
                "artifact": rel,
                "classification": classification,
                "media_or_binary": True,
            }
        else:
            trace_info = classify_artifact(root, rel)
        artifacts.append(trace_info)
    return {
        "artifact_role": "failed_rehearsal_execution_trace",
        "version": 1,
        "run": str(root),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def build_rendered_product_quality_gap_report(run: str | Path) -> dict[str, Any]:
    root = Path(run)
    failure_review = Path("docs/construction-guides/work-orders/2026-07-08-copyedit-rehearsal-failure-review-report.md")
    contact_sheet = Path(".tmp/copyedit_rehearsal_failure_review_20260708-183000/contact_sheet_10s.jpg")
    rendered_qa = _load_json(root / "rendered_product_qa.json")
    title_qa = _load_json(root / "title_effect_lifecycle_qa.json")
    gaps = []
    if rendered_qa is None:
        gaps.append({
            "rule": "missing_rendered_product_qa",
            "message": "no rendered_product_qa.json inspected frames/contact sheet for product quality",
        })
    if isinstance(title_qa, Mapping) and title_qa.get("pass") is True and not _has_rendered_frame_evidence(title_qa):
        gaps.append({
            "rule": "timing_only_title_effect_qa",
            "message": "title_effect_lifecycle_qa checked timing claims without rendered-frame quality evidence",
        })
    return {
        "artifact_role": "rendered_product_quality_gap_report",
        "version": 1,
        "run": str(root),
        "failed_review_report": str(failure_review) if failure_review.is_file() else None,
        "contact_sheet_evidence": str(contact_sheet) if contact_sheet.is_file() else None,
        "quality_gaps": gaps,
        "product_quality_verified": not gaps,
    }


def write_trace_audit(run: str | Path, out_dir: str | Path) -> dict[str, Any]:
    root = Path(run)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    inventory = build_pipeline_tool_inventory()
    trace = build_failed_rehearsal_execution_trace(root)
    gate_audit = audit_run_gate_authenticity(root)
    quality = build_rendered_product_quality_gap_report(root)
    decision = evaluate_no_skip_contract(root)
    artifacts = {
        "pipeline_tool_inventory.json": inventory,
        "failed_rehearsal_execution_trace.json": trace,
        "gate_authenticity_audit.json": gate_audit,
        "rendered_product_quality_gap_report.json": quality,
        "no_skip_contract_decision.json": decision,
    }
    for name, payload in artifacts.items():
        (out / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    final_check = build_final_artifact_check(out)
    (out / "final_artifact_check.json").write_text(
        json.dumps(final_check, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return final_check


def build_final_artifact_check(out_dir: str | Path) -> dict[str, Any]:
    root = Path(out_dir)
    required = [
        "pipeline_tool_inventory.json",
        "failed_rehearsal_execution_trace.json",
        "gate_authenticity_audit.json",
        "rendered_product_quality_gap_report.json",
        "no_skip_contract_decision.json",
    ]
    bad: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".srt", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            bad.append(_rel(root, path))
            continue
        if "\ufffd" in text or "????" in text:
            bad.append(_rel(root, path))
    forbidden_media = [
        _rel(root, path)
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".mp4", ".mov", ".wav"}
    ]
    forbidden_approvals = [
        name
        for name in ("story_human_review_decision.json", "human_transcript_review_decision.json")
        if (root / name).exists()
    ]
    return {
        "artifact_role": "final_artifact_check",
        "version": 1,
        "status": "ok" if not bad and not forbidden_media and not forbidden_approvals and all((root / name).exists() for name in required) else "failed",
        "required_files": {name: (root / name).exists() for name in required},
        "checks": {
            "utf8_no_corruption": not bad,
            "utf8_bad_files": bad,
            "no_render_or_final_created": not forbidden_media,
            "forbidden_media": forbidden_media,
            "no_approval_artifacts": not forbidden_approvals,
            "forbidden_approvals": forbidden_approvals,
        },
    }
