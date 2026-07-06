import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class BranchEnvTest(unittest.TestCase):
    def test_bootstrap_reads_known_repo_env_without_leaking_values(self):
        from video_pipeline_core.branch_env import bootstrap_branch_env, build_branch_env_probe

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "JAMENDO_CLIENT_ID=jamendo-secret\n"
                "PIXABAY_API_KEY=pixabay-secret\n"
                "IGNORED_SECRET=must-not-load\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                env = bootstrap_branch_env(repo_root=root)
                probe = build_branch_env_probe(repo_root=root, env=env)

        self.assertEqual(env["JAMENDO_CLIENT_ID"], "jamendo-secret")
        self.assertEqual(env["PIXABAY_API_KEY"], "pixabay-secret")
        self.assertNotIn("IGNORED_SECRET", env)
        self.assertTrue(probe["jamendo_client_id_present"])
        self.assertEqual(probe["jamendo_client_id_length"], len("jamendo-secret"))
        self.assertTrue(probe["pixabay_api_key_present"])
        self.assertEqual(probe["pixabay_api_key_length"], len("pixabay-secret"))
        serialized = json.dumps(probe, ensure_ascii=False)
        self.assertNotIn("jamendo-secret", serialized)
        self.assertNotIn("pixabay-secret", serialized)
        self.assertTrue(probe["secrets_redacted"])

    def test_existing_process_values_are_not_overwritten(self):
        from video_pipeline_core.branch_env import bootstrap_branch_env

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "JAMENDO_CLIENT_ID=from-dotenv\n"
                "PIXABAY_API_KEY=from-dotenv\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"JAMENDO_CLIENT_ID": "from-env"}, clear=True):
                env = bootstrap_branch_env(repo_root=root)

        self.assertEqual(env["JAMENDO_CLIENT_ID"], "from-env")
        self.assertEqual(env["PIXABAY_API_KEY"], "from-dotenv")

    def test_defaults_voxcpm_python_to_repo_venv_when_unset(self):
        from video_pipeline_core.branch_env import bootstrap_branch_env

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            venv_python = root / ".venv_voxcpm" / "Scripts" / "python.exe"
            venv_python.parent.mkdir(parents=True)
            venv_python.write_text("", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                env = bootstrap_branch_env(repo_root=root)

        self.assertEqual(Path(env["VOXCPM_PYTHON"]), venv_python)

    def test_discovers_ytdlp_from_path_when_ytdlp_path_unset(self):
        from video_pipeline_core.branch_env import bootstrap_branch_env, build_branch_env_probe

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            ytdlp = bin_dir / "yt-dlp.cmd"
            ytdlp.write_text("@echo off\necho 2026.07.06\n", encoding="utf-8")
            env = {
                "PATH": str(bin_dir),
                "PATHEXT": ".COM;.EXE;.BAT;.CMD",
                "ComSpec": os.environ.get("ComSpec", r"C:\Windows\System32\cmd.exe"),
                "SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"),
            }
            with patch.dict(os.environ, env, clear=True):
                env = bootstrap_branch_env(repo_root=root)
                probe = build_branch_env_probe(repo_root=root, env=env)

        self.assertEqual(Path(env["YTDLP_PATH"]), ytdlp)
        self.assertEqual(Path(probe["yt_dlp_path"]), ytdlp)
        self.assertTrue(probe["yt_dlp_version"])

    def test_voxcpm_runtime_tool_runs_directly_from_repo_root(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "voxcpm_runtime_check.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/voxcpm_runtime_check.py",
                    "--out",
                    str(out),
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok_to_execute"])
            self.assertEqual(
                Path(payload["python"]),
                repo / ".venv_voxcpm" / "Scripts" / "python.exe",
            )


if __name__ == "__main__":
    unittest.main()
