import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.tool_command_catalog import build_command_manifest, build_workflow_manifest


def _effect_revision_request():
    return {
        "artifact_role": "effect_revision_request",
        "version": 1,
        "status": "pending",
        "summary": {"request_count": 2},
        "requests": [{
            "request_id": "fxrev_page",
            "effect_id": "fxintent_2_external_effect_1",
            "source_effect_id": "fx_page_turn",
            "segment": 2,
            "operation": "external_effect",
            "route": "route_to_node14_or_remotion_adapter",
            "reason": "remotion-only page turn did not render",
            "status": "pending",
        }, {
            "request_id": "fxrev_lower",
            "effect_id": "seg1_lower_third_1",
            "source_effect_id": "fx_lower",
            "segment": 1,
            "operation": "lower_third",
            "route": "implement_or_wire_effect_recipe",
            "reason": "missing ffmpeg lower third recipe",
            "status": "pending",
        }],
    }


def _effect_intent_plan():
    return {
        "artifact_role": "effect_intent_plan",
        "version": 1,
        "effects": [{
            "effect_id": "fx_page_turn",
            "role": "chapter_transition",
            "intent": "像實習報告翻頁進入下一段訓練回憶",
            "intensity": "medium",
            "target": {"beat_id": "b02", "segment_id": "2"},
            "visual_language": ["paper texture", "warm glow", "page turn"],
            "required_for_story": True,
            "must_preserve_proof": False,
            "allowed_backends": ["remotion_preview", "remotion_render"],
            "fallback": "simple fade",
        }, {
            "effect_id": "fx_lower",
            "role": "lower_third",
            "intent": "主任勉勵",
            "intensity": "low",
            "target": {"beat_id": "b01", "segment_id": "1"},
            "visual_language": ["clean lower third"],
            "required_for_story": False,
            "must_preserve_proof": True,
            "allowed_backends": ["ffmpeg_light_effects"],
            "fallback": "none",
        }],
    }


def _timeline():
    return {
        "clips": [
            {"segment": 1, "timeline_in_sec": 0.0, "timeline_out_sec": 2.5},
            {"segment": 2, "timeline_in_sec": 2.5, "timeline_out_sec": 6.25},
            {"segment": 2, "timeline_in_sec": 6.25, "timeline_out_sec": 7.0},
        ]
    }


