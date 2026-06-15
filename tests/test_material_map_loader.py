"""M6e.1 — the single canonical material_map loader.

A relative `material_map` resolves against the materials_db.json directory (never
the process cwd), so supply-review, the pre-BUILD gate, and the BUILD render path
all see the SAME maps. Declared-but-bad maps are fail-closed; absent keys are
skipped; absolute paths stay compatible.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core import contract_adapter as ca
from video_pipeline_core import mv_cut
from video_pipeline_core import project_material_map as pmm
from video_pipeline_core.material_retrieval import plan_ranked_windows


def _map_obj(asset_id="clip", source="a.mp4", end=6.0, caption="主任講話"):
    return {"asset_id": asset_id, "asset_type": "video", "source": source,
            "duration_sec": end, "scenes": [{"start": 0.0, "end": end, "caption": caption}]}


def _project(d, *, material_map="maps/clip.map.json", map_obj=None, write_map=True):
    """A materials_db.json with a RELATIVE material_map, in project dir d."""
    d = Path(d)
    if write_map and material_map is not None:
        mp = d / material_map
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(json.dumps(map_obj or _map_obj()), encoding="utf-8")
    db = d / "materials_db.json"
    db.write_text(json.dumps({"files": [{"path": "a.mp4", "material_map": material_map}]}
                             if material_map is not None else {"files": [{"path": "a.mp4"}]}),
                  encoding="utf-8")
    return str(db)


class RelativePathTest(unittest.TestCase):
    def test_A_all_consumers_load_same_map_from_unrelated_cwd(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as alien:
            db = _project(d)
            payload, _ = pmm.load_material_db(db)
            db_dir = Path(db).parent
            old = os.getcwd()
            try:
                os.chdir(alien)                       # nothing relevant in cwd
                via_canonical, e1 = pmm.material_maps_from_db(db)
                via_gate_loader, e2 = ca._load_current_material_maps(payload, db_dir)
                via_build = mv_cut._load_material_maps(payload, db_dir)
            finally:
                os.chdir(old)
            self.assertIsNone(e1); self.assertIsNone(e2)
            ids = lambda ms: [m["asset_id"] for m in ms]
            self.assertEqual(ids(via_canonical), ["clip"])
            self.assertEqual(ids(via_gate_loader), ["clip"])    # same maps the gate sees
            self.assertEqual(ids(via_build), ["clip"])          # same maps BUILD renders

    def test_B_relative_map_yields_map_ranked_window_not_gap(self):
        with tempfile.TemporaryDirectory() as d:
            db = _project(d, map_obj=_map_obj(source="real.mp4", caption="主任對學員的期勉講話"))
            maps, err = pmm.material_maps_from_db(db)
            self.assertIsNone(err)
            seg = {"segment": 1, "material_fit": {"visual_desc": "主任對學員的期勉講話"}}
            slots = plan_ranked_windows(seg, maps, limit=1, clip_dur=3.0)
            self.assertTrue(slots and slots[0]["source"] == "real.mp4")   # not a silent GAP

    def test_C_missing_corrupt_or_dir_map_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            # missing
            db = _project(d, material_map="maps/nope.map.json", write_map=False)
            _, err = pmm.material_maps_from_db(db)
            self.assertTrue(err and "not found" in err)
        with tempfile.TemporaryDirectory() as d:
            # corrupt
            (Path(d) / "maps").mkdir()
            (Path(d) / "maps" / "clip.map.json").write_text("{ bad", encoding="utf-8")
            db = _project(d, write_map=False)
            _, err = pmm.material_maps_from_db(db)
            self.assertTrue(err and ("read/parsed" in err or "malformed" in err))
        with tempfile.TemporaryDirectory() as d:
            # directory
            (Path(d) / "maps" / "clip.map.json").mkdir(parents=True)
            db = _project(d, write_map=False)
            _, err = pmm.material_maps_from_db(db)
            self.assertTrue(err and "directory" in err)

    def test_D_absolute_map_path_still_works(self):
        with tempfile.TemporaryDirectory() as d:
            mp = Path(d) / "abs.map.json"
            mp.write_text(json.dumps(_map_obj(asset_id="abs")), encoding="utf-8")
            db = Path(d) / "materials_db.json"
            db.write_text(json.dumps({"files": [{"path": "a.mp4", "material_map": str(mp)}]}),
                          encoding="utf-8")
            maps, err = pmm.material_maps_from_db(str(db))
            self.assertIsNone(err)
            self.assertEqual([m["asset_id"] for m in maps], ["abs"])

    def test_E_absent_material_map_key_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            db = _project(d, material_map=None)       # files entry has no material_map key
            maps, err = pmm.material_maps_from_db(db)
            self.assertIsNone(err)
            self.assertEqual(maps, [])                # existing-material-first

    def test_F_malformed_map_not_treated_as_covered(self):
        with tempfile.TemporaryDirectory() as d:
            db = _project(d, map_obj={"asset_id": "x", "source": "a.mp4", "scenes": [123]})
            maps, err = pmm.material_maps_from_db(db)
            self.assertIsNone(maps)                   # fail-closed, not [] / covered
            self.assertTrue(err)


class RunContractIntegrationTest(unittest.TestCase):
    def test_relative_missing_map_blocks_before_render(self):
        from video_pipeline_core import contract_adapter as ca2
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            # material_db declares a relative map that does NOT exist
            (d / "materials_db.json").write_text(
                json.dumps({"files": [{"path": "a.mp4", "material_map": "maps/missing.map.json"}]}),
                encoding="utf-8")
            contract = {"style": "mv", "music": {"brief": "x"}, "segments": [
                {"core": {"section_role": "montage", "story_purpose": "p", "timeline_source": "beat"},
                 "material_fit": {"visual_desc": "d", "reason": "r"},
                 "audio": {"role": "music", "reason": "r"},
                 "visual_style": {"layout": "montage", "pace": "fast", "reason": "r"},
                 "text_layer": "none"} for _ in range(2)]}
            (d / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
            (d / "bgm.mp3").write_bytes(b"x")
            called = {"mv": False}

            def fake_mv(*a, **k):
                called["mv"] = True
                return {"final": "x", "plan": []}

            with patch("video_pipeline_core.mv_cut.mv_chain", fake_mv), \
                 patch("video_pipeline_core.music_structure.write_music_structure",
                       lambda p, o, **k: (Path(o).write_text("{}", encoding="utf-8"),
                                          {"ok": True, "music_structure": str(o)})[1]):
                result = ca2.run_contract(d / "contract.json", material_db=d / "materials_db.json",
                                          out_path=d / "out" / "final.mp4", music_path=d / "bgm.mp3",
                                          mat_dir=d / "out", verbose=False)
            self.assertEqual(result["stage"], "material_map")    # fail-closed before render
            self.assertFalse(called["mv"])
            self.assertFalse((d / "out" / "final.mp4").exists())


if __name__ == "__main__":
    unittest.main()
