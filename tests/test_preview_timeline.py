import json
import tempfile
import unittest
from pathlib import Path

from tools.preview_timeline import (
    build_preview_timeline,
    classify_clip_type,
    compute_timeline_starts,
    main,
    parse_srt,
    path_to_url,
    seconds_to_frame,
)

BASE_URL = "http://localhost:8770"


def _write(root: Path, name: str, payload) -> None:
    if isinstance(payload, str):
        (root / name).write_text(payload, encoding="utf-8")
    else:
        (root / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class PreviewTimelinePureTest(unittest.TestCase):
    def test_classify_prefers_asset_type_then_extension(self):
        self.assertEqual(classify_clip_type("a.MOV", "image"), "image")
        self.assertEqual(classify_clip_type("a.MOV"), "video")
        self.assertEqual(classify_clip_type("a.PNG"), "image")
        self.assertEqual(classify_clip_type("a.unknown"), "video")

    def test_path_to_url_has_no_raw_windows_path(self):
        url = path_to_url(r"C:\Users\user\Downloads\clip.MOV", BASE_URL)
        self.assertTrue(url.startswith(BASE_URL))
        self.assertNotIn("\\", url)
        self.assertNotIn("C:\\", url)
        self.assertIn("/media?src=", url)

    def test_compute_timeline_starts_is_deterministic(self):
        self.assertEqual(compute_timeline_starts([2.0, 1.5, 3.0]), [0.0, 2.0, 3.5])

    def test_seconds_to_frame(self):
        self.assertEqual(seconds_to_frame(1.0, 30), 30)
        self.assertEqual(seconds_to_frame(0.5, 24), 12)

    def test_parse_srt_to_overlays(self):
        srt = "1\n00:00:00,000 --> 00:00:03,000\nHello\n\n2\n00:00:03,000 --> 00:00:05,500\nWorld\n"
        subs = parse_srt(srt)
        self.assertEqual(len(subs), 2)
        self.assertEqual(subs[0]["text"], "Hello")
        self.assertEqual(subs[0]["start_sec"], 0.0)
        self.assertEqual(subs[0]["duration_sec"], 3.0)
        self.assertEqual(subs[1]["start_sec"], 3.0)
        self.assertEqual(subs[1]["duration_sec"], 2.5)


class PreviewTimelineBuildTest(unittest.TestCase):
    def _make_root(self, tmp: str) -> Path:
        root = Path(tmp)
        vid = root / "clip.mp4"
        img = root / "still.png"
        vid.write_bytes(b"\x00")
        img.write_bytes(b"\x00")
        _write(root, "timeline.json", {
            "plan": [
                {"slot_index": 0, "segment": 1, "source": str(vid),
                 "slot_dur": 3.5, "extract_start": 1.2, "extract_dur": 3.5,
                 "scene_id": "s0", "need_id": "nd_0", "caption": "intro"},
                {"slot_index": 1, "segment": 1, "source": str(img),
                 "slot_dur": 2.0, "scene_id": "s1", "need_id": "nd_1", "caption": "still"},
            ],
        })
        _write(root, "project_material_map.json", {
            "artifact_role": "project_material_map", "version": 1,
            "assets": [
                {"asset_id": "a0", "asset_type": "video", "source": str(vid), "duration_sec": 70.0},
                {"asset_id": "a1", "asset_type": "image", "source": str(img), "duration_sec": 0.0},
            ],
            "needs": [],
        })
        _write(root, "review_subtitles.srt",
               "1\n00:00:00,000 --> 00:00:03,500\nSeg 1\n\n2\n00:00:03,500 --> 00:00:05,500\nSeg 2\n")
        return root

    def test_build_translates_video_and_image_clips(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._make_root(tmp)
            preview = build_preview_timeline(str(root), BASE_URL)

        self.assertEqual(preview["artifact_role"], "preview_timeline")
        self.assertEqual(preview["fps"], 30)
        self.assertEqual(len(preview["clips"]), 2)

        v, i = preview["clips"][0], preview["clips"][1]
        self.assertEqual(v["type"], "video")
        self.assertEqual(i["type"], "image")
        # source window preserved on the video clip
        self.assertEqual(v["source_start_sec"], 1.2)
        self.assertEqual(v["source_duration_sec"], 3.5)
        # image clip has source_start 0
        self.assertEqual(i["source_start_sec"], 0.0)
        # deterministic timeline starts
        self.assertEqual(v["timeline_start_sec"], 0.0)
        self.assertEqual(i["timeline_start_sec"], 3.5)
        self.assertEqual(preview["duration_sec"], 5.5)

    def test_subtitles_become_overlays(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._make_root(tmp)
            preview = build_preview_timeline(str(root), BASE_URL)
        self.assertEqual(len(preview["subtitles"]), 2)
        self.assertEqual(preview["subtitles"][0]["text"], "Seg 1")

    def test_src_url_is_browser_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._make_root(tmp)
            preview = build_preview_timeline(str(root), BASE_URL)
        for clip in preview["clips"]:
            self.assertTrue(clip["src_url"].startswith(BASE_URL))
            self.assertNotIn("\\", clip["src_url"])

    def test_missing_source_goes_to_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "timeline.json", {
                "plan": [
                    {"slot_index": 0, "source": str(root / "ghost.mp4"),
                     "slot_dur": 2.0, "extract_start": 0.0, "extract_dur": 2.0},
                    {"slot_index": 1, "source": None, "slot_dur": 1.0},
                ],
            })
            preview = build_preview_timeline(str(root), BASE_URL)

        statuses = {c["slot_index"]: c["status"] for c in preview["clips"]}
        self.assertEqual(statuses[0], "render_failed")  # source path missing on disk
        self.assertEqual(statuses[1], "gap")            # no source path at all
        codes = {d["code"] for d in preview["diagnostics"]}
        self.assertIn("source_not_found", codes)
        self.assertIn("missing_source", codes)

    def test_build_cli_refuses_canonical_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._make_root(tmp)
            before = (root / "timeline.json").read_text(encoding="utf-8")
            rc = main(["build", "--artifact-root", str(root), "--out", "timeline.json"])
            self.assertEqual(rc, 2)
            self.assertEqual((root / "timeline.json").read_text(encoding="utf-8"), before)

    def test_build_never_writes_timeline_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._make_root(tmp)
            before = (root / "timeline.json").read_text(encoding="utf-8")
            build_preview_timeline(str(root), BASE_URL)
            after = (root / "timeline.json").read_text(encoding="utf-8")
            self.assertEqual(before, after)
            # build is pure: it must not create preview_timeline.json by itself
            self.assertFalse((root / "preview_timeline.json").exists())

    def test_effect_patch_becomes_preview_effect_intent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._make_root(tmp)
            _write(root, "effect_patch.json", {
                "artifact_role": "effect_patch",
                "version": 1,
                "patches": [{
                    "op": "add_effect",
                    "effect_id": "fx-demo",
                    "after": {
                        "preset": "flash",
                        "target_slot_index": 0,
                        "start_sec": 0.2,
                        "duration_sec": 0.5,
                        "intensity": 4,
                    },
                }],
            })
            preview = build_preview_timeline(str(root), BASE_URL)
        effect = next(e for e in preview["effects"] if e.get("effect_id") == "fx-demo")
        self.assertEqual(effect["preset"], "flash")
        self.assertEqual(effect["target_slot_index"], 0)
        self.assertEqual(effect["start_sec"], 0.2)

    def test_project_effect_assets_are_projected_for_workbench(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._make_root(tmp)
            fx = root / "light_sweep.webm"
            fx.write_bytes(b"\x00")
            project = json.loads((root / "project_material_map.json").read_text(encoding="utf-8"))
            project["assets"].append({
                "asset_id": "fx-light",
                "asset_type": "effect_overlay",
                "source": str(fx),
                "duration_sec": 1.2,
                "scenes": [{"start": 0, "end": 1.2, "visual_family": "light_sweep"}],
            })
            _write(root, "project_material_map.json", project)
            preview = build_preview_timeline(str(root), BASE_URL)
        self.assertEqual(preview["effect_assets"][0]["asset_id"], "fx-light")
        self.assertEqual(preview["effect_assets"][0]["asset_type"], "effect_overlay")
        self.assertTrue(preview["effect_assets"][0]["src_url"].startswith(BASE_URL))

    def test_project_material_assets_are_projected_for_browser(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._make_root(tmp)
            project = json.loads((root / "project_material_map.json").read_text(encoding="utf-8"))
            project["assets"][0]["scenes"] = [{
                "index": 0,
                "start": 0.0,
                "end": 3.5,
                "visual_family": "training_wide",
                "angle_scale": "wide",
                "caption": "training field",
            }]
            project["assets"].append({
                "asset_id": "sfx-hit",
                "asset_type": "sfx",
                "source": str(root / "hit.wav"),
                "duration_sec": 0.2,
                "scenes": [],
            })
            _write(root, "project_material_map.json", project)
            preview = build_preview_timeline(str(root), BASE_URL)

        assets = preview["material_assets"]
        self.assertEqual([a["asset_id"] for a in assets], ["a0", "a1"])
        self.assertEqual(assets[0]["asset_type"], "video")
        self.assertEqual(assets[0]["scene_count"], 1)
        self.assertEqual(assets[0]["visual_family"], "training_wide")
        self.assertEqual(assets[0]["angle_scale"], "wide")
        self.assertTrue(assets[0]["src_url"].startswith(BASE_URL))


if __name__ == "__main__":
    unittest.main()