class RemotionPromptPackTest(unittest.TestCase):
    def test_build_prompt_pack_only_for_remotion_adapter_requests(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        pack = build_remotion_prompt_pack(
            _effect_revision_request(),
            _effect_intent_plan(),
            timeline=_timeline(),
            output_dir="effects/remotion",
        )

        self.assertEqual(pack["artifact_role"], "remotion_prompt_pack")
        self.assertEqual(pack["version"], 1)
        self.assertEqual(pack["status"], "pending")
        self.assertEqual(pack["summary"]["job_count"], 1)
        job = pack["jobs"][0]
        self.assertEqual(job["job_id"], "rm_fx_page_turn")
        self.assertEqual(job["source_effect_id"], "fx_page_turn")
        self.assertEqual(job["component_family"], "page_turn_transition")
        self.assertEqual(job["timing"], {"start_sec": 2.5, "duration_sec": 4.5})
        self.assertIn("實習報告翻頁", job["prompt"])
        self.assertEqual(job["output"]["type"], "overlay_video")
        self.assertTrue(job["output"]["alpha"])
        self.assertTrue(job["output"]["target_file"].endswith("rm_fx_page_turn.mov"))
        self.assertEqual(job["acceptance"]["must_match_duration_sec"], 4.5)
        self.assertNotIn("fx_lower", json.dumps(pack, ensure_ascii=False))

    def test_prompt_pack_fails_closed_for_unknown_source_effect(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        request = _effect_revision_request()
        request["requests"][0]["source_effect_id"] = "fx_missing"
        with self.assertRaises(ValueError):
            build_remotion_prompt_pack(request, _effect_intent_plan(), timeline=_timeline())

    def test_prompt_pack_does_not_require_timeline_but_marks_timing_unknown(self):
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        pack = build_remotion_prompt_pack(_effect_revision_request(), _effect_intent_plan())
        job = pack["jobs"][0]
        self.assertEqual(job["timing"]["start_sec"], 0.0)
        self.assertEqual(job["timing"]["duration_sec"], 3.0)
        self.assertTrue(job["diagnostics"])

    def test_prompt_pack_cli_writes_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request = root / "effect_revision_request.json"
            plan = root / "effect_intent_plan.json"
            timeline = root / "timeline_build.json"
            out = root / "remotion_prompt_pack.json"
            request.write_text(json.dumps(_effect_revision_request()), encoding="utf-8")
            plan.write_text(json.dumps(_effect_intent_plan()), encoding="utf-8")
            timeline.write_text(json.dumps(_timeline()), encoding="utf-8")

            proc = subprocess.run([
                sys.executable,
                "video_tools.py",
                "remotion-prompt-pack",
                "--request", str(request),
                "--effect-intent-plan", str(plan),
                "--timeline", str(timeline),
                "--out", str(out),
                "--output-dir", "fx",
            ], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            written = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(written["artifact_role"], "remotion_prompt_pack")
            self.assertEqual(written["jobs"][0]["output"]["target_file"], "fx/rm_fx_page_turn.mov")


class RemotionWorkerOutputsTest(unittest.TestCase):
    def _worker_outputs(self, root):
        preview = root / "preview.mp4"
        rendered = root / "overlay.mov"
        preview.write_bytes(b"preview")
        rendered.write_bytes(b"rendered")
        return {
            "artifact_role": "remotion_worker_outputs",
            "version": 1,
            "jobs": [{
                "job_id": "rm_fx_page_turn",
                "source_effect_id": "fx_page_turn",
                "status": "rendered",
                "preview_file": str(preview),
                "rendered_asset": str(rendered),
                "duration_sec": 4.5,
                "backend": "remotion",
            }],
        }

    def test_validate_worker_outputs_accepts_matching_rendered_job(self):
        from video_pipeline_core.remotion_effects import (
            build_remotion_prompt_pack,
            validate_remotion_worker_outputs,
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pack = build_remotion_prompt_pack(
                _effect_revision_request(),
                _effect_intent_plan(),
                timeline=_timeline(),
                output_dir=str(root),
            )
            result = validate_remotion_worker_outputs(self._worker_outputs(root), pack)

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["summary"]["rendered_count"], 1)
        self.assertEqual(result["review_artifact"]["status"], "pending_review")
        self.assertEqual(result["review_artifact"]["items"][0]["source_effect_id"], "fx_page_turn")

    def test_validate_worker_outputs_fails_closed_on_missing_file_or_unknown_job(self):
        from video_pipeline_core.remotion_effects import (
            build_remotion_prompt_pack,
            validate_remotion_worker_outputs,
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pack = build_remotion_prompt_pack(
                _effect_revision_request(),
                _effect_intent_plan(),
                timeline=_timeline(),
                output_dir=str(root),
            )
            outputs = self._worker_outputs(root)
            outputs["jobs"][0]["rendered_asset"] = str(root / "missing.mov")
            result = validate_remotion_worker_outputs(outputs, pack)
            self.assertFalse(result["ok"])
            self.assertIn("rendered_asset", result["errors"][0])

            outputs = self._worker_outputs(root)
            outputs["jobs"][0]["job_id"] = "rm_unknown"
            result = validate_remotion_worker_outputs(outputs, pack)
            self.assertFalse(result["ok"])
            self.assertIn("unknown job_id", result["errors"][0])

    def test_validate_worker_outputs_cli_writes_review_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            from video_pipeline_core.remotion_effects import build_remotion_prompt_pack
            pack = build_remotion_prompt_pack(
                _effect_revision_request(),
                _effect_intent_plan(),
                timeline=_timeline(),
                output_dir=str(root),
            )
            pack_path = root / "remotion_prompt_pack.json"
            outputs_path = root / "remotion_worker_outputs.json"
            out_review = root / "remotion_effect_review.json"
            pack_path.write_text(json.dumps(pack), encoding="utf-8")
            outputs_path.write_text(json.dumps(self._worker_outputs(root)), encoding="utf-8")

            proc = subprocess.run([
                sys.executable,
                "video_tools.py",
                "remotion-worker-outputs",
                "--prompt-pack", str(pack_path),
                "--worker-outputs", str(outputs_path),
                "--out-review", str(out_review),
            ], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            review = json.loads(out_review.read_text(encoding="utf-8"))
            self.assertEqual(review["artifact_role"], "remotion_effect_review")
            self.assertEqual(review["status"], "pending_review")

    def test_command_catalog_exposes_remotion_effect_adapter_steps(self):
        commands = [
            "effect-revision-request",
            "effect-revision-draft",
            "remotion-prompt-pack",
            "remotion-worker-outputs",
        ]
        manifest = build_command_manifest(commands)
        workflow = build_workflow_manifest(commands)

        self.assertEqual(manifest["commands"]["remotion-prompt-pack"]["group"], "contract")
        self.assertIn("remotion_effect_adapter", workflow["workflows"])
        self.assertEqual([
            item for item in workflow["missing_commands"]
            if item["workflow"] == "remotion_effect_adapter"
        ], [])


if __name__ == "__main__":
    unittest.main()
