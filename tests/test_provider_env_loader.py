import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core import vt_stock
from video_pipeline_core.vt_core import ToolError


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps({"videos": []}).encode("utf-8")


class ProviderEnvLoaderTest(unittest.TestCase):
    def test_pexels_provider_reads_same_repo_dotenv_as_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".env").write_text("PEXELS_API_KEY=from-dotenv\n", encoding="utf-8")
            captured = {}

            def fake_urlopen(request, timeout):
                captured["authorization"] = request.headers.get("Authorization")
                captured["timeout"] = timeout
                return _FakeResponse()

            with patch.dict("os.environ", {}, clear=True), \
                 patch("video_pipeline_core.env_loader.REPO_ROOT", repo), \
                 patch("urllib.request.urlopen", fake_urlopen):
                try:
                    result = vt_stock._pexels_video_candidates("city", limit=1)
                except ToolError as exc:  # pragma: no cover - should fail before fix
                    self.fail(f"provider did not load repo .env: {exc}")

        self.assertEqual(result, [])
        self.assertEqual(captured["authorization"], "from-dotenv")
        self.assertEqual(captured["timeout"], 30)


if __name__ == "__main__":
    unittest.main()
