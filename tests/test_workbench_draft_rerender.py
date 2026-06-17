import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import video_tools
from tools.workbench_handoff import build_handoff
from tools.workbench_draft_rerender import rerender_from_handoff


def _write(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _make_root(tmp: str) -> Path:
    root = Path(tmp)
    source = root / "clip.mp4"
    source.write_bytes(b"video")
    (root / "music.wav").write_bytes(b"music")
    _write(root / "timeline.json", {
        "artifact_role": "timeline",
        "plan": [
            {
                "slot_index": 0,
                "source": str(source),
                "slot_dur": 2.0,
                "extract_start": 0.0,
                "extract_dur": 2.0,
            }
        ],
    })
    _write(root / "project_material_map.json", {
        "artifact_role": "project_material_map",
        "version": 1,
        "assets": [{
            "asset_id": "a0",
            "asset_type": "video",
            "source": str(source),
            "duration_sec": 5.0,
        }],
        "needs": [],
    })
    return root


class FakeRenderer:
    def __init__(self):
        self.calls = []

    def __call__(self, plan, music_path, out_path, mat_dir=None):
        self.calls.append({"plan": plan, "music": music_path, "out": out_path, "mat_dir": mat_dir})
        Path(out_path).write_bytes(b"rendered")
        return out_path


class FakeEffectRenderer:
    def __init__(self):
        self.calls = []

    def __call__(self, artifact_root, input_path, output_path, **kwargs):
        self.calls.append({"root": artifact_root, "input": input_path, "output": output_path, "kwargs": kwargs})
        Path(output_path).write_bytes(Path(input_path).read_bytes() + b"+fx")
        return {"ok": True, "out": output_path, "applied_count": 1, "skipped_count": 0}


class WorkbenchDraftRerenderTest(unittest.TestCase):
    def test_rerender_requires_valid_handoff_and_uses_patched_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _write(root / "patched_draft_timeline.json", {
                "artifact_role": "patched_draft_timeline",
                "plan": [{
                    "slot_index": 0,
                    "source": str(root / "clip.mp4"),
                    "slot_dur": 1.5,
                    "extract_start": 0.5,
                    "extract_dur": 1.5,
                }],
            })
            _write(root / "workbench_review_report.json", {"artifact_role": "workbench_review_report"})
            _write(root / "workbench_handoff.json", build_handoff(str(root)))
            renderer = FakeRenderer()

            result = rerender_from_handoff(str(root), renderer=renderer)

            self.assertTrue(result["ok"])
            self.assertEqual(result["artifact_role"], "workbench_draft_rerender")
            self.assertEqual(result["handoff_validation"]["ok"], True)
            self.assertEqual(result["export"]["source"], "patched_timeline")
            self.assertEqual(len(renderer.calls), 1)
            self.assertEqual(renderer.calls[0]["plan"][0]["slot_dur"], 1.5)
            self.assertTrue((root / "workbench_rerender.mp4").is_file())
            self.assertTrue((root / "workbench_rerender_report.json").is_file())
            self.assertFalse((root / "final.mp4").exists())

    def test_rerender_can_use_timeline_patch_when_no_patched_draft_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _write(root / "timeline_patch.json", {
                "artifact_role": "timeline_patch",
                "version": 1,
                "patches": [{"op": "set_duration", "slot_index": 0, "after": {"duration_sec": 1.0}}],
            })
            _write(root / "workbench_review_report.json", {"artifact_role": "workbench_review_report"})
            _write(root / "workbench_handoff.json", build_handoff(str(root)))

            result = rerender_from_handoff(str(root), renderer=FakeRenderer())

            self.assertTrue(result["ok"])
            self.assertEqual(result["export"]["source"], "patch")

    def test_invalid_handoff_fails_before_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _write(root / "workbench_handoff.json", {
                "artifact_role": "workbench_handoff",
                "version": 1,
                "artifacts": {"timeline_patch": "timeline_patch.json"},
                "artifact_details": {"timeline_patch": {"path": "timeline_patch.json", "size_bytes": 1, "sha256": "0" * 64}},
            })
            renderer = FakeRenderer()

            with self.assertRaises(ValueError):
                rerender_from_handoff(str(root), renderer=renderer)

            self.assertEqual(renderer.calls, [])
            self.assertFalse((root / "workbench_rerender.mp4").exists())

    def test_rerender_refuses_canonical_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _write(root / "patched_draft_timeline.json", {
                "artifact_role": "patched_draft_timeline",
                "plan": [{"slot_index": 0, "source": str(root / "clip.mp4"), "slot_dur": 1.0}],
            })
            _write(root / "workbench_review_report.json", {"artifact_role": "workbench_review_report"})
            _write(root / "workbench_handoff.json", build_handoff(str(root)))

            with self.assertRaises(ValueError):
                rerender_from_handoff(str(root), out="final.mp4", renderer=FakeRenderer())

    def test_effects_are_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _write(root / "patched_draft_timeline.json", {
                "artifact_role": "patched_draft_timeline",
                "plan": [{"slot_index": 0, "source": str(root / "clip.mp4"), "slot_dur": 1.0}],
            })
            _write(root / "effect_patch.json", {
                "artifact_role": "effect_patch",
                "version": 1,
                "patches": [{
                    "op": "add_effect",
                    "effect_id": "fx1",
                    "after": {"preset": "flash", "target_slot_index": 0, "start_sec": 0, "duration_sec": 0.5},
                }],
            })
            _write(root / "workbench_review_report.json", {"artifact_role": "workbench_review_report"})
            _write(root / "workbench_handoff.json", build_handoff(str(root)))
            effects = FakeEffectRenderer()

            result = rerender_from_handoff(
                str(root),
                renderer=FakeRenderer(),
                render_effects=True,
                effect_renderer=effects,
            )

            self.assertEqual(len(effects.calls), 1)
            self.assertEqual(result["export"]["effect_render"]["applied_count"], 1)

    def test_video_tools_workbench_draft_rerender_cli_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _write(root / "patched_draft_timeline.json", {
                "artifact_role": "patched_draft_timeline",
                "plan": [{"slot_index": 0, "source": str(root / "clip.mp4"), "slot_dur": 1.0}],
            })
            _write(root / "workbench_review_report.json", {"artifact_role": "workbench_review_report"})
            _write(root / "workbench_handoff.json", build_handoff(str(root)))

            with redirect_stdout(StringIO()):
                video_tools.cmd_workbench_draft_rerender(
                    SimpleNamespace(
                        artifact_root=str(root),
                        out="preview.mp4",
                        report_out=None,
                        music=None,
                        effects=False,
                        renderer=FakeRenderer(),
                    )
                )

            self.assertTrue((root / "preview.mp4").is_file())
            report = json.loads((root / "workbench_rerender_report.json").read_text(encoding="utf-8"))
            self.assertTrue(report["ok"])

    def test_default_report_path_with_relative_artifact_root_is_not_double_prefixed(self):
        tmp_parent = Path.cwd() / ".tmp"
        tmp_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_parent) as tmp:
            root = _make_root(tmp)
            _write(root / "patched_draft_timeline.json", {
                "artifact_role": "patched_draft_timeline",
                "plan": [{"slot_index": 0, "source": str(root / "clip.mp4"), "slot_dur": 1.0}],
            })
            _write(root / "workbench_review_report.json", {"artifact_role": "workbench_review_report"})
            rel_root = Path(os.path.relpath(root, Path.cwd()))
            _write(rel_root / "workbench_handoff.json", build_handoff(str(rel_root)))

            result = rerender_from_handoff(str(rel_root), renderer=FakeRenderer())

            expected = rel_root / "workbench_rerender_report.json"
            double_prefixed = rel_root / rel_root / "workbench_rerender_report.json"
            self.assertEqual(Path(result["report_path"]), expected)
            self.assertTrue(expected.is_file())
            self.assertFalse(double_prefixed.exists())


if __name__ == "__main__":
    unittest.main()
