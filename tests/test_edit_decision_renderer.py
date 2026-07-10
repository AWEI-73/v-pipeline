import importlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _renderer_module():
    path = ROOT / "video_pipeline_core" / "edit_decision_renderer.py"
    return importlib.import_module("video_pipeline_core.edit_decision_renderer") if path.is_file() else None


class EditDecisionRendererTest(unittest.TestCase):
    def _make_media(self, root):
        video = root / "source.mp4"
        audio = root / "music.wav"
        for command in (
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x180:d=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)],
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=2", str(audio)],
        ):
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
        return video, audio

    def test_renders_canonical_decision_with_owned_manifest_and_streams(self):
        renderer = _renderer_module()
        self.assertIsNotNone(renderer, "canonical edit-decision renderer module is required")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video, audio = self._make_media(root)
            cuts = []
            for index in range(8):
                timeline_in = round(index * 0.226, 3)
                timeline_out = 2.0 if index == 7 else round((index + 1) * 0.226, 3)
                if index % 2 == 0:
                    cuts.append({"id": f"real_{index}", "asset_id": "accepted_video", "source_type": "video", "timeline_in_sec": timeline_in, "timeline_out_sec": timeline_out, "in_seconds": 0.0, "out_seconds": timeline_out - timeline_in})
                else:
                    cuts.append({"id": f"black_{index}", "source_type": "generated_background", "generated_background": {"color": "black"}, "timeline_in_sec": timeline_in, "timeline_out_sec": timeline_out})
            decision = {
                "artifact_role": "edit_decision_plan",
                "settings": {"fps": 30, "resolution": "1920x1080"},
                "cuts": cuts,
                "overlays": [{"id": "title", "kind": "text", "text": {"main": "ABC"}, "treatment": "progressive_typewriter", "start_sec": 0.0, "end_sec": 1.0}],
                "transitions": [{"type": "hard_cut", "at_sec": 1.0}],
                "audio": {"music": {"asset_id": "accepted_bgm"}},
            }
            timeline = {"settings": {"fps": 30, "resolution": "1920x1080"}, "clips": decision["cuts"], "overlays": decision["overlays"], "transitions": decision["transitions"]}
            result = renderer.render_edit_decision(
                decision,
                timeline,
                run_dir=root / "run",
                accepted_inputs=[
                    {"asset_id": "accepted_video", "source_path": str(video), "accepted": True, "kind": "video"},
                    {"asset_id": "accepted_bgm", "source_path": str(audio), "accepted": True, "kind": "audio"},
                ],
            )

            run = root / "run"
            self.assertTrue((run / "timeline_build.json").is_file())
            self.assertTrue((run / "render_handoff.json").is_file())
            self.assertTrue((run / "render_input_manifest.json").is_file())
            self.assertTrue((run / "final.mp4").is_file())
            handoff = json.loads((run / "render_handoff.json").read_text(encoding="utf-8"))
            self.assertTrue(handoff["ok"])
            self.assertEqual(handoff["owner"], "main-pipeline")
            self.assertFalse(handoff["final_delivery_claimed"])
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json", str(run / "final.mp4")],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(probe.returncode, 0, probe.stderr)
            streams = json.loads(probe.stdout)["streams"]
            self.assertEqual({stream["codec_type"] for stream in streams}, {"video", "audio"})
            self.assertLessEqual(abs(float(json.loads(probe.stdout)["format"]["duration"]) - 2.0), 1.0 / 30.0)
            self.assertTrue(result["ok"], result)

    def test_motion_graphics_contract_propagates_reveal_complete_sec(self):
        renderer = _renderer_module()
        self.assertIsNotNone(renderer, "canonical edit-decision renderer module is required")

        contract = renderer._motion_graphics_contract([{
            "id": "title",
            "kind": "text",
            "text": {"main": "ABC"},
            "treatment": "progressive_typewriter",
            "start_sec": 3.5,
            "reveal_complete_sec": 9.0,
            "end_sec": 11.0,
        }])

        self.assertEqual(contract["items"][0]["timing"]["reveal_complete_sec"], 9.0)

    def test_rejects_invalid_reveal_complete_sec_before_render(self):
        renderer = _renderer_module()
        self.assertIsNotNone(renderer, "canonical edit-decision renderer module is required")
        for reveal_complete_sec in (0.0, 1.1):
            with self.subTest(reveal_complete_sec=reveal_complete_sec):
                cuts = [{
                    "id": "black",
                    "source_type": "generated_background",
                    "generated_background": {"color": "black"},
                    "timeline_in_sec": 0.0,
                    "timeline_out_sec": 1.0,
                    "in_seconds": 0.0,
                }]
                decision = {
                    "artifact_role": "edit_decision_plan",
                    "settings": {"fps": 30, "resolution": "1920x1080"},
                    "cuts": cuts,
                    "overlays": [{
                        "id": "title",
                        "kind": "text",
                        "text": {"main": "ABC"},
                        "treatment": "progressive_typewriter",
                        "start_sec": 0.0,
                        "reveal_complete_sec": reveal_complete_sec,
                        "end_sec": 1.0,
                    }],
                    "transitions": [],
                    "audio": {"music": {"asset_id": "accepted_bgm"}},
                }
                timeline = {
                    "settings": {"fps": 30, "resolution": "1920x1080"},
                    "clips": cuts,
                    "overlays": decision["overlays"],
                    "transitions": [],
                }

                with self.assertRaisesRegex(renderer.EditDecisionRenderError, "reveal_complete_sec"):
                    renderer._validate_composition(
                        decision,
                        timeline,
                        {"accepted_bgm": {"kind": "audio"}},
                    )
