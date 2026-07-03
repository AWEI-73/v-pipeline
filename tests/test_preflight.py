import json
import tempfile
import unittest
from pathlib import Path

from tools import preflight


class PreflightTests(unittest.TestCase):
    def test_load_env_file_merges_dotenv_without_overriding_process_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "PEXELS_API_KEY=from-file\n"
                "PIXABAY_API_KEY=\"quoted\"\n"
                "EXISTING=from-file\n",
                encoding="utf-8",
            )

            merged = preflight.load_env_file(env_file, {"EXISTING": "from-env"})

            self.assertEqual(merged["PEXELS_API_KEY"], "from-file")
            self.assertEqual(merged["PIXABAY_API_KEY"], "quoted")
            self.assertEqual(merged["EXISTING"], "from-env")

    def test_lenient_allows_missing_api_keys_as_warnings(self):
        result = preflight.check_environment(
            env={},
            python_version=(3, 10, 16),
            which=lambda name: f"C:/bin/{name}.exe",
            find_spec=lambda name: object(),
            run_command=lambda args: "tool version 1.2.3",
        )

        self.assertEqual(result["status"], "warning")
        self.assertFalse(result["strict_pass"])
        self.assertIn("PEXELS_API_KEY", result["environment"]["missing_keys"])
        self.assertEqual(result["tools"]["ffmpeg"]["status"], "ok")
        self.assertEqual(result["tools"]["node"]["status"], "ok")

    def test_strict_fails_when_hard_requirement_is_missing(self):
        result = preflight.check_environment(
            env={"PEXELS_API_KEY": "present"},
            python_version=(3, 10, 16),
            which=lambda name: None if name == "ffmpeg" else f"C:/bin/{name}.exe",
            find_spec=lambda name: object(),
            run_command=lambda args: "tool version 1.2.3",
        )

        self.assertEqual(result["status"], "error")
        self.assertFalse(result["strict_pass"])
        self.assertEqual(result["tools"]["ffmpeg"]["status"], "missing")

    def test_main_writes_json_and_text_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_out = Path(tmp) / "preflight.json"
            text_out = Path(tmp) / "preflight.txt"

            code = preflight.main(
                [
                    "--json-out",
                    str(json_out),
                    "--summary-out",
                    str(text_out),
                ],
                env={"PEXELS_API_KEY": "present"},
                which=lambda name: f"C:/bin/{name}.exe",
                find_spec=lambda name: object(),
                run_command=lambda args: "tool version 1.2.3",
                python_version=(3, 10, 16),
            )

            self.assertEqual(code, 0)
            payload = json.loads(json_out.read_text(encoding="utf-8"))
            summary = text_out.read_text(encoding="utf-8")
            self.assertEqual(payload["python"]["version"], "3.10.16")
            self.assertIn("Capability summary", summary)
            self.assertIn("ffmpeg: ok", summary)


if __name__ == "__main__":
    unittest.main()
