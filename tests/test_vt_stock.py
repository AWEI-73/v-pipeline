import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core import vt_stock


class VtStockTest(unittest.TestCase):
    def test_fetch_stock_video_uses_pexels_first(self):
        seen = []

        def fake_download(url, out_path):
            seen.append(url)
            Path(out_path).write_bytes(b"video")
            return True

        with tempfile.TemporaryDirectory() as d, \
             patch("video_pipeline_core.vt_stock._pexels_video_candidates", return_value=[
                 {"provider": "pexels", "download_url": "https://pexels.example/a.mp4", "duration": 5}
             ]), \
             patch("video_pipeline_core.vt_stock._pixabay_video_candidates", return_value=[
                 {"provider": "pixabay", "download_url": "https://pixabay.example/b.mp4", "duration": 5}
             ]), \
             patch("video_pipeline_core.vt_stock._download_url", fake_download):
            out = Path(d) / "stock.mp4"
            result = vt_stock.fetch_stock_video("work truck", out)
        self.assertEqual(result, out)
        self.assertEqual(seen, ["https://pexels.example/a.mp4"])

    def test_fetch_stock_video_falls_back_to_pixabay(self):
        seen = []

        def fake_download(url, out_path):
            seen.append(url)
            Path(out_path).write_bytes(b"video")
            return True

        with tempfile.TemporaryDirectory() as d, \
             patch("video_pipeline_core.vt_stock._pexels_video_candidates", return_value=[]), \
             patch("video_pipeline_core.vt_stock._pixabay_video_candidates", return_value=[
                 {"provider": "pixabay", "download_url": "https://pixabay.example/b.mp4", "duration": 8}
             ]), \
             patch("video_pipeline_core.vt_stock._download_url", fake_download):
            out = Path(d) / "stock.mp4"
            result = vt_stock.fetch_stock_video("clean team", out)
        self.assertEqual(result, out)
        self.assertEqual(seen, ["https://pixabay.example/b.mp4"])

    def test_fetch_stock_video_filters_min_duration_across_providers(self):
        with tempfile.TemporaryDirectory() as d, \
             patch("video_pipeline_core.vt_stock._pexels_video_candidates", return_value=[
                 {"provider": "pexels", "download_url": "https://pexels.example/short.mp4", "duration": 2}
             ]), \
             patch("video_pipeline_core.vt_stock._pixabay_video_candidates", return_value=[]), \
             patch("video_pipeline_core.vt_stock._download_url", return_value=True):
            result = vt_stock.fetch_stock_video("short clip", Path(d) / "stock.mp4", min_dur=5)
        self.assertIsNone(result)

    def test_fetch_stock_video_prefers_relevance_order_over_duration(self):
        """Regression: candidates arrive in API relevance order; the first eligible
        one must win even when a later (less relevant) candidate is much longer
        (the ai-video 'robot dance' failure)."""
        seen = []

        def fake_download(url, out_path):
            seen.append(url)
            Path(out_path).write_bytes(b"video")
            return True

        with tempfile.TemporaryDirectory() as d, \
             patch("video_pipeline_core.vt_stock._pexels_video_candidates", return_value=[
                 {"provider": "pexels", "download_url": "https://pexels.example/on-topic-short.mp4", "duration": 12},
                 {"provider": "pexels", "download_url": "https://pexels.example/off-topic-long.mp4", "duration": 58},
             ]), \
             patch("video_pipeline_core.vt_stock._pixabay_video_candidates", return_value=[]), \
             patch("video_pipeline_core.vt_stock._download_url", fake_download):
            out = Path(d) / "stock.mp4"
            result = vt_stock.fetch_stock_video("team workspace discussion", out, min_dur=5)
        self.assertEqual(result, out)
        self.assertEqual(seen, ["https://pexels.example/on-topic-short.mp4"])

    def test_fetch_stock_video_skips_too_short_then_takes_next_relevant(self):
        """min_dur stays an eligibility filter: skip too-short candidates but keep
        relevance order among the eligible rest."""
        seen = []

        def fake_download(url, out_path):
            seen.append(url)
            Path(out_path).write_bytes(b"video")
            return True

        with tempfile.TemporaryDirectory() as d, \
             patch("video_pipeline_core.vt_stock._pexels_video_candidates", return_value=[
                 {"provider": "pexels", "download_url": "https://pexels.example/too-short.mp4", "duration": 3},
                 {"provider": "pexels", "download_url": "https://pexels.example/next-relevant.mp4", "duration": 10},
                 {"provider": "pexels", "download_url": "https://pexels.example/longest.mp4", "duration": 60},
             ]), \
             patch("video_pipeline_core.vt_stock._pixabay_video_candidates", return_value=[]), \
             patch("video_pipeline_core.vt_stock._download_url", fake_download):
            out = Path(d) / "stock.mp4"
            result = vt_stock.fetch_stock_video("bright office", out, min_dur=5)
        self.assertEqual(result, out)
        self.assertEqual(seen, ["https://pexels.example/next-relevant.mp4"])

    def test_fetch_stock_video_with_provider_returns_tuple(self):
        with tempfile.TemporaryDirectory() as d, \
             patch("video_pipeline_core.vt_stock._pexels_video_candidates", return_value=[]), \
             patch("video_pipeline_core.vt_stock._pixabay_video_candidates", return_value=[
                 {"provider": "pixabay", "download_url": "https://pixabay.example/b.mp4", "duration": 8}
             ]), \
             patch("video_pipeline_core.vt_stock._download_url", return_value=True):
            out = Path(d) / "stock.mp4"
            result_path, provider = vt_stock.fetch_stock_video_with_provider("clean team", out)
        self.assertEqual(result_path, out)
        self.assertEqual(provider, "pixabay")


if __name__ == "__main__":
    unittest.main()
