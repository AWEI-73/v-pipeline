import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core.soundtrack_providers import (
    download_candidate,
    import_url_with_ytdlp,
    search_soundtrack_providers,
)


def _plan():
    return {
        "artifact_role": "soundtrack_plan",
        "sections": [
            {
                "section_id": "warm_story",
                "music_role": "bgm",
                "vocal_policy": "instrumental_required",
                "energy_curve": "low",
                "source_type": "pixabay_music",
                "duration_sec": 60,
            },
            {
                "section_id": "mv_climax",
                "music_role": "song",
                "vocal_policy": "vocal_ok",
                "energy_curve": "high",
                "source_type": "jamendo_song",
                "duration_sec": 90,
            },
        ],
    }


class FakeResponse:
    def __init__(self, payload=None, data=b"fake-mp3"):
        self.payload = payload
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        if self.payload is not None:
            return json.dumps(self.payload).encode("utf-8")
        return self.data


class SoundtrackProvidersTest(unittest.TestCase):
    def test_jamendo_search_maps_tracks_to_deliverable_candidates(self):
        jamendo_payload = {
            "results": [
                {
                    "id": "123",
                    "name": "Run Forward",
                    "artist_name": "Open Band",
                    "duration": 123,
                    "audio": "https://audio.example/preview.mp3",
                    "audiodownload": "https://audio.example/download.mp3",
                    "audiodownload_allowed": True,
                    "shareurl": "https://jamendo.com/track/123",
                    "license_ccurl": "https://creativecommons.org/licenses/by-sa/3.0/",
                }
            ]
        }

        with patch("urllib.request.urlopen", return_value=FakeResponse(jamendo_payload)) as mocked:
            result = search_soundtrack_providers(
                _plan(),
                providers=["jamendo", "pixabay"],
                env={"JAMENDO_CLIENT_ID": "client", "PIXABAY_API_KEY": "pixabay"},
                limit=1,
            )

        candidates = result["candidates"]
        jamendo = next(item for item in candidates if item["provider"] == "jamendo")
        self.assertEqual(jamendo["section_id"], "mv_climax")
        self.assertEqual(jamendo["source_type"], "jamendo_song")
        self.assertTrue(jamendo["delivery_allowed"])
        self.assertEqual(jamendo["download_url"], "https://audio.example/download.mp3")
        self.assertEqual(jamendo["license_url"], "https://creativecommons.org/licenses/by-sa/3.0/")
        self.assertTrue(any("api.jamendo.com" in call.args[0].full_url for call in mocked.call_args_list))

        pixabay = next(item for item in candidates if item["provider"] == "pixabay")
        self.assertFalse(pixabay["delivery_allowed"])
        self.assertEqual(pixabay["status"], "provider_unavailable")
        self.assertIn("official audio API", pixabay["note"])

    def test_missing_jamendo_client_id_returns_provider_unavailable_without_network(self):
        with patch("urllib.request.urlopen") as mocked:
            result = search_soundtrack_providers(
                _plan(),
                providers=["jamendo"],
                env={},
                limit=1,
            )

        self.assertFalse(mocked.called)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["provider"], "jamendo")
        self.assertEqual(candidate["status"], "provider_unavailable")
        self.assertIn("JAMENDO_CLIENT_ID", candidate["note"])

    def test_download_candidate_writes_audio_manifest_and_handoff(self):
        candidate = {
            "candidate_id": "jamendo_mv_climax_123",
            "provider": "jamendo",
            "section_id": "mv_climax",
            "source_type": "jamendo_song",
            "title": "Run Forward",
            "artist": "Open Band",
            "download_url": "https://audio.example/download.mp3",
            "license_url": "https://creativecommons.org/licenses/by-sa/3.0/",
            "license_status": "license_metadata_present",
            "delivery_allowed": True,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("urllib.request.urlopen", return_value=FakeResponse(data=b"ID3 fake")):
                result = download_candidate(candidate, root)

            audio_path = Path(result["audio_file"])
            self.assertTrue(audio_path.is_file())
            self.assertEqual(audio_path.read_bytes(), b"ID3 fake")
            manifest = json.loads((root / "sound_license_manifest.json").read_text(encoding="utf-8"))
            handoff = json.loads((root / "audio_director_handoff.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["delivery_allowed"])
            self.assertTrue(handoff["ready_for_audio_director"])
            self.assertEqual(handoff["selected_audio_files"][0]["candidate_id"], "jamendo_mv_climax_123")

    def test_download_rejects_reference_only_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                download_candidate(
                    {
                        "candidate_id": "ref_1",
                        "provider": "youtube",
                        "source_type": "reference_only",
                        "delivery_allowed": False,
                        "download_url": "https://example.com/file.mp3",
                    },
                    tmp,
                )

    def test_import_url_with_ytdlp_records_internal_only_license_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_ytdlp = root / "yt-dlp.cmd"
            fake_ytdlp.write_text(
                "@echo off\r\n"
                "set out=\r\n"
                ":loop\r\n"
                "if \"%1\"==\"\" goto done\r\n"
                "if \"%1\"==\"-o\" set out=%2\r\n"
                "shift\r\n"
                "goto loop\r\n"
                ":done\r\n"
                "echo fake audio> \"%out%\"\r\n",
                encoding="utf-8",
            )
            result = import_url_with_ytdlp(
                "https://youtube.example/watch?v=abc",
                root,
                section_id="mv_climax",
                source_type="youtube_audio_library",
                usage_scope="internal_only",
                license_note="user confirmed internal classroom use",
                license_url="",
                ytdlp_path=str(fake_ytdlp),
            )

            self.assertTrue(Path(result["audio_file"]).is_file())
            self.assertTrue(result["audio_file"].endswith(".mp3"))
            manifest = json.loads((root / "sound_license_manifest.json").read_text(encoding="utf-8"))
            handoff = json.loads((root / "audio_director_handoff.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["selected_sources"][0]["usage_scope"], "internal_only")
            self.assertTrue(handoff["ready_for_audio_director"])
            self.assertEqual(handoff["selected_audio_files"][0]["source_type"], "youtube_audio_library")

    def test_import_url_accepts_license_url_without_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_ytdlp = root / "yt-dlp.cmd"
            fake_ytdlp.write_text(
                "@echo off\r\n"
                "set out=\r\n"
                ":loop\r\n"
                "if \"%1\"==\"\" goto done\r\n"
                "if \"%1\"==\"-o\" set out=%2\r\n"
                "shift\r\n"
                "goto loop\r\n"
                ":done\r\n"
                "echo fake audio> \"%out%\"\r\n",
                encoding="utf-8",
            )
            result = import_url_with_ytdlp(
                "https://youtube.example/watch?v=abc",
                root,
                section_id="warm_story",
                source_type="licensed_library",
                usage_scope="internal_only",
                license_note="",
                license_url="https://example.com/license",
                ytdlp_path=str(fake_ytdlp),
            )

            self.assertTrue(Path(result["audio_file"]).is_file())
            self.assertTrue(result["audio_file"].endswith(".mp3"))
            manifest = json.loads((root / "sound_license_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["selected_sources"][0]["license_url"], "https://example.com/license")

    def test_import_url_requires_license_note_or_url_for_deliverable_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                import_url_with_ytdlp(
                    "https://youtube.example/watch?v=abc",
                    tmp,
                    section_id="mv_climax",
                    source_type="youtube_audio_library",
                    usage_scope="internal_only",
                    license_note="",
                    license_url="",
                    ytdlp_path="yt-dlp",
                )

    def test_video_tools_provider_download_command_writes_selected_audio(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            source_audio = run / "source.mp3"
            source_audio.write_bytes(b"ID3 fake")
            candidates = {
                "artifact_role": "music_source_candidates",
                "candidates": [
                    {
                        "candidate_id": "jamendo_mv_climax_123",
                        "provider": "jamendo",
                        "section_id": "mv_climax",
                        "source_type": "jamendo_song",
                        "title": "Run Forward",
                        "artist": "Open Band",
                        "download_url": source_audio.as_uri(),
                        "license_url": "https://creativecommons.org/licenses/by-sa/3.0/",
                        "license_status": "license_metadata_present",
                        "delivery_allowed": True,
                    }
                ],
            }
            candidates_path = run / "music_source_candidates.json"
            candidates_path.write_text(json.dumps(candidates), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "soundtrack-provider-download",
                    "--candidates",
                    str(candidates_path),
                    "--candidate-id",
                    "jamendo_mv_climax_123",
                    "--out-dir",
                    str(run),
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((run / "audio" / "sources" / "jamendo_mv_climax_123.mp3").is_file())
            self.assertTrue((run / "sound_license_manifest.json").is_file())

    def test_video_tools_import_url_command_uses_ytdlp_fallback(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            fake_ytdlp = run / "yt-dlp.cmd"
            fake_ytdlp.write_text(
                "@echo off\r\n"
                "set out=\r\n"
                ":loop\r\n"
                "if \"%1\"==\"\" goto done\r\n"
                "if \"%1\"==\"-o\" set out=%2\r\n"
                "shift\r\n"
                "goto loop\r\n"
                ":done\r\n"
                "echo fake audio> \"%out%\"\r\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "soundtrack-import-url",
                    "--url",
                    "https://youtube.example/watch?v=abc",
                    "--section-id",
                    "mv_climax",
                    "--source-type",
                    "youtube_audio_library",
                    "--usage-scope",
                    "internal_only",
                    "--license-note",
                    "internal classroom use confirmed by user",
                    "--ytdlp-path",
                    str(fake_ytdlp),
                    "--out-dir",
                    str(run),
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((run / "sound_license_manifest.json").is_file())
            self.assertTrue((run / "audio_director_handoff.json").is_file())

    def test_video_tools_provider_search_writes_candidates_file(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            plan_path = run / "soundtrack_plan.json"
            plan_path.write_text(json.dumps(_plan()), encoding="utf-8")
            out = run / "music_source_candidates.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "soundtrack-provider-search",
                    "--plan",
                    str(plan_path),
                    "--out",
                    str(out),
                    "--providers",
                    "jamendo",
                    "--limit",
                    "1",
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("jamendo", payload["provider_status"])
            self.assertGreaterEqual(len(payload["candidates"]), 1)


if __name__ == "__main__":
    unittest.main()
