"""Render-free golden-path smoke for the contract pipeline."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from . import contract_adapter, dashboard_state, spec_review
from .next_action_vocabulary import NEXT_ACTION_VOCABULARY


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = {
    "stock_story": ROOT / "examples" / "genre_tests" / "stock_story_e2e",
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _copy_fixture(case: str, run_dir: Path) -> Path:
    fixture = FIXTURES.get(case)
    if not fixture or not fixture.exists():
        raise ValueError(f"unknown e2e smoke case: {case}")
    for name in ("brief.json", "blueprint.json", "segment_contract.json", "material_categories.json"):
        shutil.copy2(fixture / name, run_dir / name)
    return run_dir / "segment_contract.json"


def _verify_result_payload() -> dict:
    return {
        "artifact_role": "verify_result",
        "version": 1,
        "pass": True,
        "score": 100,
        "dimensions": {
            "script_coverage": 100,
            "duration_fit": 100,
            "subtitle_accuracy": 100,
            "audio_levels": 100,
            "technical_quality": 100,
            "subtitle_readability": 100,
        },
        "issue_count": 0,
        "issues": [],
    }


def _record_state(run_dir: Path, step: str, trace: list[dict]) -> str | None:
    state = dashboard_state.load_dashboard_state(str(run_dir))
    action = state["run"].get("next_action")
    trace.append({"step": step, "next_action": action})
    return action


def _classify_trace(trace: list[dict]) -> tuple[bool, str | None]:
    actions = [item.get("next_action") for item in trace if item.get("next_action")]
    if not actions:
        return False, "no_next_action"
    last = actions[-1]
    if isinstance(last, str) and last.startswith("missing_artifact:"):
        return False, last
    if last not in NEXT_ACTION_VOCABULARY:
        return False, f"unknown:{last}"
    if len(actions) >= 2 and actions[-1] == actions[-2]:
        return False, f"repeat_without_progress:{last}"
    return True, last


def run_e2e_smoke(case: str = "stock_story", *, keep_dir: bool = False, base_dir: str | Path | None = None) -> dict:
    temp_ctx = None
    if base_dir is None:
        temp_ctx = tempfile.TemporaryDirectory(prefix=f"e2e_smoke_{case}_")
        run_dir = Path(temp_ctx.name)
    else:
        run_dir = Path(base_dir)
        run_dir.mkdir(parents=True, exist_ok=True)

    try:
        contract_path = _copy_fixture(case, run_dir)
        contract = _read_json(contract_path)
        brief = _read_json(run_dir / "brief.json")
        trace: list[dict] = []

        review = spec_review.review_spec(contract, brief, has_editorial_design=True)
        _write_json(run_dir / "spec_review.json", review)
        _record_state(run_dir, "spec_review", trace)

        dry = contract_adapter.dry_build(
            contract_path,
            run_dir,
            categories_path=run_dir / "material_categories.json",
            verbose=False,
        )
        _record_state(run_dir, "contract_dry_build", trace)

        _write_json(run_dir / "verify_result.json", _verify_result_payload())
        (run_dir / "final.mp4").write_bytes(b"e2e-smoke-placeholder-not-a-render\n")
        final_action = _record_state(run_dir, "simulated_verify", trace)

        ok, stalled_action = _classify_trace(trace)
        return {
            "ok": ok,
            "case": case,
            "run_dir": str(run_dir) if keep_dir or base_dir else None,
            "trace": trace,
            "final_next_action": final_action,
            "stalled_action": None if ok else stalled_action,
            "spec_ready_for_build": review.get("ready_for_build"),
            "dry_build_ok": dry.get("ok"),
        }
    finally:
        if temp_ctx and not keep_dir:
            temp_ctx.cleanup()


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run a render-free pipeline e2e smoke.")
    parser.add_argument("--case", default="stock_story", choices=sorted(FIXTURES))
    parser.add_argument("--keep-dir", action="store_true")
    parser.add_argument("--out-dir")
    args = parser.parse_args(argv)

    result = run_e2e_smoke(args.case, keep_dir=args.keep_dir, base_dir=args.out_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
