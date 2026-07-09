"""Thin graduation product route execution harness."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from video_pipeline_core.no_skip_execution_trace import classify_artifact
from video_pipeline_core.rendered_product_qa import find_rendered_candidate


CommandRunner = Callable[[list[str], Path | None], dict[str, Any]]


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _default_command_runner(command: list[str], cwd: Path | None = None) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _parse_stdout_json(result: dict[str, Any]) -> dict[str, Any] | None:
    try:
        payload = json.loads(result.get("stdout") or "{}")
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _is_approved_product_decision(payload: dict[str, Any] | None) -> tuple[bool, str | None]:
    if payload is None:
        return False, "missing product_route_review_decision.json"
    decision = payload.get("decision") or payload.get("status")
    reviewer = payload.get("reviewer")
    if decision != "approved":
        return False, f"decision={decision}"
    if reviewer != "human":
        return False, f"reviewer={reviewer}"
    if payload.get("approve_all_reviewed") is False:
        return False, "approve_all_reviewed=false"
    return True, None


def _readiness_ok(payload: dict[str, Any] | None) -> tuple[bool, str | None]:
    if payload is None:
        return False, "missing production_readiness_gate.json"
    if payload.get("ready_for_production") is True or payload.get("pass") is True:
        return True, None
    return False, str(payload.get("status") or payload.get("next_action") or "not ready")


def _visual_gate_ok(run: Path, payload: dict[str, Any] | None) -> tuple[bool, str | None]:
    if payload is None:
        return False, "missing visual_selection_gate.json"
    if payload.get("pass") is not True:
        return False, str(payload.get("status") or "visual gate not passed")
    classification = classify_artifact(run, "visual_selection_gate.json").get("classification")
    if classification in {"copied_from_prior", "run_local_worker_generated", "unknown"}:
        return False, f"{classification} visual_selection_gate.json"
    return True, None


def _effect_ok(payload: dict[str, Any] | None) -> tuple[bool, str | None]:
    if payload is None:
        return False, "missing effect_handoff.json"
    status = payload.get("status") or payload.get("review_status")
    if status in {"accepted", "review_accepted", "ready"} or payload.get("pass") is True:
        return True, None
    return False, str(status or "effect handoff not accepted")


def _music_subtitle_ok(run: Path) -> tuple[bool, str | None]:
    for name in ("render_handoff.json", "audio_subtitle_review_handoff.json", "render_rehearsal_entry_packet.json"):
        payload = _load_json(run / name)
        if payload is None:
            continue
        if payload.get("status") in {"ready", "accepted"} or payload.get("pass") is True:
            return True, None
        if payload.get("music_subtitle_profile") or payload.get("profiles"):
            return True, None
    return False, "missing music/subtitle profile evidence"


# Declarative route stage table (single source of the graduation product-route
# sequence + per-stage owner branch, owner tool, gate artifact, and kind). run()
# is a consumer of this table; a guard test asserts the executed stage order
# matches it and that every owner is a registered branch. ``kind`` declares
# whether each stage is a mechanical verify or a review (point-4 "every stage has
# a verify or a review"); signature enforcement is declared here but intentionally
# not enforced yet (turning it on is a deliberate tightening, not a refactor).
VERIFY_KINDS = {"state_check", "artifact_check", "verify"}
REVIEW_KINDS = {"human_review", "review", "signed_review"}

ROUTE_STAGES: list[dict[str, Any]] = [
    {"stage_id": "pipeline_home", "owner": "main-pipeline", "owner_tool": "tools/pipeline_home.py", "artifact": None, "kind": "state_check"},
    {"stage_id": "film_canon_route_artifact_check", "owner": "film-canon-product-route", "owner_tool": None, "artifact": "graduation_film_canon.json", "kind": "artifact_check"},
    {"stage_id": "film_canon_readiness", "owner": "film-canon-product-route", "owner_tool": "tools/film_canon_readiness.py", "artifact": "production_readiness_gate.json", "kind": "verify"},
    {"stage_id": "product_route_review_decision", "owner": "film-canon-product-route", "owner_tool": "tools/write_product_route_review_decision.py", "artifact": "product_route_review_decision.json", "kind": "human_review"},
    {"stage_id": "shot_level_material_proof", "owner": "material-map", "owner_tool": None, "artifact": "shot_level_material_proof_plan.json", "kind": "verify"},
    {"stage_id": "visual_selection_gate", "owner": "film-canon-product-route", "owner_tool": "tools/visual_selection_gate.py", "artifact": "visual_selection_gate.json", "kind": "review"},
    {"stage_id": "effect_handoff", "owner": "effect-factory", "owner_tool": None, "artifact": "effect_handoff.json", "kind": "review"},
    {"stage_id": "music_subtitle_profile", "owner": "soundtrack-arranger", "owner_tool": None, "artifact": "render_handoff.json", "kind": "verify"},
    {"stage_id": "compose_render_handoff", "owner": "main-pipeline", "owner_tool": None, "artifact": "render_handoff.json", "kind": "verify"},
    {"stage_id": "rendered_product_qa", "owner": "verify-delivery", "owner_tool": "tools/rendered_product_qa.py", "artifact": "rendered_product_qa.json", "kind": "verify"},
    {"stage_id": "no_skip_execution_trace", "owner": "verify-delivery", "owner_tool": "tools/no_skip_execution_trace.py", "artifact": "no_skip_contract_decision.json", "kind": "verify"},
]

ROUTE_STAGE_BY_ID: dict[str, dict[str, Any]] = {stage["stage_id"]: stage for stage in ROUTE_STAGES}


class GraduationProductRouteRunner:
    def __init__(
        self,
        *,
        repo_root: str | Path,
        python_exe: str = r"C:\Users\user\miniconda3\python.exe",
        command_runner: CommandRunner = _default_command_runner,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.python_exe = python_exe
        self.command_runner = command_runner
        self.entries: list[dict[str, Any]] = []

    def _record(
        self,
        stage_id: str,
        *,
        owner: str,
        owner_tool: str | None = None,
        artifact: str | None = None,
        inputs: list[str] | None = None,
        outputs: list[str] | None = None,
        command: list[str] | None = None,
        command_result: dict[str, Any] | None = None,
        status: str,
        evidence: dict[str, Any] | None = None,
        stop_reason: str | None = None,
    ) -> None:
        self.entries.append({
            "stage_id": stage_id,
            "owner": owner,
            "owner_tool": owner_tool,
            "artifact": artifact,
            "inputs": inputs or [],
            "outputs": outputs or [],
            "command": command,
            "exit_code": None if command_result is None else command_result.get("exit_code"),
            "status": status,
            "evidence": evidence or {},
            "stop_reason": stop_reason,
            "classification": "pipeline_tool_generated" if owner_tool else "unknown",
            "source_tool": owner_tool,
        })

    def _record_stage(
        self,
        stage_id: str,
        *,
        status: str,
        inputs: list[str] | None = None,
        outputs: list[str] | None = None,
        command: list[str] | None = None,
        command_result: dict[str, Any] | None = None,
        evidence: dict[str, Any] | None = None,
        stop_reason: str | None = None,
    ) -> None:
        """Record a stage, taking owner/owner_tool/artifact from ROUTE_STAGES."""
        spec = ROUTE_STAGE_BY_ID[stage_id]
        self._record(
            stage_id,
            owner=spec["owner"],
            owner_tool=spec["owner_tool"],
            artifact=spec["artifact"],
            inputs=inputs,
            outputs=outputs,
            command=command,
            command_result=command_result,
            status=status,
            evidence=evidence,
            stop_reason=stop_reason,
        )

    def _stop(self, out_dir: Path, gate: str, reason: str) -> dict[str, Any]:
        result = {
            "artifact_role": "graduation_product_route_harness_result",
            "version": 1,
            "source_tool": "tools/run_graduation_product_route.py",
            "pass": False,
            "stop_gate": gate,
            "stop_reason": reason,
            "trace_path": str(out_dir / "pipeline_execution_trace.json"),
            "next_action": "repair_or_complete_upstream_gate",
        }
        self._write_outputs(out_dir, result)
        return result

    def _write_outputs(self, out_dir: Path, result: dict[str, Any]) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        trace = {
            "artifact_role": "pipeline_execution_trace",
            "version": 1,
            "source_tool": "tools/run_graduation_product_route.py",
            "entries": self.entries,
        }
        (out_dir / "pipeline_execution_trace.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (out_dir / "graduation_product_route_harness_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def run(self, *, run: str | Path, source_root: str | Path, out_dir: str | Path, mode: str) -> dict[str, Any]:
        run_dir = Path(run)
        source = Path(source_root)
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        self.entries = []

        command = [self.python_exe, "tools/pipeline_home.py", "--run", str(run_dir), "--json"]
        home_result = self.command_runner(command, self.repo_root)
        home_payload = _parse_stdout_json(home_result) or {}
        home_status = str(home_payload.get("status") or "UNKNOWN")
        self._record_stage(
            "pipeline_home",
            inputs=[str(run_dir)],
            outputs=["pipeline_home_json_stdout"],
            command=command,
            command_result=home_result,
            status="pass" if home_status not in {"UNKNOWN", "WAITING", "REPAIR"} else "stop",
            evidence=home_payload,
            stop_reason=home_status if home_status in {"UNKNOWN", "WAITING", "REPAIR"} else None,
        )
        if home_status in {"UNKNOWN", "WAITING", "REPAIR"}:
            return self._stop(out, "pipeline_home", home_status)

        self._record_stage(
            "film_canon_route_artifact_check",
            inputs=[str(source)],
            outputs=["graduation_film_canon.json", "film_canon.json"],
            status="inspected",
            evidence={
                "graduation_film_canon_exists": (run_dir / "graduation_film_canon.json").exists(),
                "film_canon_exists": (run_dir / "film_canon.json").exists(),
            },
        )

        readiness_payload = _load_json(run_dir / "production_readiness_gate.json")
        readiness_pass, readiness_reason = _readiness_ok(readiness_payload)
        self._record_stage(
            "film_canon_readiness",
            inputs=["product_route_review_decision.json"],
            outputs=["production_readiness_gate.json"],
            status="pass" if readiness_pass else "missing_or_not_ready",
            evidence=readiness_payload or {},
            stop_reason=readiness_reason,
        )

        decision_payload = _load_json(run_dir / "product_route_review_decision.json")
        decision_pass, decision_reason = _is_approved_product_decision(decision_payload)
        self._record_stage(
            "product_route_review_decision",
            status="pass" if decision_pass else "stop",
            evidence=decision_payload or {},
            stop_reason=decision_reason,
        )
        if not decision_pass:
            return self._stop(out, "product_route_review_decision", decision_reason or "not approved")
        if not readiness_pass:
            return self._stop(out, "film_canon_readiness", readiness_reason or "not ready")

        shot_proof = _load_json(run_dir / "shot_level_material_proof_plan.json")
        self._record_stage(
            "shot_level_material_proof",
            status="pass" if shot_proof else "stop",
            evidence=shot_proof or {},
            stop_reason=None if shot_proof else "missing shot_level_material_proof_plan.json",
        )
        if shot_proof is None:
            return self._stop(out, "shot_level_material_proof", "missing shot_level_material_proof_plan.json")

        visual_payload = _load_json(run_dir / "visual_selection_gate.json")
        visual_pass, visual_reason = _visual_gate_ok(run_dir, visual_payload)
        self._record_stage(
            "visual_selection_gate",
            status="pass" if visual_pass else "stop",
            evidence=visual_payload or {},
            stop_reason=visual_reason,
        )
        if not visual_pass:
            return self._stop(out, "visual_selection_gate", visual_reason or "visual gate not passed")

        effect_payload = _load_json(run_dir / "effect_handoff.json")
        effect_pass, effect_reason = _effect_ok(effect_payload)
        self._record_stage(
            "effect_handoff",
            status="pass" if effect_pass else "stop",
            evidence=effect_payload or {},
            stop_reason=effect_reason,
        )
        if not effect_pass:
            return self._stop(out, "effect_handoff", effect_reason or "effect handoff not accepted")

        music_pass, music_reason = _music_subtitle_ok(run_dir)
        self._record_stage(
            "music_subtitle_profile",
            status="pass" if music_pass else "stop",
            evidence={"checked_artifacts": ["render_handoff.json", "audio_subtitle_review_handoff.json", "render_rehearsal_entry_packet.json"]},
            stop_reason=music_reason,
        )
        if not music_pass:
            return self._stop(out, "music_subtitle_profile", music_reason or "missing evidence")

        compose_handoff = _load_json(run_dir / "render_handoff.json")
        self._record_stage(
            "compose_render_handoff",
            status="pass" if compose_handoff else "stop",
            evidence=compose_handoff or {},
            stop_reason=None if compose_handoff else "missing render_handoff.json",
        )
        if compose_handoff is None:
            return self._stop(out, "compose_render_handoff", "missing render_handoff.json")

        candidate = find_rendered_candidate(run_dir)
        if mode == "no-render" or candidate is None:
            result = {
                "artifact_role": "graduation_product_route_harness_result",
                "version": 1,
                "source_tool": "tools/run_graduation_product_route.py",
                "pass": mode == "no-render",
                "stop_gate": None if mode == "no-render" else "rendered_candidate",
                "stop_reason": None if mode == "no-render" else "missing rendered candidate",
                "trace_path": str(out / "pipeline_execution_trace.json"),
                "next_action": "ready_for_render_rehearsal" if mode == "no-render" else "create_rendered_candidate",
            }
            self._write_outputs(out, result)
            return result

        rendered_command = [self.python_exe, "tools/rendered_product_qa.py", "--run", str(run_dir), "--out-dir", str(out), "--json"]
        rendered_result = self.command_runner(rendered_command, self.repo_root)
        rendered_payload = _parse_stdout_json(rendered_result) or {}
        self._record_stage(
            "rendered_product_qa",
            inputs=[str(candidate)],
            outputs=["rendered_product_qa.json"],
            command=rendered_command,
            command_result=rendered_result,
            status="pass" if rendered_payload.get("pass") is True else "stop",
            evidence=rendered_payload,
            stop_reason=None if rendered_payload.get("pass") is True else "rendered product QA failed",
        )
        if rendered_payload.get("pass") is not True:
            return self._stop(out, "rendered_product_qa", "rendered product QA failed")

        no_skip_command = [self.python_exe, "tools/no_skip_execution_trace.py", "--run", str(out), "--out-dir", str(out), "--json"]
        no_skip_result = self.command_runner(no_skip_command, self.repo_root)
        no_skip_payload = _parse_stdout_json(no_skip_result) or {}
        self._record_stage(
            "no_skip_execution_trace",
            inputs=["pipeline_execution_trace.json", "rendered_product_qa.json"],
            outputs=["no_skip_contract_decision.json"],
            command=no_skip_command,
            command_result=no_skip_result,
            status="pass" if no_skip_result.get("exit_code") == 0 else "stop",
            evidence=no_skip_payload,
            stop_reason=None if no_skip_result.get("exit_code") == 0 else "no-skip trace failed",
        )
        if no_skip_result.get("exit_code") != 0:
            return self._stop(out, "no_skip_execution_trace", "no-skip trace failed")

        result = {
            "artifact_role": "graduation_product_route_harness_result",
            "version": 1,
            "source_tool": "tools/run_graduation_product_route.py",
            "pass": True,
            "stop_gate": None,
            "stop_reason": None,
            "trace_path": str(out / "pipeline_execution_trace.json"),
            "next_action": "route_trace_complete",
        }
        self._write_outputs(out, result)
        return result
