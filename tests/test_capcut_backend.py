"""capcut_backend — P3 optional Node 13 render-candidate backend."""
import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import capcut_backend as cc


def _timeline():
    return {"clips": [
        {"segment": 1, "source_path": "a.mp4", "start_sec": 0, "end_sec": 3,
         "duration_sec": 3, "timeline_in_sec": 0, "timeline_out_sec": 3,
         "text_overlay": "開場", "audio_policy": "music"},
        {"segment": 2, "source_path": "b.mp4", "start_sec": 5, "end_sec": 7,
         "duration_sec": 2, "timeline_in_sec": 3, "timeline_out_sec": 5,
         "text_overlay": "none", "audio_policy": "duck"},
    ], "audio_tracks": [
        {"role": "bgm", "source_path": "bgm.mp3", "source_in_sec": 0,
         "timeline_in_sec": 0, "duration_sec": 5, "volume": 0.35},
    ]}


class DraftManifestTest(unittest.TestCase):
    def test_build_draft_manifest_shape(self):
        m = cc.build_draft_manifest(_timeline(), project_name="coffee")
        self.assertEqual(m["artifact_role"], "capcut_draft_manifest")
        self.assertEqual(m["version"], 1)
        self.assertEqual(m["backend"], "capcut_draft")
        # CapCut GUI export is a human/Computer-Use gate
        self.assertTrue(m["requires_human_or_computer_use"])
        # real proprietary .draft serialization is a version-gated boundary
        self.assertEqual(m["draft_serialization"]["status"], "pending")
        self.assertIn("capcut", m["draft_serialization"]["reason"].lower())
        self.assertEqual(m["project"]["name"], "coffee")

    def test_items_map_from_timeline(self):
        m = cc.build_draft_manifest(_timeline())
        items = m["video_track"]
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["source_path"], "a.mp4")
        self.assertEqual(items[0]["source_in_sec"], 0)
        self.assertEqual(items[0]["source_out_sec"], 3)
        self.assertEqual(items[0]["timeline_in_sec"], 0)
        # text overlays preserved, "none" dropped
        texts = [t["text"] for t in m["text_overlays"]]
        self.assertIn("開場", texts)
        self.assertNotIn("none", texts)
        self.assertEqual(m["audio_track"][0]["source_path"], "bgm.mp3")
        self.assertEqual(m["audio_track"][0]["role"], "bgm")

    def test_writer_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "capcut_draft_manifest.json"
            res = cc.write_draft_manifest(_timeline(), p, project_name="x")
            saved = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(res["capcut_draft_manifest"], str(p))
            self.assertEqual(saved["artifact_role"], "capcut_draft_manifest")


class ExportManifestTest(unittest.TestCase):
    def test_export_is_render_candidate_not_accepted(self):
        draft = cc.build_draft_manifest(_timeline(), project_name="coffee")
        ex = cc.record_export(draft, "exported.mp4", export_method="human")
        self.assertEqual(ex["artifact_role"], "capcut_export_manifest")
        self.assertTrue(ex["render_candidate"])
        self.assertFalse(ex["accepted"])           # never auto-accepted
        self.assertTrue(ex["requires_node12_verify"])
        self.assertEqual(ex["export_method"], "human")
        self.assertEqual(ex["exported_video"], "exported.mp4")

    def test_export_method_validation(self):
        draft = cc.build_draft_manifest(_timeline())
        with self.assertRaises(ValueError):
            cc.record_export(draft, "x.mp4", export_method="auto_magic")

    def test_write_export_manifest_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            draft = cc.build_draft_manifest(_timeline())
            p = Path(d) / "capcut_export_manifest.json"
            res = cc.write_export_manifest(draft, "out.mp4", p, export_method="computer_use")
            saved = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(res["capcut_export_manifest"], str(p))
            self.assertFalse(saved["accepted"])
            self.assertEqual(saved["export_method"], "computer_use")


