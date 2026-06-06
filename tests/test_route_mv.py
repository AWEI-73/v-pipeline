"""route.py MV mode (roadmap #7 route↔MV).

These cover the dispatch/report logic with a pre-written state.json so they never
invoke the heavy mv_chain (no librosa/ffmpeg/VLM needed).
"""
import json
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import route


def _args(out, material_db=None, music=None):
    return types.SimpleNamespace(script="x.json", out=out, material_db=material_db,
                                 music=music, verbose=False)


class RouteMvTest(unittest.TestCase):
    def test_requires_db_and_music(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(route._route_mv(_args(d)), 2)

    def test_await_material_reports_without_running(self):
        with tempfile.TemporaryDirectory() as d:
            state = {"mode": "mv", "next_action": "await_material", "final": None,
                     "blocking": [{"segment": 2, "reason": "必放『所長』無素材"}],
                     "review_points": [{"segment": 1, "reason": "開場高權重"}],
                     "qa": {"audio_pairing": 75, "audio_issues": []}}
            with open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
                json.dump(state, f)
            # db/music present so it gets past the guard; state present so no mv_chain run
            rc = route._route_mv(_args(d, material_db="db.json", music="m.mp3"))
            self.assertEqual(rc, 0)

    def test_done_path(self):
        with tempfile.TemporaryDirectory() as d:
            state = {"mode": "mv", "next_action": None, "final": f"{d}/final.mp4",
                     "blocking": [], "review_points": [],
                     "qa": {"audio_pairing": 100, "audio_issues": []}}
            with open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
                json.dump(state, f)
            self.assertEqual(route._route_mv(_args(d, material_db="db.json", music="m.mp3")), 0)

    def test_run_mv_routes_segment_contract_through_adapter(self):
        with tempfile.TemporaryDirectory() as d:
            contract = Path(d) / "segment_contract.json"
            contract.write_text(json.dumps({
                "segments": [{"core": {"segment": 1}, "material_fit": {"intent": "cover"}}]
            }), encoding="utf-8")
            calls = []

            def fake_run_contract(contract_arg, **kwargs):
                calls.append((contract_arg, kwargs))
                Path(kwargs["out_path"]).write_bytes(b"mp4")
                return {"ok": True}

            with patch("video_pipeline_core.contract_adapter.run_contract", fake_run_contract):
                rc = route._run_mv(str(contract), d, "materials_db.json", "music.mp3")

            self.assertEqual(rc, 0)
            self.assertEqual(calls[0][0], str(contract))
            self.assertEqual(calls[0][1]["material_db"], "materials_db.json")
            self.assertEqual(calls[0][1]["music_path"], "music.mp3")
            self.assertEqual(calls[0][1]["mat_dir"], d)

    def test_segment_contract_detection_does_not_match_legacy_script(self):
        self.assertFalse(route._looks_like_segment_contract([{"segment": 1}]))
        self.assertFalse(route._looks_like_segment_contract({"segments": [{"segment": 1}]}))
        self.assertTrue(route._looks_like_segment_contract({
            "segments": [{"core": {}, "material_fit": {}}]
        }))


if __name__ == "__main__":
    unittest.main()
