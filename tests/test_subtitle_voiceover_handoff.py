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

    def test_blocks_voxcpm_unavailable_without_fallback_with_visible_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = {
                "artifact_role": "stage0_subtitle_voiceover_intent",
                "language": "zh-TW",
                "voiceover_required": True,
                "preferred_provider": "voxcpm",
                "fallback_allowed": False,
            }
            provider_plan = {
                "artifact_role": "voiceover_provider_plan",
                "requested_provider": "voxcpm",
                "selected_provider": "voxcpm",
                "provider_available": False,
                "provider_unavailable_reason": "voxcpm executable not found",
                "fallback_allowed": False,
                "errors": [{
                    "rule": "provider_unavailable",
                    "message": "VoxCPM provider entry was not found and fallback is disabled",
                }],
            }
            runtime_check = {
                "artifact_role": "voxcpm_runtime_check",
                "ok_to_execute": False,
                "python": "C:/Python/python.exe",
                "voxcpm_repo": "C:/repo/VoxCPM-main",
                "missing_modules": ["torch"],
                "gpu": {"available": False, "summary": "", "stderr": "nvidia-smi missing"},
            }

            result = accept_subtitle_voiceover_handoff(
                contract,
                narration_manifest={
                    "artifact_role": "narration_manifest",
                    "segments": [{"id": "n1", "audio_file": "missing.wav", "text": "hello"}],
                },
                voiceover_provider_plan=provider_plan,
                voxcpm_runtime_check=runtime_check,
                out_dir=root,
            )

            acceptance = result["subtitle_voiceover_handoff_acceptance"]
            self.assertFalse(acceptance["ok"])
            self.assertEqual(acceptance["next_action"], "needs-context")
            rules = {item["rule"] for item in acceptance["blocking"]}
            self.assertIn("voiceover_provider_unavailable", rules)
            self.assertIn("voiceover_audio_missing", rules)
            provider_block = next(item for item in acceptance["blocking"] if item["rule"] == "voiceover_provider_unavailable")
            self.assertEqual(provider_block["provider"], "voxcpm")
            self.assertIn("torch", provider_block["missing_modules"])
            handoff = result["subtitle_voiceover_build_handoff"]
            self.assertFalse(handoff["voiceover_ready"])
            self.assertEqual(handoff["provider_status"]["selected_provider"], "voxcpm")
            self.assertFalse(handoff["provider_status"]["fallback_allowed"])

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
            manifest = json.loads((root / "artifact_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["subtitle_voiceover_handoff_acceptance"],
                str(root / "subtitle_voiceover_handoff_acceptance.json"),
            )
            self.assertEqual(
                manifest["subtitle_voiceover_build_handoff"],
                str(root / "subtitle_voiceover_build_handoff.json"),
            )

    def test_cli_accepts_provider_plan_and_runtime_check_for_fail_closed_reason(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = _write_json(root, "subtitle_voiceover_contract.json", {
                "artifact_role": "stage0_subtitle_voiceover_intent",
                "language": "zh-TW",
                "voiceover_required": True,
                "preferred_provider": "voxcpm",
                "fallback_allowed": False,
            })
            provider_plan = _write_json(root, "voiceover_provider_plan.json", {
                "artifact_role": "voiceover_provider_plan",
                "selected_provider": "voxcpm",
                "provider_available": False,
                "provider_unavailable_reason": "local VoxCPM runtime missing torch",
                "fallback_allowed": False,
            })
            runtime_check = _write_json(root, "voxcpm_runtime_check.json", {
                "artifact_role": "voxcpm_runtime_check",
                "ok_to_execute": False,
                "python": "C:/Python/python.exe",
                "voxcpm_repo": "C:/repo/VoxCPM-main",
                "missing_modules": ["torch"],
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/subtitle_voiceover_handoff_accept.py",
                    "--contract",
                    str(contract),
                    "--voiceover-provider-plan",
                    str(provider_plan),
                    "--voxcpm-runtime-check",
                    str(runtime_check),
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

            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            acceptance = payload["subtitle_voiceover_handoff_acceptance"]
            self.assertFalse(acceptance["ok"])
            self.assertEqual(acceptance["next_action"], "needs-context")
            self.assertFalse(payload["subtitle_voiceover_build_handoff"]["voiceover_ready"])
            self.assertEqual(
                payload["subtitle_voiceover_build_handoff"]["provider_status"]["provider_unavailable_reason"],
                "local VoxCPM runtime missing torch",
            )


if __name__ == "__main__":
    unittest.main()
