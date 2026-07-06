import json
import subprocess
import tempfile
from pathlib import Path
import unittest

from video_pipeline_core.voiceover_provider import (
    build_voiceover_provider_plan,
    write_voiceover_provider_artifacts,
)


class VoiceoverProviderTests(unittest.TestCase):
    def _script(self, root: Path) -> Path:
        path = root / "script.json"
        path.write_text(
            json.dumps(
                [
                    {"segment": 1, "title": "開場", "text": "這是第一段旁白。"},
                    {"segment": 2, "title": "收束", "text": "這是第二段旁白。"},
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path

    def test_plan_only_falls_back_when_voxcpm_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = build_voiceover_provider_plan(
                script_path=self._script(root),
                out_dir=root / "voice",
                allow_fallback=True,
                voxcpm_bin=str(root / "missing-voxcpm.exe"),
                voxcpm_repo=root / "missing-voxcpm-repo",
            )
            self.assertEqual(payload["plan"]["selected_provider"], "legacy_edge_tts")
            self.assertTrue(payload["plan"]["fallback_used"])
            self.assertIn("voxcpm executable", payload["plan"]["fallback_reason"])
            self.assertFalse(payload["handoff"]["voiceover_ready"])
            self.assertEqual(payload["handoff"]["fallback"]["status"], "planned")
            written = write_voiceover_provider_artifacts(payload, root / "voice")
            self.assertTrue(Path(written["plan"]).exists())
            self.assertTrue(Path(written["handoff"]).exists())
            manifest = json.loads((root / "voice" / "artifact_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["voiceover_provider_plan"], written["plan"])
            self.assertEqual(manifest["subtitle_voiceover_build_handoff"], written["handoff"])
            self.assertEqual(
                manifest["artifacts"]["subtitle_voiceover_build_handoff"]["status"],
                "planned_or_blocked",
            )

    def test_no_fallback_fails_closed_when_voxcpm_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = build_voiceover_provider_plan(
                script_path=self._script(root),
                out_dir=root / "voice",
                allow_fallback=False,
                voxcpm_bin=str(root / "missing-voxcpm.exe"),
                voxcpm_repo=root / "missing-voxcpm-repo",
            )
            self.assertEqual(payload["plan"]["selected_provider"], "voxcpm")
            self.assertFalse(payload["plan"]["provider_available"])
            self.assertFalse(payload["handoff"]["voiceover_ready"])
            self.assertEqual(payload["plan"]["errors"][0]["rule"], "provider_unavailable")

    def test_fake_voxcpm_runner_marks_voiceover_ready(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fake_bin = root / "voxcpm.cmd"
            fake_bin.write_text("@echo off\r\n", encoding="utf-8")

            def runner(command, timeout_sec):
                output = Path(command[command.index("--output") + 1])
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"fake wav")
                return subprocess.CompletedProcess(command, 0, "", "")

            payload = build_voiceover_provider_plan(
                script_path=self._script(root),
                out_dir=root / "voice",
                voxcpm_bin=str(fake_bin),
                execute=True,
                runner=runner,
            )
            self.assertEqual(payload["plan"]["selected_provider"], "voxcpm")
            self.assertTrue(payload["handoff"]["voiceover_ready"])
            self.assertEqual(len(payload["handoff"]["voice_files"]), 2)
            self.assertTrue(all(seg["status"] == "rendered" for seg in payload["plan"]["segments"]))

    def test_voxcpm_auto_failure_retries_segment_on_cpu(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fake_bin = root / "voxcpm.cmd"
            fake_bin.write_text("@echo off\r\n", encoding="utf-8")
            calls = []

            def runner(command, timeout_sec):
                calls.append(list(command))
                output = Path(command[command.index("--output") + 1])
                device = command[command.index("--device") + 1]
                if device == "auto":
                    return subprocess.CompletedProcess(command, 3221225477, "", "cuda access violation")
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"fake wav")
                return subprocess.CompletedProcess(command, 0, "", "")

            payload = build_voiceover_provider_plan(
                script_path=self._script(root),
                out_dir=root / "voice",
                voxcpm_bin=str(fake_bin),
                execute=True,
                runner=runner,
            )

            self.assertTrue(payload["handoff"]["voiceover_ready"])
            self.assertEqual(len(calls), 4)
            first = payload["plan"]["segments"][0]
            self.assertEqual(first["status"], "rendered")
            self.assertEqual(first["retry"]["retry_device"], "cpu")
            self.assertEqual(first["retry"]["primary_returncode"], 3221225477)
            self.assertEqual(calls[0][calls[0].index("--device") + 1], "auto")
            self.assertEqual(calls[1][calls[1].index("--device") + 1], "cpu")

    def test_local_voxcpm_repo_entrypoint_is_supported(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "VoxCPM-main"
            cli = repo / "src" / "voxcpm" / "cli.py"
            cli.parent.mkdir(parents=True)
            cli.write_text("print('fake cli')\n", encoding="utf-8")
            payload = build_voiceover_provider_plan(
                script_path=self._script(root),
                out_dir=root / "voice",
                voxcpm_bin=str(root / "missing-voxcpm.exe"),
                voxcpm_repo=repo,
            )
            self.assertEqual(payload["plan"]["selected_provider"], "voxcpm")
            self.assertTrue(payload["plan"]["provider_available"])
            self.assertEqual(payload["plan"]["provider_entry_type"], "local_repo")
            command = payload["plan"]["segments"][0]["command"]
            self.assertIn("runpy.run_path", command[2])
            self.assertIn("src\\\\voxcpm\\\\cli.py", command[2])

    def test_local_voxcpm_repo_can_use_dedicated_python(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "VoxCPM-main"
            cli = repo / "src" / "voxcpm" / "cli.py"
            cli.parent.mkdir(parents=True)
            cli.write_text("print('fake cli')\n", encoding="utf-8")
            fake_python = root / "python.exe"
            fake_python.write_text("", encoding="utf-8")
            payload = build_voiceover_provider_plan(
                script_path=self._script(root),
                out_dir=root / "voice",
                voxcpm_bin=str(root / "missing-voxcpm.exe"),
                voxcpm_repo=repo,
                voxcpm_python=fake_python,
            )
            self.assertEqual(payload["plan"]["provider_python"], str(fake_python))
            self.assertEqual(payload["plan"]["segments"][0]["command"][0], str(fake_python))


if __name__ == "__main__":
    unittest.main()
