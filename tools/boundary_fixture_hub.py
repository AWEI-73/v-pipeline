"""Discover and run boundary-smoke fixture folders under an explicit root."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.boundary_smoke import run_boundary


def _load_json(path: Path):
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def discover_fixtures(root) -> list[dict]:
    root = Path(root).resolve()
    fixtures = []
    for config_path in sorted(root.glob("*/input/boundary_config.json")):
        fixture_dir = config_path.parent.parent
        config = _load_json(config_path)
        fixtures.append({
            "name": fixture_dir.name,
            "stage": config.get("stage"),
            "path": str(fixture_dir),
        })
    return fixtures


def run_fixture_hub(root, *, stage: str | None = None) -> dict:
    root = Path(root).resolve()
    fixtures = discover_fixtures(root)
    if stage:
        fixtures = [item for item in fixtures if item.get("stage") == stage]

    results = []
    for fixture in fixtures:
        report = run_boundary(fixture["path"])
        results.append({
            "name": fixture["name"],
            "stage": fixture["stage"],
            "path": fixture["path"],
            "pass": bool(report.get("pass")),
            "gate_status": report.get("gate_status"),
            "regressions": report.get("regressions") or [],
            "report": str(Path(fixture["path"]) / "actual" / "boundary_report.json"),
        })

    summary = {
        "artifact_role": "boundary_fixture_report",
        "version": 1,
        "root": str(root),
        "stage_filter": stage,
        "fixture_count": len(results),
        "pass_count": sum(1 for item in results if item["pass"]),
        "fail_count": sum(1 for item in results if not item["pass"]),
        "pass": all(item["pass"] for item in results),
        "results": results,
    }
    _write_json(root / "boundary_fixture_report.json", summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="fixture root containing */input/boundary_config.json")
    parser.add_argument("--stage", help="only run one boundary stage")
    parser.add_argument("--json", action="store_true", help="print JSON summary")
    args = parser.parse_args(argv)
    summary = run_fixture_hub(args.root, stage=args.stage)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"fixtures={summary['fixture_count']} pass={summary['pass_count']} fail={summary['fail_count']}")
        for item in summary["results"]:
            status = "PASS" if item["pass"] else "FAIL"
            print(f"{status} {item['name']} ({item['stage']})")
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
