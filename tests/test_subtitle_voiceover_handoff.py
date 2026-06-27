import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.subtitle_voiceover_handoff import accept_subtitle_voiceover_handoff


def _write_json(root: Path, name: str, payload: dict):
    path = root / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


class SubtitleVoiceoverHandoffTest(unittest.TestCase):
    def test_accepts_subtitles_and_voiceover_evidence_for_build_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            srt = root / "subtitles.srt"
            voice = root / "voiceover.wav"
            srt.write_text("1\n00:00:00,000 --> 00:00:02,000\n開始\n", encoding="utf-8")
            voice.write_bytes(b"RIFF voice")
            contract = {
                "artifact_role": "stage0_subtitle_voiceover_intent",
                "language": "zh-TW",
                "subtitle_required": True,
                "voiceover_required": True,
            }
            caption_audit = {"artifact_role": "caption_audit", "pass": True, "caption_count": 1}
            narration_manifest = {
                "artifact_role": "narration_manifest",
                "segments": [{"id": "n1", "audio_file": str(voice), "text": "開始"}],
            }

            result = accept_subtitle_voiceover_handoff(
                contract,
                caption_audit=caption_audit,
                narration_manifest=narration_manifest,
                subtitles_path=srt,
                out_dir=root,
            )

            self.assertTrue(result["subtitle_voiceover_handoff_acceptance"]["ok"])
            handoff = result["subtitle_voiceover_build_handoff"]
            self.assertTrue(handoff["subtitle_ready"])
            self.assertTrue(handoff["voiceover_ready"])
            self.assertEqual(handoff["language"], "zh-TW")
            self.assertEqual(handoff["subtitles"], str(srt))
            self.assertEqual(handoff["narration_manifest"], str(root / "narration_manifest.json"))
            self.assertTrue((root / "subtitle_voiceover_handoff_acceptance.json").is_file())
            self.assertTrue((root / "subtitle_voiceover_build_handoff.json").is_file())
            self.assertTrue((root / "narration_manifest.json").is_file())

    def test_blocks_required_subtitle_without_caption_audit_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            srt = root / "subtitles.srt"
            srt.write_text("1\n00:00:00,000 --> 00:00:02,000\n字幕\n", encoding="utf-8")

            result = accept_subtitle_voiceover_handoff(
                {"subtitle_required": True, "voiceover_required": False},
                caption_audit={"artifact_role": "caption_audit", "pass": False},
                subtitles_path=srt,
                out_dir=root,
            )

            self.assertFalse(result["subtitle_voiceover_handoff_acceptance"]["ok"])
            rules = {item["rule"] for item in result["subtitle_voiceover_handoff_acceptance"]["blocking"]}
            self.assertIn("caption_audit_not_passed", rules)
            self.assertFalse(result["subtitle_voiceover_build_handoff"]["subtitle_ready"])

    def test_cli_writes_acceptance_and_build_handoff(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            srt = root / "subtitles.srt"
            srt.write_text("1\n00:00:00,000 --> 00:00:02,000\n開始\n", encoding="utf-8")
            contract = _write_json(root, "subtitle_voiceover_contract.json", {
                "artifact_role": "stage0_subtitle_voiceover_intent",
                "language": "zh-TW",
                "subtitle_required": True,
                "voiceover_required": False,
            })
            caption = _write_json(root, "caption_audit.json", {
                "artifact_role": "caption_audit",
                "pass": True,
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/subtitle_voiceover_handoff_accept.py",
                    "--contract",
                    str(contract),
                    "--caption-audit",
                    str(caption),
                    "--subtitles",
                    str(srt),
                    "--out-dir",
                    str(root),
                    "--json",
                ],
                cwd=repo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["subtitle_voiceover_handoff_acceptance"]["ok"])
            self.assertTrue((root / "subtitle_voiceover_handoff_acceptance.json").is_file())
            self.assertTrue((root / "subtitle_voiceover_build_handoff.json").is_file())


if __name__ == "__main__":
    unittest.main()