def _skeleton():
    """Minimal but structurally real CapCut draft skeleton (1 video segment)."""
    return {
        "id": "OLD-DRAFT-ID",
        "duration": 1_000_000,
        "fps": 30.0,
        "name": "skeleton",
        "canvas_config": {"ratio": "original", "width": 1920, "height": 1080, "background": None},
        "materials": {
            "videos": [{"id": "V1", "path": "old.mp4", "duration": 1_000_000,
                        "type": "video", "width": 1920, "height": 1080,
                        "material_name": "old"}],
            "speeds": [{"id": "SP1", "type": "speed", "speed": 1.0}],
            "canvases": [{"id": "CV1", "type": "canvas_color"}],
            "sound_channel_mappings": [{"id": "SC1"}],
            "vocal_separations": [{"id": "VS1"}],
        },
        "tracks": [
            {"type": "video", "segments": [{
                "id": "SEG1", "material_id": "V1",
                "extra_material_refs": ["SP1", "CV1", "SC1", "VS1"],
                "source_timerange": {"start": 0, "duration": 1_000_000},
                "target_timerange": {"start": 0, "duration": 1_000_000},
                "render_index": 0,
            }]},
            {"type": "sticker", "segments": [{"id": "ST1"}]},
        ],
    }


class CapcutDraftWriterTest(unittest.TestCase):
    def test_build_draft_injects_clips_with_microsecond_timeranges(self):
        draft = cc.build_capcut_draft(_skeleton(), _timeline(), project_name="coffee")
        vids = draft["materials"]["videos"]
        self.assertEqual(len(vids), 2)
        # paths + durations (us) set from clips
        self.assertEqual(vids[0]["path"], "a.mp4")
        self.assertEqual(vids[0]["duration"], 3_000_000)
        self.assertEqual(vids[1]["duration"], 2_000_000)
        # unique material ids
        self.assertNotEqual(vids[0]["id"], vids[1]["id"])

        segs = draft["tracks"][0]["segments"]
        self.assertEqual(len(segs), 2)
        # sequential timeline placement
        self.assertEqual(segs[0]["target_timerange"], {"start": 0, "duration": 3_000_000})
        self.assertEqual(segs[1]["target_timerange"], {"start": 3_000_000, "duration": 2_000_000})
        # source in-point honored (clip 2 starts at 5s)
        self.assertEqual(segs[1]["source_timerange"]["start"], 5_000_000)
        # segment links to its own material
        self.assertEqual(segs[0]["material_id"], vids[0]["id"])
        # top-level duration = sum
        self.assertEqual(draft["duration"], 5_000_000)
        self.assertEqual(draft["name"], "coffee")

    def test_extra_material_refs_are_cloned_unique(self):
        draft = cc.build_capcut_draft(_skeleton(), _timeline())
        segs = draft["tracks"][0]["segments"]
        refs0 = set(segs[0]["extra_material_refs"])
        refs1 = set(segs[1]["extra_material_refs"])
        # each segment got its own cloned siblings (no sharing, no template ids)
        self.assertEqual(len(refs0), 4)
        self.assertTrue(refs0.isdisjoint(refs1))
        self.assertNotIn("SP1", refs0)
        # cloned siblings actually exist in the materials buckets
        all_ids = {m["id"] for b in draft["materials"].values()
                   if isinstance(b, list) for m in b}
        self.assertTrue(refs0 <= all_ids)

    def test_sticker_track_preserved(self):
        draft = cc.build_capcut_draft(_skeleton(), _timeline())
        types = [t["type"] for t in draft["tracks"]]
        self.assertIn("sticker", types)

    def test_build_draft_injects_editable_text_track(self):
        draft = cc.build_capcut_draft(_skeleton(), _timeline())
        text_track = next(t for t in draft["tracks"] if t["type"] == "text")
        self.assertEqual(len(text_track["segments"]), 1)
        self.assertEqual(
            text_track["segments"][0]["target_timerange"],
            {"start": 0, "duration": 3_000_000},
        )
        material_id = text_track["segments"][0]["material_id"]
        material = next(m for m in draft["materials"]["texts"] if m["id"] == material_id)
        self.assertEqual(json.loads(material["content"])["text"], "開場")

    def test_build_draft_injects_audio_track_from_explicit_sources(self):
        draft = cc.build_capcut_draft(_skeleton(), _timeline())
        audio_track = next(t for t in draft["tracks"] if t["type"] == "audio")
        self.assertEqual(len(audio_track["segments"]), 1)
        seg = audio_track["segments"][0]
        self.assertEqual(seg["target_timerange"], {"start": 0, "duration": 5_000_000})
        self.assertEqual(seg["volume"], 0.35)
        material = next(m for m in draft["materials"]["audios"] if m["id"] == seg["material_id"])
        self.assertEqual(material["path"], "bgm.mp3")
        self.assertEqual(material["type"], "audio")

    def test_write_draft_project_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            skel = Path(d) / "skeleton.json"
            skel.write_text(json.dumps(_skeleton()), encoding="utf-8")
            proj = Path(d) / "test_p3"
            res = cc.write_capcut_draft(skel, _timeline(), proj, project_name="test_p3")
            self.assertEqual(res["clip_count"], 2)
            content = json.loads((proj / "draft_content.json").read_text(encoding="utf-8"))
            info = json.loads((proj / "draft_info.json").read_text(encoding="utf-8"))
            self.assertEqual(content["duration"], 5_000_000)
            self.assertEqual(content, info)  # synced copies match

    def test_skeleton_without_video_track_raises(self):
        bad = {"materials": {"videos": []}, "tracks": []}
        with self.assertRaises(ValueError):
            cc.build_capcut_draft(bad, _timeline())


