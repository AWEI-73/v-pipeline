"""Tests for platform_tools.py — cross-platform executable resolver."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core import platform_tools
from video_pipeline_core.vt_core import ToolError


class ResolvePythonTest(unittest.TestCase):
    def test_windows_returns_python(self):
        with patch.object(platform_tools, "_is_windows", return_value=True):
            self.assertEqual(platform_tools.resolve_python(), "python")

    def test_linux_returns_python3(self):
        with patch.object(platform_tools, "_is_windows", return_value=False):
            self.assertEqual(platform_tools.resolve_python(), "python3")


class ResolveExecutableTest(unittest.TestCase):
    """Test the generic _resolve_executable helper."""

    def test_env_var_takes_priority(self):
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            fake = f.name
        try:
            with patch.dict(os.environ, {"TEST_TOOL": fake}):
                result = platform_tools._resolve_executable(
                    "TEST_TOOL", ["nonexistent_tool_xyz"], guidance=""
                )
            self.assertEqual(result, fake)
        finally:
            os.unlink(fake)

    def test_which_fallback(self):
        # python/python3 should always be findable
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FFMPEG_PATH", None)
            # We test with "python" which is always on PATH
            result = platform_tools._resolve_executable(
                "NONEXISTENT_ENV_VAR_XYZ", ["python"], guidance=""
            )
            self.assertIn("python", result.lower())

    def test_missing_tool_raises_tool_error(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NONEXISTENT_ENV_XYZ", None)
            with self.assertRaises(ToolError) as ctx:
                platform_tools._resolve_executable(
                    "NONEXISTENT_ENV_XYZ",
                    ["completely_nonexistent_tool_xyz_abc_123"],
                    guidance="Install it somehow.",
                )
            self.assertIn("Install it somehow", str(ctx.exception))


class ResolveFfmpegTest(unittest.TestCase):
    def test_env_override(self):
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            fake = f.name
        try:
            with patch.dict(os.environ, {"FFMPEG_PATH": fake}):
                self.assertEqual(platform_tools.resolve_ffmpeg(), fake)
        finally:
            os.unlink(fake)


class ResolveTempDirTest(unittest.TestCase):
    def test_default_is_system_temp(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("VIDEO_PIPELINE_TEMP", None)
            result = platform_tools.resolve_temp_dir()
            self.assertTrue(Path(result).is_dir())

    def test_env_override(self):
        with tempfile.TemporaryDirectory() as d:
            custom = os.path.join(d, "my_temp")
            with patch.dict(os.environ, {"VIDEO_PIPELINE_TEMP": custom}):
                result = platform_tools.resolve_temp_dir()
                self.assertEqual(result, custom)
                self.assertTrue(Path(custom).is_dir())


class ResolveOllamaUrlTest(unittest.TestCase):
    def test_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OLLAMA_URL", None)
            self.assertEqual(platform_tools.resolve_ollama_url(), "http://localhost:11434")

    def test_env_override(self):
        with patch.dict(os.environ, {"OLLAMA_URL": "http://gpu-box:11434"}):
            self.assertEqual(platform_tools.resolve_ollama_url(), "http://gpu-box:11434")


class ResolveOllamaTest(unittest.TestCase):
    def test_env_override(self):
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            fake = f.name
        try:
            with patch.dict(os.environ, {"OLLAMA_PATH": fake}):
                self.assertEqual(platform_tools.resolve_ollama(), fake)
        finally:
            os.unlink(fake)


class ResolveFontTest(unittest.TestCase):
    def test_env_override(self):
        with tempfile.NamedTemporaryFile(suffix=".ttc", delete=False) as f:
            fake = f.name
        try:
            with patch.dict(os.environ, {"VIDEO_PIPELINE_FONT": fake}):
                self.assertEqual(platform_tools.resolve_font(), fake)
        finally:
            os.unlink(fake)

    def test_missing_font_raises_tool_error(self):
        with patch.dict(os.environ, {"VIDEO_PIPELINE_FONT": "/nonexistent/font.ttc"}):
            # env set but file missing → fall through to platform search
            # If platform search also fails, ToolError
            with patch.object(platform_tools, "_is_windows", return_value=True), \
                 patch("pathlib.Path.is_file", return_value=False):
                with self.assertRaises(ToolError):
                    platform_tools.resolve_font()


if __name__ == "__main__":
    unittest.main()
