import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import video_tools
from tools.operator_flow_acceptance import run_operator_flow_acceptance
from tools.workbench_handoff import build_handoff


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _material_needs():
    return {
        "artifact_role": "material_needs",
        "version": 1,
        "project": "generic-demo",
        "needs": [{
            "need_id": "nd_demo",
            "category": "training",
            "type": "video",
            "purpose": "show the training action",
            "count": 1,
            "fallback_tier": 1,
            "must_have": True,
        }],
    }


def _project_map_with_satisfies(source: Path):
    return {
        "artifact_role": "project_material_map",
        "version": 1,
        "assets": [{
            "asset_id": "clip-a",
            "asset_type": "video",
            "source": str(source),
            "duration_sec": 4.0,
            "scenes": [{
                "start": 0.0,
                "end": 2.0,
                "caption": "training action",
                "satisfies": [{"need_id": "nd_demo", "status": "accepted"}],
            }],
        }],
    }


def _write_workbench_bundle(root: Path) -> None:
    source = root / "clip.mp4"
    source.write_bytes(b"clip")
    (root / "music.wav").write_bytes(b"music")
    _write_json(root / "timeline.json", {
        "artifact_role": "timeline",
        "plan": [{
            "slot_index": 0,
            "source": str(source),
            "slot_dur": 1.0,
            "extract_start": 0.0,
            "extract_dur": 1.0,
        }],
    })
    _write_json(root / "patched_draft_timeline.json", {
        "artifact_role": "patched_draft_timeline",
        "plan": [{
            "slot_index": 0,
            "source": str(source),
            "slot_dur": 1.0,
            "extract_start": 0.0,
            "extract_dur": 1.0,
        }],
    })
    _write_json(root / "workbench_review_report.json", {
        "artifact_role": "workbench_review_report",
        "ok": True,
    })
    _write_json(root / "workbench_handoff.json", build_handoff(str(root)))


class FakeRenderer:
    def __init__(self):
        self.calls = []

    def __call__(self, plan, music_path, out_path, mat_dir=None):
        self.calls.append({
            "plan": plan,
            "music_path": music_path,
            "out_path": out_path,
            "mat_dir": mat_dir,
        })
        Path(out_path).write_bytes(b"rendered")
        return out_path


class OperatorFlowAcceptanceTest(unittest.TestCase):
    def test_incomplete_replay_package_fails_before_rerender_when_satisfies_has_no_needs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_workbench_bundle(root)
            _write_json(root / "project_material_map.json", _project_map_with_satisfies(root / "clip.mp4"))
            renderer = FakeRenderer()

            report = run_operator_flow_acceptance(str(root), renderer=renderer)

            self.assertFalse(report["ok"])
            self.assertEqual(report["stage"], "incomplete_replay_package")
            self.assertIn("material_needs.json", report["errors"][0]["message"])
            self.assertEqual(renderer.calls, [])
            self.assertTrue((root / "operator_flow_acceptance.json").is_file())

    def test_explicit_report_out_is_not_rebased_under_artifact_root(self):
        tmp_parent = Path.cwd() / ".tmp"
        tmp_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_parent) as tmp:
            root = Path(tmp)
            _write_workbench_bundle(root)
            _write_json(root / "project_material_map.json", _project_map_with_satisfies(root / "clip.mp4"))
            report_out = Path(".tmp") / "operator_flow_explicit_report.json"
            if report_out.exists():
                report_out.unlink()

            report = run_operator_flow_acceptance(str(root), report_out=str(report_out), renderer=FakeRenderer())

            self.assertFalse(report["ok"])
            self.assertTrue(report_out.is_file())
            self.assertFalse((root / report_out).exists())
            report_out.unlink()

    def test_complete_package_runs_material_lifecycle_handoff_and_draft_rerender(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_workbench_bundle(root)
            _write_json(root / "material_needs.json", _material_needs())
            _write_json(root / "project_material_map.json", _project_map_with_satisfies(root / "clip.mp4"))
            renderer = FakeRenderer()

            report = run_operator_flow_acceptance(str(root), renderer=renderer)

            self.assertTrue(report["ok"], report.get("errors"))
            self.assertEqual(report["stage"], "passed")
            self.assertEqual(report["material_lifecycle"]["exit"], "ok")
            self.assertNotEqual(report["material_lifecycle"]["stage"], "invalid")
            self.assertTrue(report["workbench_handoff_validation"]["ok"])
            self.assertTrue(report["workbench_rerender"]["ok"])
            self.assertEqual(len(renderer.calls), 1)
            self.assertTrue((root / "operator_flow_rerender.mp4").is_file())
            self.assertTrue((root / "operator_flow_rerender_report.json").is_file())
            self.assertTrue((root / "operator_flow_acceptance.json").is_file())

    def test_video_tools_operator_flow_acceptance_cli_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_workbench_bundle(root)
            _write_json(root / "material_needs.json", _material_needs())
            _write_json(root / "project_material_map.json", _project_map_with_satisfies(root / "clip.mp4"))
            renderer = FakeRenderer()

            with redirect_stdout(StringIO()):
                video_tools.cmd_operator_flow_acceptance(
                    SimpleNamespace(
                        artifact_root=str(root),
                        out=str(root / "operator_report.json"),
                        rerender_out="operator.mp4",
                        rerender_report_out="operator_rerender_report.json",
                        effects=False,
                        renderer=renderer,
                    )
                )

            self.assertTrue((root / "operator_report.json").is_file())
            self.assertTrue((root / "operator.mp4").is_file())
            payload = json.loads((root / "operator_report.json").read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"])
            self.assertEqual(len(renderer.calls), 1)


if __name__ == "__main__":
    unittest.main()