class CapcutCliTest(unittest.TestCase):
    def test_capcut_draft_cmd(self):
        import video_tools
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            timeline = Path(d) / "timeline_build.json"
            timeline.write_text(json.dumps(_timeline()), encoding="utf-8")
            out = str(Path(d) / "capcut_draft_manifest.json")
            video_tools.cmd_capcut_draft(
                SimpleNamespace(timeline=str(timeline), out=out, project="coffee"))
            saved = json.loads(Path(out).read_text(encoding="utf-8"))
            self.assertEqual(saved["artifact_role"], "capcut_draft_manifest")
            self.assertTrue(saved["requires_human_or_computer_use"])


class CapcutHelpersTest(unittest.TestCase):
    def test_mute_all_video_segments(self):
        draft = _skeleton()
        # Ensure it has a video track and segment
        segs = draft["tracks"][0]["segments"]
        self.assertEqual(len(segs), 1)
        # Apply mute
        cc.mute_all_video_segments(draft)
        
        # Verify segment volume and last_nonzero_volume
        self.assertEqual(segs[0]["volume"], 0.0)
        self.assertEqual(segs[0]["last_nonzero_volume"], 0.0)
        
        # Verify material has_audio and has_sound_separated
        mat = draft["materials"]["videos"][0]
        self.assertFalse(mat.get("has_audio", True))
        self.assertTrue(mat.get("has_sound_separated", False))

    def test_apply_text_preset(self):
        draft = _skeleton()
        # Add a text track and text material
        draft["tracks"].append({
            "type": "text",
            "segments": [{
                "id": "TSEG1",
                "material_id": "TMAT1",
                "extra_material_refs": []
            }]
        })
        draft["materials"]["texts"] = [{
            "id": "TMAT1",
            "font_path": "",
            "text_color": "",
            "content": json.dumps({
                "text": "Hello 中文",
                "styles": []
            })
        }]
        
        # Apply preset
        cc.apply_text_preset(draft, 0, preset_name="white_outline_black")
        
        # Check text material fields
        mat = draft["materials"]["texts"][0]
        self.assertEqual(mat["text_color"], "#ffffff")
        self.assertEqual(mat["border_color"], "#000000")
        
        # Check content styles
        co = json.loads(mat["content"])
        self.assertEqual(co["styles"][0]["size"], 15)
        self.assertEqual(co["styles"][0]["fill"]["content"]["solid"]["color"], [1, 1, 1])

    def test_parse_silencedetect(self):
        # 1) 末段 silence 跑到 EOF
        stderr = "[silencedetect @ 0x55] silence_start: 165.381\n"
        res = cc._parse_silencedetect(stderr, 171.711)
        self.assertEqual(res, 165.381)

        # 2) 末段 silence 有 end 但緊貼 total
        stderr = "silence_start: 100.0\nsilence_end: 171.5 | silence_duration: 71.5\n"
        res = cc._parse_silencedetect(stderr, 171.711)
        self.assertEqual(res, 100.0)

        # 3) 中段 silence 後人聲又恢復
        stderr = "silence_start: 50.0\nsilence_end: 52.0 | silence_duration: 2.0\n"
        res = cc._parse_silencedetect(stderr, 171.711)
        self.assertEqual(res, 171.711)


if __name__ == "__main__":
    unittest.main()
