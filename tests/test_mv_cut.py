"""MV-cut increment ①: beat → cut_grid (timeline:beat driver).

Pure-function tests — no audio, no librosa. The beats are synthetic timestamps
so the cut-grid logic is fully deterministic.
"""
import tempfile
import unittest
from unittest.mock import patch

from video_pipeline_core import mv_cut


class BeatsToCutGridTest(unittest.TestCase):
    def _beats(self, n, step=0.5):
        return [round(i * step, 3) for i in range(n)]  # 120 BPM = 0.5s/beat

    def test_120bpm_cut_every_4_beats(self):
        # 9 beats: 0.0 .. 4.0 ; every 4 beats -> cut at 0, 2.0, 4.0
        grid = mv_cut.beats_to_cut_grid(self._beats(9), every_n_beats=4, min_seg=1.0)
        self.assertEqual(grid, [(0.0, 2.0), (2.0, 4.0)])

    def test_total_extends_final_segment(self):
        grid = mv_cut.beats_to_cut_grid(self._beats(9), every_n_beats=4,
                                        min_seg=1.0, total=5.0)
        self.assertEqual(grid[-1], (4.0, 5.0))   # last beat 4.0 → extended to song end 5.0
        self.assertEqual(len(grid), 3)

    def test_short_tail_segment_merges_into_previous(self):
        # total 4.3 → tail (4.0,4.3)=0.3s < min_seg → merged into (2.0,4.0)
        grid = mv_cut.beats_to_cut_grid(self._beats(9), every_n_beats=4,
                                        min_seg=1.0, total=4.3)
        self.assertEqual(grid, [(0.0, 2.0), (2.0, 4.3)])

    def test_too_few_beats_returns_single_span(self):
        self.assertEqual(mv_cut.beats_to_cut_grid([1.0], total=10.0), [(1.0, 10.0)])
        self.assertEqual(mv_cut.beats_to_cut_grid([], total=10.0), [(0.0, 10.0)])

    def test_every_n_1_cuts_each_beat(self):
        grid = mv_cut.beats_to_cut_grid(self._beats(5), every_n_beats=1, min_seg=0.1)
        self.assertEqual(len(grid), 4)  # 5 beats → 4 spans

    def test_unsorted_input_is_sorted(self):
        grid = mv_cut.beats_to_cut_grid([2.0, 0.0, 1.0, 3.0, 4.0],
                                        every_n_beats=2, min_seg=0.1)
        self.assertEqual(grid[0][0], 0.0)
        self.assertTrue(all(grid[i][1] == grid[i + 1][0] for i in range(len(grid) - 1)))


class SelectWindowsTest(unittest.TestCase):
    def _c(self, score, group, tag=None):
        return {"score": score, "group": group, "tag": tag}

    def test_top_k_by_score(self):
        cands = [self._c(90, "a"), self._c(70, "b"), self._c(50, "c")]
        sel, unfilled = mv_cut.select_windows(cands, n_slots=2)
        self.assertEqual([c["score"] for c in sel], [90, 70])
        self.assertEqual(unfilled, [])

    def test_must_include_overrides_score_floor(self):
        # 所長 clip is boring (score 10) but MUST be included
        cands = [self._c(95, "活動"), self._c(90, "活動"), self._c(10, "所長")]
        sel, unfilled = mv_cut.select_windows(cands, n_slots=2,
                                              must_include=["所長"], min_score=60)
        groups = {c["group"] for c in sel}
        self.assertIn("所長", groups)          # 必放進來了,即使 score 10 < 60
        self.assertEqual(len(sel), 2)
        self.assertEqual(unfilled, [])

    def test_must_include_matches_parent_folder_via_path(self):
        # 必放是父層「必放項目」,但 group 只取葉層「所長看填志願」
        cands = [{"score": 95, "group": "活動", "source": "/m/活動/v.mov"},
                 {"score": 10, "group": "所長看填志願",
                  "source": "/m/必放項目/所長看填志願/IMG.mov"}]
        sel, unfilled = mv_cut.select_windows(cands, n_slots=2,
                                              must_include=["必放項目"], min_score=60)
        self.assertEqual(unfilled, [])                       # 父層路徑匹配到了
        self.assertTrue(any(c["group"] == "所長看填志願" for c in sel))

    def test_unfilled_must_reported(self):
        cands = [self._c(95, "活動")]
        sel, unfilled = mv_cut.select_windows(cands, n_slots=3,
                                              must_include=["所長"])
        self.assertEqual(unfilled, ["所長"])   # 沒有所長素材 → 缺口給 VERIFY
        self.assertEqual([c["group"] for c in sel], ["活動"])

    def test_min_score_filters_fill(self):
        cands = [self._c(95, "a"), self._c(40, "b")]
        sel, _ = mv_cut.select_windows(cands, n_slots=5, min_score=60)
        self.assertEqual(len(sel), 1)          # score-40 dropped

    def test_n_slots_cap(self):
        cands = [self._c(s, f"g{s}") for s in (90, 80, 70, 60)]
        sel, _ = mv_cut.select_windows(cands, n_slots=2)
        self.assertEqual(len(sel), 2)


class ScoreWindowsTest(unittest.TestCase):
    """increment ③ I/O loop — frame extract + VLM scoring injected as fakes."""

    def test_assembles_candidates_with_scores(self):
        windows = [(0.0, 4.0), (4.0, 8.0)]
        scores = iter([(90.0, "a man pulling cable", "primary=yes"),
                       (40.0, "blurry wall", "related=somewhat")])
        cands = mv_cut.score_windows(
            "/x/拖拉電纜/IMG_1.mov", windows, "學員協力拖拉電纜",
            _extract=lambda v, t, o: True, _score=lambda f, d: next(scores))
        self.assertEqual([c["score"] for c in cands], [90.0, 40.0])
        self.assertEqual(cands[0]["group"], "拖拉電纜")     # derived from folder
        self.assertEqual(cands[0]["source"], "/x/拖拉電纜/IMG_1.mov")  # full path for ④ render
        self.assertEqual(cands[0]["source_name"], "IMG_1.mov")
        self.assertEqual(cands[0]["win"], (0.0, 4.0))

    def test_frame_fail_scores_zero(self):
        cands = mv_cut.score_windows(
            "/x/g/v.mov", [(0.0, 4.0)], "desc",
            _extract=lambda v, t, o: False, _score=lambda f, d: (99.0, "x", "y"))
        self.assertEqual(cands[0]["score"], 0.0)
        self.assertEqual(cands[0]["reason"], "frame_fail")

    def test_feeds_select_windows_endtoend(self):
        # window scoring → must-include selection, all in-memory
        windows = [(0, 4), (4, 8), (8, 12)]
        scores = iter([(95.0, "", ""), (88.0, "", ""), (10.0, "", "")])
        cands = mv_cut.score_windows(
            "/x/所長看填志願/v.mov", windows, "所長致詞",
            group="所長",
            _extract=lambda v, t, o: True, _score=lambda f, d: next(scores))
        sel, unfilled = mv_cut.select_windows(cands, n_slots=2,
                                              must_include=["所長"], min_score=60)
        self.assertEqual(unfilled, [])
        self.assertTrue(any(c["group"] == "所長" for c in sel))


class DrawtextChainTest(unittest.TestCase):
    def test_empty_when_no_text(self):
        self.assertEqual(mv_cut._drawtext_chain(None, "/tmp", 0), "")
        self.assertEqual(mv_cut._drawtext_chain({}, "/tmp", 0), "")

    def test_label_and_name_super_build_drawtext(self):
        if not mv_cut._CJK_FONT:
            self.skipTest("no CJK font")
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            out = mv_cut._drawtext_chain(
                {"label": "礙子拆線作業", "name_super": {"text": "鍾峻松", "title": "老師"}}, d, 3)
            self.assertTrue(out.startswith(","))
            self.assertEqual(out.count("drawtext="), 2)
            self.assertTrue(os.path.exists(os.path.join(d, "lbl_3.txt")))
            with open(os.path.join(d, "lbl_3.txt"), encoding="utf-8") as f:
                self.assertEqual(f.read(), "礙子拆線作業")

    def test_narrative_card_darkens_and_centers(self):
        if not mv_cut._CJK_FONT:
            self.skipTest("no CJK font")
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            out = mv_cut._drawtext_chain({"narrative": "傳承精技\n篤學不倦"}, d, 1)
            self.assertIn("drawbox", out)                      # 暗化背景
            self.assertIn("fontsize=72", out)                  # 大字
            self.assertIn("(w-text_w)/2", out)                 # 置中
            with open(os.path.join(d, "nar_1.txt"), encoding="utf-8") as f:
                self.assertEqual(f.read(), "傳承精技\n篤學不倦")


class BuildMvStateTest(unittest.TestCase):
    def _run(self, tmp, per_seg, segs):
        import os
        out = os.path.join(tmp, "final.mp4")
        script = {"style": "mv", "music": {"brief": "熱血"}, "segments": segs}
        return mv_cut.build_mv_state(script, per_seg, out)

    def test_done_and_gap_status(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            per_seg = [{"segment": 1, "visual_desc": "拖拉電纜", "source": "local",
                        "picked_scores": [100, 100]},
                       {"segment": 2, "visual_desc": "大合照", "source": "local",
                        "picked_scores": ["GAP"]}]
            segs = [{"segment": 1, "layout": "montage", "label": "電纜作業"},
                    {"segment": 2, "kind": "closing"}]
            st = self._run(tmp, per_seg, segs)
            self.assertEqual(st["segments"][0]["status"], "done")
            self.assertEqual(st["segments"][0]["label"], "電纜作業")
            self.assertEqual(st["segments"][1]["status"], "blocked")
            self.assertEqual(len(st["blocking"]), 1)
            self.assertEqual(st["next_action"], "await_material")
            self.assertEqual(st["mode"], "mv")
            import os
            self.assertTrue(os.path.exists(os.path.join(tmp, "state.json")))

    def test_clean_pass(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            st = self._run(tmp, [{"segment": 1, "visual_desc": "x", "source": "local",
                                  "picked_scores": [100]}], [{"segment": 1}])
            self.assertTrue(st["pass"])
            self.assertIsNone(st["next_action"])

    def test_pending_visual_review_is_not_reported_as_material_gap(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            st = self._run(
                tmp,
                [{
                    "segment": 1,
                    "visual_desc": "team discussion",
                    "source": "stock",
                    "pending_visual_review": True,
                    "picked_scores": ["PENDING_VISUAL_REVIEW"],
                }],
                [{"segment": 1, "source": "stock"}],
            )

        self.assertEqual(st["next_action"], "await_visual_review")
        self.assertEqual(st["blocking"], [])
        self.assertEqual(st["segments"][0]["status"], "pending_review")

    def test_must_include_unfilled_and_review_points(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "f.mp4")
            script = {"style": "mv", "segments": [
                {"segment": 1, "kind": "opening"},                        # bookend → review
                {"segment": 2, "must_include": "所長"},                    # GAP + 必放
                {"segment": 3, "needs_review": True}]}
            per_seg = [{"segment": 1, "visual_desc": "片頭", "picked_scores": [100]},
                       {"segment": 2, "visual_desc": "致詞", "picked_scores": ["GAP"]},
                       {"segment": 3, "visual_desc": "x", "picked_scores": [100]}]
            st = mv_cut.build_mv_state(script, per_seg, out)
            # 必放未滿的 blocking reason 要點名 must_include
            blk2 = next(b for b in st["blocking"] if b["segment"] == 2)
            self.assertIn("必放", blk2["reason"])
            self.assertIn("所長", blk2["reason"])
            # review_points 含 opening(高權重)與 needs_review 段
            rp = {r["segment"] for r in st["review_points"]}
            self.assertIn(1, rp)
            self.assertIn(3, rp)

    def test_timeline_and_build_layer_from_plan(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "final.mp4")
            script = {"style": "mv", "segments": [
                {"segment": 1, "layout": "montage", "must_include": "所長"},
                {"segment": 2, "kind": "closing"}]}
            per_seg = [{"segment": 1, "visual_desc": "拖拉電纜", "source": "local",
                        "picked_scores": [100, 90]},
                       {"segment": 2, "visual_desc": "大合照", "source": "local",
                        "picked_scores": ["GAP"]}]
            # seg1 兩 slot(各 1.5s)來自同一支 a.mov;seg2 無 slot(GAP)
            plan = [{"segment": 1, "source": "/m/拖拉電纜/a.mov", "extract_dur": 1.5},
                    {"segment": 1, "source": "/m/拖拉電纜/a.mov", "extract_dur": 1.5}]
            st = mv_cut.build_mv_state(script, per_seg, out, plan=plan)
            s1 = st["segments"][0]
            self.assertEqual(s1["start"], 0.0)
            self.assertEqual(s1["dur"], 3.0)
            self.assertEqual(s1["n_slots"], 2)
            self.assertEqual(s1["picked_clips"], ["a.mov"])   # 去重
            self.assertEqual(s1["must_include"], "所長")
            # GAP 段沒時長
            self.assertIsNone(st["segments"][1]["dur"])
            self.assertEqual(st["total_dur"], 3.0)


class PhotoHandlingTest(unittest.TestCase):
    def test_is_image(self):
        self.assertTrue(mv_cut._is_image("/x/大合照/a.JPG"))
        self.assertTrue(mv_cut._is_image("b.png"))
        self.assertFalse(mv_cut._is_image("c.mov"))
        self.assertFalse(mv_cut._is_image("d.mp4"))
        self.assertFalse(mv_cut._is_image(""))

    def test_photo_vf_hold_vs_kenburns(self):
        self.assertEqual(mv_cut._photo_vf(3.0, kenburns=False), mv_cut._MV_VF)
        kb = mv_cut._photo_vf(2.0, kenburns=True)
        self.assertIn("zoompan", kb)
        self.assertIn("d=60", kb)          # 2.0s * 30fps
        self.assertIn("s=1920x1080", kb)

    def test_find_photos_filters_by_hint_and_ext(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "大合照"))
            os.makedirs(os.path.join(d, "其他"))
            for rel in ["大合照/a.jpg", "大合照/b.png", "其他/c.jpg"]:
                open(os.path.join(d, rel), "w").close()
            open(os.path.join(d, "大合照/v.mov"), "w").close()  # 影片不算
            hits = mv_cut.find_photos(d, "大合照")
            self.assertEqual(len(hits), 2)
            self.assertTrue(all(h.endswith((".jpg", ".png")) for h in hits))


class AudioQaTest(unittest.TestCase):
    def test_subtitle_auto_without_keep_audio_flags(self):
        segs = [{"segment": 1, "subtitle": "auto"}]   # 講話卻沒保留原音
        r = mv_cut.audio_qa(segs)
        self.assertEqual(r["dimension"], "audio_pairing")
        self.assertEqual(len(r["issues"]), 1)
        self.assertEqual(r["score"], 75)

    def test_subtitle_auto_with_duck_is_clean(self):
        segs = [{"segment": 1, "subtitle": "auto", "audio_role": "duck"}]
        r = mv_cut.audio_qa(segs)
        self.assertEqual(r["issues"], [])
        self.assertEqual(r["score"], 100)

    def test_diegetic_keeps_audio_auto(self):
        # diegetic 隱含 keep_audio → 不應報錯
        r = mv_cut.audio_qa([{"segment": 1, "audio_role": "diegetic"}])
        self.assertEqual(r["issues"], [])

    def test_state_carries_audio_pairing(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "f.mp4")
            script = {"style": "mv", "segments": [
                {"segment": 1, "subtitle": "auto"},               # 會被 flag
                {"segment": 2, "audio_role": "music"}]}
            per_seg = [{"segment": 1, "visual_desc": "a", "picked_scores": [100]},
                       {"segment": 2, "visual_desc": "b", "picked_scores": [100]}]
            st = mv_cut.build_mv_state(script, per_seg, out)
            self.assertEqual(st["qa"]["audio_pairing"], 75)
            self.assertEqual(len(st["qa"]["audio_issues"]), 1)


class RunMvArtifactTest(unittest.TestCase):
    def test_run_mv_snaps_plan_to_motion_before_render(self):
        script = {"segments": [
            {"segment": 1, "visual_desc": "開場", "weight": 1.0,
             "pace": "hold", "audio_role": "music"},
            {"segment": 2, "visual_desc": "動作", "weight": 1.0,
             "pace": "hold", "audio_role": "music"},
        ]}
        clip_list = {"assignments": [
            {"segment": 1, "picks": [{"path": "/m/a.mp4"}]},
            {"segment": 2, "picks": [{"path": "/m/b.mp4"}]},
        ]}
        captured = {}

        def fake_render(plan, *_args, **_kwargs):
            captured["plan"] = plan

        with patch("video_pipeline_core.mv_cut.detect_beats", lambda _p: (120.0, [0.0, 2.0, 4.0])), \
             patch("video_pipeline_core.mv_cut._windows_from_clip", lambda path, *a, **k: [{
                 "source": path, "extract_start": 10.0, "extract_dur": 3.0,
                 "keep_audio": False, "segment": k.get("segment"),
             }]), \
             patch("video_pipeline_core.edit_artifacts.snap_render_plan_to_motion",
                   side_effect=lambda plan: [plan[0], {
                       **plan[1],
                       "original_extract_start": plan[1]["extract_start"],
                       "extract_start": 11.0,
                       "adjustment_reason": "snapped_to_motion_peak",
                   }]), \
             patch("video_pipeline_core.mv_cut.render_mv_audio", fake_render), \
             patch("video_pipeline_core.mv_cut.build_mv_state", lambda *a, **k: None):
            result = mv_cut.run_mv(
                script, "/materials", "/out/final.mp4",
                music_path="/music.mp3", clip_list=clip_list, verbose=False,
            )

        self.assertEqual(captured["plan"][0]["extract_start"], 10.0)
        self.assertEqual(captured["plan"][1]["extract_start"], 11.0)
        self.assertEqual(result["plan"][1]["adjustment_reason"], "snapped_to_motion_peak")

    def test_run_mv_returns_render_plan_for_timeline_artifact(self):
        script = {"segments": [
            {"segment": 1, "visual_desc": "開場", "weight": 1.0,
             "pace": "hold", "audio_role": "music",
             "attention_budget": {"owner": "music", "shot_sec": [1.5, 4.0]}}
        ]}
        clip_list = {"assignments": [{"segment": 1, "picks": [{"path": "/m/a.mp4"}]}]}

        def fake_windows(path, n_clips, clip_dur, keep_audio, text=None, segment=None):
            return [{"source": path, "extract_start": 1.0, "extract_dur": 2.0,
                     "keep_audio": keep_audio, "text": text, "segment": segment}]

        with patch("video_pipeline_core.mv_cut.detect_beats", lambda _p: (120.0, [0.0, 2.0])), \
             patch("video_pipeline_core.mv_cut._windows_from_clip", fake_windows), \
             patch("video_pipeline_core.mv_cut.render_mv_audio", lambda *a, **k: None), \
             patch("video_pipeline_core.mv_cut.build_mv_state", lambda *a, **k: None):
            result = mv_cut.run_mv(script, "/materials", "/out/final.mp4",
                                   music_path="/music.mp3", clip_list=clip_list,
                                   verbose=False)

        self.assertEqual(result["cuts"], 1)
        self.assertEqual(result["plan"][0]["source"], "/m/a.mp4")
        self.assertEqual(result["plan"][0]["segment"], 1)
        self.assertEqual(result["plan"][0]["attention_budget"]["owner"], "music")

    def test_run_mv_can_preserve_text_trace_without_burning_base_text(self):
        script = {"segments": [{
            "segment": 1,
            "visual_desc": "opening",
            "narrative": "Opening title",
            "weight": 1.0,
            "pace": "hold",
            "audio_role": "music",
        }]}
        clip_list = {"assignments": [{"segment": 1, "picks": [{"path": "/m/a.mp4"}]}]}
        captured = {}

        def fake_render(plan, music_path, out_path, **kwargs):
            captured["text"] = plan[0]["text"]["narrative"]
            captured["burn_text"] = kwargs["burn_text"]

        with patch("video_pipeline_core.mv_cut.detect_beats", lambda _p: (120.0, [0.0, 2.0])), \
             patch("video_pipeline_core.mv_cut._windows_from_clip", lambda path, n_clips, clip_dur, keep_audio, text=None, segment=None: [{
                 "source": path, "extract_start": 0.0, "extract_dur": 2.0,
                 "keep_audio": keep_audio, "text": text, "segment": segment,
             }]), \
             patch("video_pipeline_core.mv_cut.render_mv_audio", fake_render), \
             patch("video_pipeline_core.mv_cut.build_mv_state", lambda *a, **k: None):
            mv_cut.run_mv(
                script, "/materials", "/out/final.mp4",
                music_path="/music.mp3", clip_list=clip_list,
                verbose=False, burn_text=False,
            )

        self.assertEqual(captured["text"], "Opening title")
        self.assertFalse(captured["burn_text"])

    def test_run_mv_preserves_explicit_transition_on_first_segment_slot(self):
        script = {"segments": [{
            "segment": 1, "visual_desc": "opening", "weight": 1.0,
            "pace": "hold", "audio_role": "music",
        }, {
            "segment": 2, "visual_desc": "next", "weight": 1.0,
            "pace": "hold", "audio_role": "music",
            "visual_style": {"transition": "xfade", "transition_duration": 0.4},
        }]}
        clip_list = {"assignments": [
            {"segment": 1, "picks": [{"path": "/m/a.mp4"}]},
            {"segment": 2, "picks": [{"path": "/m/b.mp4"}]},
        ]}

        with patch("video_pipeline_core.mv_cut.detect_beats", lambda _p: (120.0, [0.0, 2.0, 4.0])), \
             patch("video_pipeline_core.mv_cut._windows_from_clip", lambda path, n_clips, clip_dur, keep_audio, text=None, segment=None: [{
                 "source": path, "extract_start": 0.0, "extract_dur": 2.0,
                 "keep_audio": keep_audio, "text": text, "segment": segment,
             }]), \
             patch("video_pipeline_core.mv_cut.render_mv_audio", lambda *a, **k: None), \
             patch("video_pipeline_core.mv_cut.build_mv_state", lambda *a, **k: None):
            result = mv_cut.run_mv(
                script, "/materials", "/out/final.mp4",
                music_path="/music.mp3", clip_list=clip_list, verbose=False,
            )

        self.assertNotIn("transition", result["plan"][0])
        self.assertEqual(result["plan"][1]["transition"], "xfade")
        self.assertEqual(result["plan"][1]["transition_duration"], 0.4)

    def test_run_mv_agent_mode_writes_one_visual_review_request_and_skips_render(self):
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            def fake_stock(s, a, seg_text, mat_dir, **kwargs):
                return [], {
                    "segment": s["segment"],
                    "visual_desc": s["visual_desc"],
                    "source": "stock",
                    "candidate": f"stock-{s['segment']}.mp4",
                    "montage": f"visual_review/seg{s['segment']}.jpg",
                    "pending_visual_review": True,
                    "picked_scores": ["PENDING_VISUAL_REVIEW"],
                }, []

            with patch("video_pipeline_core.mv_cut.detect_beats", return_value=(120.0, [0.0, 2.0, 4.0])), \
                 patch("video_pipeline_core.mv_cut._plan_stock_segment", side_effect=fake_stock), \
                 patch("video_pipeline_core.mv_cut.render_mv_audio") as render, \
                 patch("video_pipeline_core.mv_cut.build_mv_state"):
                result = mv_cut.run_mv(
                    {"segments": [
                        {"segment": 1, "source": "stock", "visual_desc": "one"},
                        {"segment": 2, "source": "stock", "visual_desc": "two"},
                    ]},
                    None,
                    str(Path(tmp) / "final.mp4"),
                    music_path="music.mp3",
                    mat_dir=tmp,
                    visual_judge="agent",
                    verbose=False,
                )

            request = json.loads((Path(tmp) / "visual_review_request.json").read_text(encoding="utf-8"))

        self.assertEqual([clip["segment"] for clip in request["clips"]], [1, 2])
        self.assertTrue(result["awaiting_visual_review"])
        render.assert_not_called()

    def test_run_mv_agent_mode_loads_verdict_by_segment(self):
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "visual_review_verdict.json").write_text(json.dumps({
                "clips": [{
                    "segment": 1,
                    "accept": True,
                    "picked_windows": [{"start": 1.0, "end": 2.0}],
                }]
            }), encoding="utf-8")
            received = {}

            def fake_stock(s, a, seg_text, mat_dir, **kwargs):
                received["verdict"] = kwargs.get("visual_verdict")
                return [], {"segment": 1, "picked_scores": ["GAP"]}, []

            with patch("video_pipeline_core.mv_cut.detect_beats", return_value=(120.0, [0.0, 2.0])), \
                 patch("video_pipeline_core.mv_cut._plan_stock_segment", side_effect=fake_stock), \
                 patch("video_pipeline_core.mv_cut.render_mv_audio"), \
                 patch("video_pipeline_core.mv_cut.build_mv_state"):
                mv_cut.run_mv(
                    {"segments": [{"segment": 1, "source": "stock", "visual_desc": "one"}]},
                    None,
                    str(Path(tmp) / "final.mp4"),
                    music_path="music.mp3",
                    mat_dir=tmp,
                    visual_judge="agent",
                    verbose=False,
                )

        self.assertTrue(received["verdict"]["accept"])


class XfadeRenderTest(unittest.TestCase):
    def test_build_transition_filter_uses_xfade_only_for_explicit_boundary(self):
        plan = [
            {"segment": 1, "extract_dur": 2.0},
            {"segment": 1, "extract_dur": 2.0},
            {"segment": 2, "extract_dur": 3.0, "transition": "xfade", "transition_duration": 0.5},
            {"segment": 3, "extract_dur": 2.0, "transition": "direct_cut"},
        ]

        graph, video_label, audio_label = mv_cut._build_transition_filter(plan)

        self.assertIn("xfade=transition=fade:duration=0.500:offset=3.500", graph)
        self.assertIn("acrossfade=d=0.500", graph)
        self.assertIn("concat=n=2:v=1:a=0", graph)
        self.assertTrue(video_label.startswith("[v"))
        self.assertTrue(audio_label.startswith("[a"))


class StaticPrefilterTest(unittest.TestCase):
    def test_parse_freeze_ratio_pair(self):
        err = ("[freezedetect @ x] lavfi.freezedetect.freeze_start: 0\n"
               "[freezedetect @ x] lavfi.freezedetect.freeze_end: 2.0\n")
        self.assertAlmostEqual(mv_cut._parse_freeze_ratio(err, 4.0), 0.5)

    def test_parse_freeze_start_without_end_runs_to_window_end(self):
        err = "lavfi.freezedetect.freeze_start: 1.0\n"
        self.assertAlmostEqual(mv_cut._parse_freeze_ratio(err, 4.0), 0.75)

    def test_parse_freeze_empty_is_dynamic(self):
        self.assertEqual(mv_cut._parse_freeze_ratio("", 4.0), 0.0)
        self.assertEqual(mv_cut._parse_freeze_ratio("no freeze here", 4.0), 0.0)

    def test_filter_drops_static_keeps_dynamic(self):
        wins = [(0.0, 4.0), (4.0, 8.0), (8.0, 12.0)]
        ratios = {(0.0, 4.0): 0.95, (4.0, 8.0): 0.1, (8.0, 12.0): 0.9}
        kept = mv_cut.filter_static_windows(wins, "x", max_static=0.85,
                                            _ratio=lambda s, e: ratios[(s, e)])
        self.assertEqual(kept, [(4.0, 8.0)])

    def test_filter_all_static_falls_back_to_all(self):
        wins = [(0.0, 4.0), (4.0, 8.0)]
        kept = mv_cut.filter_static_windows(wins, "x", max_static=0.85,
                                            _ratio=lambda s, e: 0.99)
        self.assertEqual(kept, wins)


class MusicMixTest(unittest.TestCase):
    def test_sidechain_duck_when_keep_audio(self):
        fc, amap = mv_cut._mv_music_mix(True, music_vol=0.6)
        self.assertIn("sidechaincompress", fc)
        self.assertIn("asplit=2", fc)
        self.assertIn("volume=0.6", fc)
        self.assertEqual(amap, "[a]")

    def test_pure_montage_maps_music_direct(self):
        fc, amap = mv_cut._mv_music_mix(False)
        self.assertIsNone(fc)
        self.assertEqual(amap, "1:a:0")


class SrtTsTest(unittest.TestCase):
    def test_srt_timestamp_format(self):
        self.assertEqual(mv_cut._srt_ts(0), "00:00:00,000")
        self.assertEqual(mv_cut._srt_ts(65.5), "00:01:05,500")
        self.assertEqual(mv_cut._srt_ts(3661.25), "01:01:01,250")


class MatchMontageMultiPickTest(unittest.TestCase):
    def test_montage_picks_multiple(self):
        import video_tools as vt
        files = [{"path": f"/m/拖拉電纜/{i}.mov", "vlm_caption": "拖拉電纜施工",
                  "classify": {"usable": True}} for i in range(6)]
        segs = [{"segment": 1, "visual_desc": "拖拉電纜", "material_hint": "拖拉電纜",
                 "layout": "montage"}]
        r = vt.match_script_to_material(segs, files, montage_picks=5)
        self.assertEqual(len(r["assignments"][0]["picks"]), 5)

    def test_non_montage_picks_one(self):
        import video_tools as vt
        files = [{"path": f"/m/x/{i}.mov", "vlm_caption": "致詞", "classify": {"usable": True}}
                 for i in range(3)]
        segs = [{"segment": 1, "visual_desc": "致詞", "material_hint": "x"}]
        r = vt.match_script_to_material(segs, files)
        self.assertEqual(len(r["assignments"][0]["picks"]), 1)


class SegmentPlannerTest(unittest.TestCase):
    def test_video_vf_uses_patch_crop_center(self):
        vf = mv_cut._video_vf({"x": 0.7, "y": 0.4})

        self.assertIn("force_original_aspect_ratio=increase", vf)
        self.assertIn("(iw-ow)*0.700", vf)
        self.assertIn("(ih-oh)*0.400", vf)

    """run_mv 解耦出的 per-段 planner(matched/stock/live)— 以注入避開 ffmpeg/VLM。"""

    def test_windows_from_clip_image_expands_to_distinct_still_shots(self):
        slots = mv_cut._windows_from_clip("/m/group/a.jpg", 3, 2.0, False, segment=7)
        self.assertEqual(len(slots), 3)
        self.assertTrue(all(slot["is_photo"] for slot in slots))
        self.assertTrue(all(slot["segment"] == 7 for slot in slots))
        self.assertEqual(
            [slot["still_treatment"]["mode"] for slot in slots],
            ["slow_push", "pan_right", "detail_push"],
        )
        self.assertEqual([slot["photo_variant"] for slot in slots], [1, 2, 3])
        self.assertNotIn("slot_index", slots[0])   # slot_index 由 run_mv 指派

    def test_photo_vf_uses_distinct_motion_for_photo_variants(self):
        push = mv_cut._photo_vf(2.0, treatment={"mode": "slow_push"})
        pan = mv_cut._photo_vf(2.0, treatment={"mode": "pan_right"})
        detail = mv_cut._photo_vf(2.0, treatment={"mode": "detail_push"})

        self.assertNotEqual(push, pan)
        self.assertNotEqual(push, detail)
        self.assertIn("x+3", pan)
        self.assertIn("1.4", detail)

    def test_windows_from_clip_zero_clips(self):
        self.assertEqual(mv_cut._windows_from_clip("/m/x/a.mov", 0, 2.0, False), [])

    def test_anti_presentation_plan_rotates_photo_treatments_and_text_placement(self):
        slots = mv_cut._windows_from_clip("/m/group/a.jpg", 3, 2.0, False, segment=7)
        segment = {
            "anti_presentation_plan": {
                "still_treatment_modes": ["pan_left", "pan_right", "hold"],
                "text_placement": "lower_third",
            }
        }

        mv_cut._apply_anti_presentation_plan(slots, segment)

        self.assertEqual(
            [slot["still_treatment"]["mode"] for slot in slots],
            ["pan_left", "pan_right", "hold"],
        )
        self.assertTrue(all(slot["text"]["placement"] == "lower_third" for slot in slots))

    def test_allocate_segments_honors_anti_presentation_min_shots(self):
        allocation = mv_cut.allocate_segments([{
            "segment": 1,
            "kind": "opening",
            "anti_presentation_plan": {"min_shots": 3},
        }], total_dur=18.0)

        self.assertEqual(allocation[0]["n_clips"], 3)
        self.assertEqual(allocation[0]["clip_dur"], 6.0)

    def test_drawtext_chain_places_narrative_in_lower_third(self):
        original_font = mv_cut._CJK_FONT
        try:
            mv_cut._CJK_FONT = "font.ttf"
            with tempfile.TemporaryDirectory() as tmp:
                chain = mv_cut._drawtext_chain(
                    {"narrative": "Explain this", "placement": "lower_third"},
                    tmp,
                    1,
                )
        finally:
            mv_cut._CJK_FONT = original_font

        self.assertNotIn("drawbox=x=0:y=0:w=iw:h=ih", chain)
        self.assertIn("y=h-text_h-140", chain)

    def test_plan_matched_caps_at_n_clips(self):
        a = {"n_clips": 2, "clip_dur": 1.5, "budget": 6.0}
        s = {"segment": 1, "visual_desc": "拖拉電纜"}
        clip_by_seg = {1: {"picks": [{"path": "/m/拖拉電纜/a.mov"}, {"path": "/m/拖拉電纜/b.mov"},
                                     {"path": "/m/拖拉電纜/c.mov"}]}}
        # fake winfn: each clip yields 1 slot
        def winfn(path, n, dur, ka, text=None, segment=None):
            return [] if n <= 0 else [{"source": path, "segment": segment}]
        slots, entry, msgs = mv_cut._plan_matched_segment(s, a, clip_by_seg, {}, False, _winfn=winfn)
        self.assertEqual(len(slots), 2)                       # capped at n_clips
        self.assertEqual(entry["picked_scores"], ["matched", "matched"])

    def test_plan_matched_no_picks_is_gap(self):
        a = {"n_clips": 2, "clip_dur": 1.5, "budget": 6.0}
        slots, entry, _ = mv_cut._plan_matched_segment({"segment": 9}, a, {}, {}, False,
                                                       _winfn=lambda *x, **k: [])
        self.assertEqual(slots, [])
        self.assertEqual(entry["picked_scores"], ["GAP"])

    def test_plan_stock_success_and_gap(self):
        a = {"n_clips": 1, "clip_dur": 3.0, "budget": 4.0}
        s = {"segment": 2, "visual_desc": "空拍", "search_query": "aerial"}
        ok, e_ok, _ = mv_cut._plan_stock_segment(s, a, {}, "/tmp", _fetch=lambda q, o, min_dur=0: o)
        self.assertEqual(len(ok), 1)
        self.assertEqual(e_ok["picked_scores"], ["stock"])
        gap, e_gap, _ = mv_cut._plan_stock_segment(s, a, {}, "/tmp", _fetch=lambda q, o, min_dur=0: None)
        self.assertEqual(gap, [])
        self.assertEqual(e_gap["picked_scores"], ["GAP"])

    def test_plan_stock_fetch_exception_is_recoverable_gap(self):
        a = {"n_clips": 1, "clip_dur": 3.0, "budget": 4.0}
        def boom(q, o, min_dur=0):
            raise RuntimeError("network down")
        slots, entry, msgs = mv_cut._plan_stock_segment({"segment": 2, "visual_desc": "x"},
                                                        a, {}, "/tmp", _fetch=boom)
        self.assertEqual(slots, [])
        self.assertEqual(entry["picked_scores"], ["GAP"])
        self.assertTrue(any("fetch 失敗" in m for m in msgs))

    def test_plan_stock_multishot_opens_windows_not_one_long_take(self):
        """Regression (ai-video soul-v3): a fast segment (n_clips>1) must cut the
        downloaded stock into multiple windows, not one full-budget take from 0.0."""
        a = {"n_clips": 3, "clip_dur": 6.0, "budget": 18.0}
        s = {"segment": 4, "visual_desc": "團隊討論", "search_query": "team discussion"}
        fake_wins = [
            {"source": "stock.mp4", "extract_start": 2.0, "extract_dur": 6.0,
             "keep_audio": False, "text": {}, "segment": 4},
            {"source": "stock.mp4", "extract_start": 20.0, "extract_dur": 6.0,
             "keep_audio": False, "text": {}, "segment": 4},
            {"source": "stock.mp4", "extract_start": 40.0, "extract_dur": 6.0,
             "keep_audio": False, "text": {}, "segment": 4},
        ]
        slots, entry, _ = mv_cut._plan_stock_segment(
            s, a, {}, "/tmp",
            _fetch=lambda q, o, min_dur=0: o,
            _winfn=lambda *args, **kw: [dict(w) for w in fake_wins])
        self.assertEqual(len(slots), 3)
        starts = [sl["extract_start"] for sl in slots]
        self.assertEqual(starts, [2.0, 20.0, 40.0])
        self.assertTrue(all(sl["provider"] for sl in slots))
        self.assertEqual(entry["picked_scores"], ["stock", "stock", "stock"])

    def test_plan_stock_agent_mode_builds_montage_and_waits_without_scoring(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            grid_calls = []

            def fake_grid(video_path, out_path, **kwargs):
                grid_calls.append((video_path, str(out_path)))
                return {"grid_path": str(out_path), "samples": [{"timestamp_sec": 1.0}]}

            slots, entry, _ = mv_cut._plan_stock_segment(
                {"segment": 2, "visual_desc": "team discussion", "search_query": "team"},
                {"n_clips": 2, "clip_dur": 3.0, "budget": 6.0},
                {}, tmp,
                _fetch=lambda q, o, min_dur=0: o,
                visual_judge="agent",
                _gridfn=fake_grid,
                _scorefn=lambda *_: self.fail("agent mode must not invoke VLM scoring"),
            )

        self.assertEqual(slots, [])
        self.assertTrue(entry["pending_visual_review"])
        self.assertEqual(entry["picked_scores"], ["PENDING_VISUAL_REVIEW"])
        self.assertEqual(len(grid_calls), 1)
        self.assertIn("visual_review", entry["montage"])

    def test_plan_stock_agent_mode_consumes_accepted_verdict_windows(self):
        slots, entry, _ = mv_cut._plan_stock_segment(
            {"segment": 2, "visual_desc": "team discussion"},
            {"n_clips": 2, "clip_dur": 3.0, "budget": 6.0},
            {}, "/tmp",
            _fetch=lambda q, o, min_dur=0: o,
            visual_judge="agent",
            visual_verdict={
                "segment": 2,
                "accept": True,
                "picked_windows": [{"start": 1.0, "end": 4.0}, {"start": 8.0, "end": 12.0}],
            },
        )

        self.assertEqual([slot["extract_start"] for slot in slots], [1.0, 8.5])
        self.assertEqual(entry["picked_scores"], ["agent", "agent"])
        self.assertFalse(entry.get("pending_visual_review", False))

    def test_plan_stock_agent_mode_rejected_verdict_is_gap(self):
        slots, entry, _ = mv_cut._plan_stock_segment(
            {"segment": 2, "visual_desc": "wrong scene"},
            {"n_clips": 1, "clip_dur": 3.0, "budget": 3.0},
            {}, "/tmp",
            _fetch=lambda q, o, min_dur=0: o,
            visual_judge="agent",
            visual_verdict={
                "segment": 2,
                "accept": False,
                "picked_windows": [],
                "reject_reason": "off topic",
            },
        )

        self.assertEqual(slots, [])
        self.assertEqual(entry["picked_scores"], ["GAP"])
        self.assertEqual(entry["reject_reason"], "off topic")

    def test_plan_stock_agent_mode_consumes_crop_patch(self):
        slots, entry, _ = mv_cut._plan_stock_segment(
            {"segment": 2, "visual_desc": "team discussion"},
            {"n_clips": 1, "clip_dur": 3.0, "budget": 3.0},
            {}, "/tmp",
            _fetch=lambda q, o, min_dur=0: o,
            visual_judge="agent",
            visual_verdict={
                "segment": 2,
                "action": "needs_patch",
                "picked_windows": [{"start": 1.0, "end": 4.0}],
                "patch": {"type": "crop", "hint": {"x": 0.7, "y": 0.4}},
            },
        )

        self.assertEqual(slots[0]["crop_center"], {"x": 0.7, "y": 0.4})
        self.assertEqual(entry["picked_scores"], ["agent_patch"])

    def test_plan_stock_agent_mode_consumes_treatment_patch(self):
        slots, _, _ = mv_cut._plan_stock_segment(
            {"segment": 2, "visual_desc": "still idea"},
            {"n_clips": 1, "clip_dur": 3.0, "budget": 3.0},
            {}, "/tmp",
            _fetch=lambda q, o, min_dur=0: o,
            visual_judge="agent",
            visual_verdict={
                "segment": 2,
                "action": "needs_patch",
                "picked_windows": [{"start": 1.0, "end": 4.0}],
                "patch": {"type": "treatment", "hint": {"mode": "slow_push"}},
            },
        )

        self.assertEqual(slots[0]["still_treatment"], {"mode": "slow_push"})

    def test_plan_stock_multishot_cycles_when_windows_short(self):
        """Short source: fewer windows than n_clips → cycle to keep the budget."""
        a = {"n_clips": 4, "clip_dur": 5.0, "budget": 20.0}
        s = {"segment": 2, "visual_desc": "x"}
        two = [
            {"source": "stock.mp4", "extract_start": 0.0, "extract_dur": 5.0,
             "keep_audio": False, "text": {}, "segment": 2},
            {"source": "stock.mp4", "extract_start": 6.0, "extract_dur": 5.0,
             "keep_audio": False, "text": {}, "segment": 2},
        ]
        slots, entry, _ = mv_cut._plan_stock_segment(
            s, a, {}, "/tmp",
            _fetch=lambda q, o, min_dur=0: o,
            _winfn=lambda *args, **kw: [dict(w) for w in two])
        self.assertEqual(len(slots), 4)
        self.assertEqual([sl["extract_start"] for sl in slots], [0.0, 6.0, 0.0, 6.0])

    def _vlm_cands(self, got, scores):
        # shape matches score_windows output
        wins = [(0.0, 6.0), (10.0, 16.0), (20.0, 26.0), (30.0, 36.0)]
        return [{"win": w, "source": got, "source_name": "stock.mp4", "group": "g",
                 "score": float(sc), "image_desc": "d", "reason": "r"}
                for w, sc in zip(wins, scores)]

    def test_plan_stock_vlm_picks_best_windows_in_temporal_order(self):
        """Content-driven trimming: VLM scores candidate windows vs visual_desc;
        the best n win and come back in temporal order."""
        a = {"n_clips": 2, "clip_dur": 6.0, "budget": 12.0}
        s = {"segment": 4, "visual_desc": "團隊討論", "search_query": "team discussion"}
        with patch("video_pipeline_core.mv_cut.detect_shots", return_value=[(0.0, 60.0)]), \
             patch("video_pipeline_core.mv_cut.fixed_windows",
                   return_value=[(0.0, 6.0), (10.0, 16.0), (20.0, 26.0), (30.0, 36.0)]), \
             patch("video_pipeline_core.mv_cut.filter_static_windows",
                   side_effect=lambda wins, clip, **k: wins), \
             patch("video_pipeline_core.mv_cut.score_windows",
                   side_effect=lambda got, wins, vd, **k: self._vlm_cands(got, [55, 90, 40, 85])):
            slots, entry, msgs = mv_cut._plan_stock_segment(
                s, a, {}, "/tmp",
                _fetch=lambda q, o, min_dur=0: o,
                model="qwen3-vl:4b-instruct", min_score=60)
        self.assertEqual(len(slots), 2)
        self.assertEqual([sl["extract_start"] for sl in slots], [10.0, 30.0])
        self.assertEqual(entry["picked_scores"], [90, 85])

    def test_plan_stock_vlm_off_topic_is_honest_gap(self):
        """Off-topic stock (robot-dance class): even the BEST window scores at the
        rubric's off-topic tier (10/15) → recoverable GAP."""
        a = {"n_clips": 2, "clip_dur": 6.0, "budget": 12.0}
        s = {"segment": 4, "visual_desc": "團隊討論"}
        with patch("video_pipeline_core.mv_cut.detect_shots", return_value=[(0.0, 60.0)]), \
             patch("video_pipeline_core.mv_cut.fixed_windows",
                   return_value=[(0.0, 6.0), (10.0, 16.0)]), \
             patch("video_pipeline_core.mv_cut.filter_static_windows",
                   side_effect=lambda wins, clip, **k: wins), \
             patch("video_pipeline_core.mv_cut.score_windows",
                   side_effect=lambda got, wins, vd, **k: self._vlm_cands(got, [10, 15])):
            slots, entry, msgs = mv_cut._plan_stock_segment(
                s, a, {}, "/tmp",
                _fetch=lambda q, o, min_dur=0: o,
                model="qwen3-vl:4b-instruct", min_score=60)
        self.assertEqual(slots, [])
        self.assertEqual(entry["picked_scores"], ["GAP"])
        self.assertTrue(entry.get("vlm_rejected"))
        self.assertTrue(any("離題" in m for m in msgs))

    def test_plan_stock_vlm_loosely_related_is_used_not_gapped(self):
        """Regression (skill-smoke seg3 false reject): windows scoring 40
        ('loosely related' rubric tier) are legitimate stock B-roll — pick the
        best n, don't GAP the whole clip just because nothing hits 60."""
        a = {"n_clips": 2, "clip_dur": 6.0, "budget": 12.0}
        s = {"segment": 3, "visual_desc": "手沖注水特寫"}
        with patch("video_pipeline_core.mv_cut.detect_shots", return_value=[(0.0, 60.0)]), \
             patch("video_pipeline_core.mv_cut.fixed_windows",
                   return_value=[(0.0, 6.0), (10.0, 16.0), (20.0, 26.0), (30.0, 36.0)]), \
             patch("video_pipeline_core.mv_cut.filter_static_windows",
                   side_effect=lambda wins, clip, **k: wins), \
             patch("video_pipeline_core.mv_cut.score_windows",
                   side_effect=lambda got, wins, vd, **k: self._vlm_cands(got, [40, 40, 10, 40])):
            slots, entry, msgs = mv_cut._plan_stock_segment(
                s, a, {}, "/tmp",
                _fetch=lambda q, o, min_dur=0: o,
                model="qwen3-vl:4b-instruct", min_score=60)
        self.assertEqual(len(slots), 2)
        self.assertFalse(entry.get("vlm_rejected"))
        self.assertEqual(entry["picked_scores"], [40, 40])

    def test_plan_stock_vlm_unavailable_falls_back_to_mechanical(self):
        """Ollama down (exception) → mechanical windows, not GAP — no judgment
        without eyes."""
        a = {"n_clips": 2, "clip_dur": 6.0, "budget": 12.0}
        s = {"segment": 4, "visual_desc": "x"}
        two = [
            {"source": "stock.mp4", "extract_start": 0.0, "extract_dur": 6.0,
             "keep_audio": False, "text": {}, "segment": 4},
            {"source": "stock.mp4", "extract_start": 8.0, "extract_dur": 6.0,
             "keep_audio": False, "text": {}, "segment": 4},
        ]
        with patch("video_pipeline_core.mv_cut.detect_shots",
                   side_effect=RuntimeError("ollama down")):
            slots, entry, msgs = mv_cut._plan_stock_segment(
                s, a, {}, "/tmp",
                _fetch=lambda q, o, min_dur=0: o,
                _winfn=lambda *args, **kw: [dict(w) for w in two],
                model="qwen3-vl:4b-instruct", min_score=60)
        self.assertEqual(len(slots), 2)
        self.assertEqual(entry["picked_scores"], ["stock", "stock"])
        self.assertTrue(any("退回機械開窗" in m for m in msgs))

    def test_distill_subject_takes_head_clause(self):
        self.assertEqual(mv_cut._distill_subject(
            "手沖注水特寫:細水柱螺旋畫圈、咖啡粉膨脹冒泡、蒸氣上升"), "手沖注水特寫")
        self.assertEqual(mv_cut._distill_subject(
            "窗邊木桌上一杯完成的手沖咖啡,雙手捧杯,暖光"), "窗邊木桌上一杯完成的手沖咖啡")
        self.assertEqual(mv_cut._distill_subject(""), "")

    def test_plan_stock_vlm_reject_tries_next_candidate(self):
        """A wrong first clip (chocolate-box class) must not GAP the segment when
        the next-most-relevant candidate is on-topic."""
        a = {"n_clips": 2, "clip_dur": 6.0, "budget": 12.0}
        s = {"segment": 4, "visual_desc": "窗邊咖啡杯"}
        fetch_calls = []

        def fetch(q, o, min_dur=0, skip=0):
            fetch_calls.append(skip)
            return o, "pexels"

        score_calls = {"n": 0}

        def fake_score_windows(got, wins, vd, **k):
            score_calls["n"] += 1
            # candidate 1: off-topic on full desc AND distilled (2 passes of 10s);
            # candidate 2: accepted on first pass.
            if score_calls["n"] <= 2:
                return self._vlm_cands(got, [10, 15])[:len(wins)]
            return self._vlm_cands(got, [75, 60])[:len(wins)]

        with patch("video_pipeline_core.mv_cut.detect_shots", return_value=[(0.0, 60.0)]), \
             patch("video_pipeline_core.mv_cut.fixed_windows",
                   return_value=[(0.0, 6.0), (10.0, 16.0)]), \
             patch("video_pipeline_core.mv_cut.filter_static_windows",
                   side_effect=lambda wins, clip, **k: wins), \
             patch("video_pipeline_core.mv_cut.score_windows", side_effect=fake_score_windows):
            slots, entry, msgs = mv_cut._plan_stock_segment(
                s, a, {}, "/tmp", _fetch=fetch,
                model="qwen3-vl:4b-instruct", min_score=60)
        self.assertEqual(fetch_calls, [0, 1])          # tried candidate #2
        self.assertEqual(len(slots), 2)                # accepted from candidate #2
        self.assertFalse(entry.get("vlm_rejected"))
        self.assertEqual(entry["picked_scores"], [75, 60])

    def test_plan_stock_multishot_window_failure_falls_back_to_single(self):
        a = {"n_clips": 3, "clip_dur": 6.0, "budget": 18.0}
        s = {"segment": 2, "visual_desc": "x"}
        slots, entry, _ = mv_cut._plan_stock_segment(
            s, a, {}, "/tmp",
            _fetch=lambda q, o, min_dur=0: o,
            _winfn=lambda *args, **kw: [])
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["extract_start"], 0.0)
        self.assertEqual(slots[0]["extract_dur"], 18.0)


class PlanMvTest(unittest.TestCase):
    def test_maps_selected_to_slots_centered(self):
        selected = [{"source": "a.mov", "win": (0.0, 4.0), "group": "g"},
                    {"source": "b.mov", "win": (10.0, 14.0), "group": "h"}]
        grid = [(0.0, 1.5), (1.5, 3.0)]   # 1.5s beat slots
        plan = mv_cut.plan_mv(selected, grid)
        self.assertEqual(len(plan), 2)
        # slot 0: window 0-4 mid=2.0, take 1.5 centered → start 1.25
        self.assertAlmostEqual(plan[0]["extract_start"], 1.25)
        self.assertAlmostEqual(plan[0]["extract_dur"], 1.5)
        self.assertEqual(plan[0]["source"], "a.mov")
        self.assertEqual(plan[1]["slot_index"], 1)

    def test_take_clamped_to_window_length(self):
        selected = [{"source": "a.mov", "win": (0.0, 1.0), "group": "g"}]
        grid = [(0.0, 3.0)]               # slot wants 3s but window only 1s
        plan = mv_cut.plan_mv(selected, grid)
        self.assertAlmostEqual(plan[0]["extract_dur"], 1.0)   # clamped
        self.assertAlmostEqual(plan[0]["extract_start"], 0.0)

    def test_stops_at_shorter_of_selected_or_grid(self):
        selected = [{"source": "a.mov", "win": (0.0, 4.0)}]
        grid = [(0, 1.5), (1.5, 3.0), (3.0, 4.5)]
        self.assertEqual(len(mv_cut.plan_mv(selected, grid)), 1)


class ShotStatsTest(unittest.TestCase):
    def test_stats_basic(self):
        shots = [(0, 1.0), (1.0, 2.0), (2.0, 5.0), (5.0, 12.0)]  # 1,1,3,7s
        st = mv_cut._shot_stats(shots)
        self.assertEqual(st["n_shots"], 4)
        self.assertEqual(st["median"], 2.0)         # (1+3)/2
        self.assertEqual(st["total_dur"], 12.0)
        self.assertEqual(st["cuts_per_min"], 20.0)  # 4 / (12/60)
        self.assertEqual(st["dist"], {"<1s": 0, "1-3s": 2, "3-6s": 1, ">6s": 1})

    def test_empty(self):
        self.assertEqual(mv_cut._shot_stats([])["n_shots"], 0)

    def test_compare_to_gold_pace(self):
        slow = {"median": 8.0, "cuts_per_min": 7.0}
        c = mv_cut.compare_to_gold({**slow, "n_shots": 1})
        self.assertEqual(c["pace"], "太慢(剪太少)")
        ok = mv_cut.compare_to_gold({"median": 1.5, "cuts_per_min": 27.0, "n_shots": 1})
        self.assertEqual(ok["pace"], "接近 66 期節奏")


class AllocateSegmentsTest(unittest.TestCase):
    def test_montage_gets_multiple_clips_hold_gets_one(self):
        segs = [{"segment": 1, "kind": "opening"},
                {"segment": 2, "layout": "montage", "pace": "fast"},
                {"segment": 3, "hold": True, "must_include": "x"}]
        alloc = mv_cut.allocate_segments(segs, total_dur=30.0, fast_clip=1.5)
        self.assertEqual(alloc[0]["n_clips"], 1)          # opening = single
        self.assertGreater(alloc[1]["n_clips"], 1)        # montage = many
        self.assertEqual(alloc[2]["n_clips"], 1)          # hold = single
        self.assertAlmostEqual(alloc[0]["budget"], 10.0)  # 30/3 equal budget

    def test_clip_dur_divides_budget(self):
        segs = [{"segment": 1, "layout": "montage"}]
        a = mv_cut.allocate_segments(segs, total_dur=16.0, fast_clip=1.6)
        self.assertAlmostEqual(a[0]["n_clips"] * a[0]["clip_dur"], 16.0, places=1)

    def test_weight_gives_hold_more_budget(self):
        # pacing 調勻:weight 2.0 的 hold 段拿到約 2 倍預算(隊呼長 hold)
        segs = [{"segment": 1, "layout": "montage"},
                {"segment": 2, "hold": True, "weight": 2.0}]
        a = mv_cut.allocate_segments(segs, total_dur=30.0)
        self.assertAlmostEqual(a[0]["budget"], 10.0, places=1)   # 30*1/3
        self.assertAlmostEqual(a[1]["budget"], 20.0, places=1)   # 30*2/3
        self.assertEqual(a[1]["n_clips"], 1)                     # hold 仍單長 clip

    def test_default_weight_is_equal_budget(self):
        segs = [{"segment": 1}, {"segment": 2}, {"segment": 3}]
        a = mv_cut.allocate_segments(segs, total_dur=30.0)
        self.assertTrue(all(abs(x["budget"] - 10.0) < 0.01 for x in a))

    def test_empty(self):
        self.assertEqual(mv_cut.allocate_segments([], 30.0), [])
        self.assertEqual(mv_cut.allocate_segments([{"segment": 1}], 0), [])

    def test_pacing_preferred_shot_sec_overrides_fast_clip(self):
        """Contract pacing wins: [4,8] → ~6s shots, so a 24s fast segment gets
        ~4 cuts instead of 16 (engine allocation in step with Node 9 slots)."""
        segs = [{"segment": 1, "pace": "fast", "pacing": {"preferred_shot_sec": [4, 8]}}]
        a = mv_cut.allocate_segments(segs, total_dur=24.0, fast_clip=1.5)
        self.assertEqual(a[0]["n_clips"], 4)            # 24 / 6 = 4
        self.assertAlmostEqual(a[0]["clip_dur"], 6.0, places=1)

    def test_pacing_scalar_shot_sec(self):
        segs = [{"segment": 1, "pace": "fast", "pacing": {"preferred_shot_sec": 3}}]
        a = mv_cut.allocate_segments(segs, total_dur=12.0, fast_clip=1.5)
        self.assertEqual(a[0]["n_clips"], 4)            # 12 / 3

    def test_pacing_ignored_for_hold_segments(self):
        segs = [{"segment": 1, "hold": True, "pacing": {"preferred_shot_sec": [4, 8]}}]
        a = mv_cut.allocate_segments(segs, total_dur=20.0)
        self.assertEqual(a[0]["n_clips"], 1)

    def test_no_pacing_keeps_fast_clip_default(self):
        segs = [{"segment": 1, "pace": "fast"}]
        a = mv_cut.allocate_segments(segs, total_dur=15.0, fast_clip=1.5)
        self.assertEqual(a[0]["n_clips"], 10)           # 15 / 1.5 unchanged

    def test_music_attention_budget_forces_non_hold_segment_to_cut(self):
        segs = [{
            "segment": 1,
            "attention_budget": {"owner": "music", "shot_sec": [0.8, 2.0]},
        }]
        a = mv_cut.allocate_segments(segs, total_dur=12.0)
        self.assertEqual(a[0]["n_clips"], 9)
        self.assertAlmostEqual(a[0]["clip_dur"], 12.0 / 9, places=2)

    def test_music_attention_budget_overrides_generic_hold(self):
        segs = [{
            "segment": 1,
            "hold": True,
            "attention_budget": {"owner": "music", "shot_sec": [0.8, 2.0]},
        }]
        a = mv_cut.allocate_segments(segs, total_dur=12.0)
        self.assertEqual(a[0]["n_clips"], 9)

    def test_music_attention_budget_overrides_slower_legacy_pacing(self):
        segs = [{
            "segment": 1,
            "pace": "fast",
            "pacing": {"preferred_shot_sec": [6.0, 10.0]},
            "attention_budget": {"owner": "music", "shot_sec": [1.5, 4.0]},
        }]
        a = mv_cut.allocate_segments(segs, total_dur=12.0)
        self.assertEqual(a[0]["n_clips"], 4)

    def test_bookend_hold_is_preserved_with_music_attention_budget(self):
        segs = [{
            "segment": 1,
            "kind": "opening",
            "hold": True,
            "attention_budget": {"owner": "music", "shot_sec": [0.8, 2.0]},
        }]
        a = mv_cut.allocate_segments(segs, total_dur=12.0)
        self.assertEqual(a[0]["n_clips"], 1)


class TrimBeatsToTargetTest(unittest.TestCase):
    """Music length sets rhythm, brief target sets runtime (soul-v5: a 122.9s
    track stretched a 45s film to 123s and cascaded 8 pacing fails)."""

    BEATS = [0.0, 0.5, 1.0, 10.0, 20.0, 30.0, 44.6, 45.2, 60.0, 122.9]

    def test_no_target_returns_all(self):
        self.assertEqual(mv_cut.trim_beats_to_target(self.BEATS, None), self.BEATS)
        self.assertEqual(mv_cut.trim_beats_to_target(self.BEATS, 0), self.BEATS)

    def test_target_caps_at_last_beat_within(self):
        out = mv_cut.trim_beats_to_target(self.BEATS, 45.0)
        self.assertEqual(out[-1], 44.6)          # last beat <= 45, stays on the grid

    def test_target_longer_than_music_unchanged(self):
        self.assertEqual(mv_cut.trim_beats_to_target(self.BEATS, 300.0), self.BEATS)

    def test_tiny_target_keeps_two_beats(self):
        out = mv_cut.trim_beats_to_target(self.BEATS, 0.2)
        self.assertEqual(len(out), 2)

    def test_empty_beats(self):
        self.assertEqual(mv_cut.trim_beats_to_target([], 45.0), [])


class ValidateMvScriptTest(unittest.TestCase):
    def _ok_script(self):
        return {"style": "mv", "music": {"brief": "熱血"},
                "segments": [
                    {"segment": 1, "kind": "opening", "visual_desc": "列隊",
                     "needs_review": True},
                    {"segment": 2, "visual_desc": "拖拉電纜", "layout": "montage",
                     "audio_role": "music"},
                    {"segment": 3, "visual_desc": "致詞", "must_include": "必放項目",
                     "keep_audio": True, "audio_role": "duck"}]}

    def test_valid_script_passes(self):
        r = mv_cut.validate_mv_script(self._ok_script())
        self.assertTrue(r["can_run"])
        self.assertEqual(r["errors"], 0)

    def test_bad_audio_role_errors(self):
        s = self._ok_script()
        s["segments"][1]["audio_role"] = "loud"
        r = mv_cut.validate_mv_script(s)
        self.assertFalse(r["can_run"])
        self.assertTrue(any(i["field"] == "audio_role" for i in r["issues"]))

    def test_missing_visual_desc_errors(self):
        s = self._ok_script()
        del s["segments"][1]["visual_desc"]
        r = mv_cut.validate_mv_script(s)
        self.assertFalse(r["can_run"])

    def test_title_segment_exempt_from_visual_desc(self):
        s = {"style": "mv", "segments": [{"segment": 1, "kind": "title"},
                                         {"segment": 2, "visual_desc": "x"}]}
        self.assertTrue(mv_cut.validate_mv_script(s)["can_run"])

    def test_opening_without_review_warns(self):
        s = self._ok_script()
        s["segments"][0]["needs_review"] = False
        r = mv_cut.validate_mv_script(s)
        self.assertTrue(r["can_run"])              # warning, not error
        self.assertTrue(any(i["level"] == "warning" and i["field"] == "needs_review"
                            for i in r["issues"]))

    def test_must_include_without_audio_warns(self):
        s = {"style": "mv", "segments": [
            {"segment": 1, "visual_desc": "a"},
            {"segment": 2, "visual_desc": "致詞", "must_include": "必放項目"}]}
        r = mv_cut.validate_mv_script(s)
        self.assertTrue(any(i["field"] == "keep_audio" and i["level"] == "warning"
                            for i in r["issues"]))

    def test_too_few_segments_errors(self):
        self.assertFalse(mv_cut.validate_mv_script(
            {"style": "mv", "segments": [{"segment": 1, "visual_desc": "x"}]})["can_run"])

    def test_text_layer_fields_accepted(self):
        s = {"style": "mv", "segments": [
            {"segment": 1, "visual_desc": "a", "label": "礙子拆線作業",
             "narrative": "傳承精技", "subtitle": "auto"},
            {"segment": 2, "visual_desc": "b"}]}
        self.assertTrue(mv_cut.validate_mv_script(s)["can_run"])

    def test_non_string_label_errors(self):
        s = {"style": "mv", "segments": [
            {"segment": 1, "visual_desc": "a", "label": 123}, {"segment": 2, "visual_desc": "b"}]}
        self.assertFalse(mv_cut.validate_mv_script(s)["can_run"])

    def test_speaking_segment_without_subtitle_warns(self):
        s = {"style": "mv", "segments": [
            {"segment": 1, "visual_desc": "致詞", "audio_role": "duck"},
            {"segment": 2, "visual_desc": "b"}]}
        r = mv_cut.validate_mv_script(s)
        self.assertTrue(r["can_run"])   # warning not error
        self.assertTrue(any(i["field"] == "subtitle" and i["level"] == "warning"
                            for i in r["issues"]))


class GridDurationsTest(unittest.TestCase):
    def test_durations_match_spans(self):
        grid = [(0.0, 2.0), (2.0, 4.3)]
        self.assertEqual(mv_cut.grid_durations(grid), [2.0, 2.3])

    def test_durations_sum_to_total_span(self):
        grid = mv_cut.beats_to_cut_grid([round(i * 0.5, 3) for i in range(9)],
                                        every_n_beats=4, min_seg=1.0, total=6.0)
        self.assertAlmostEqual(sum(mv_cut.grid_durations(grid)), 6.0, places=3)


class FilterShotsTest(unittest.TestCase):
    def test_short_shot_merges_into_previous(self):
        shots = [(0.0, 3.0), (3.0, 3.4), (3.4, 7.0)]  # middle 0.4s shot
        self.assertEqual(mv_cut.filter_shots(shots, min_shot=1.0),
                         [(0.0, 3.4), (3.4, 7.0)])

    def test_short_first_shot_merges_into_next(self):
        shots = [(0.0, 0.5), (0.5, 4.0)]
        self.assertEqual(mv_cut.filter_shots(shots, min_shot=1.0), [(0.0, 4.0)])

    def test_no_merge_when_all_long(self):
        shots = [(0.0, 3.0), (3.0, 6.0)]
        self.assertEqual(mv_cut.filter_shots(shots, min_shot=1.0), shots)

    def test_unsorted_shots_sorted(self):
        shots = [(3.0, 6.0), (0.0, 3.0)]
        self.assertEqual(mv_cut.filter_shots(shots, min_shot=0.1),
                         [(0.0, 3.0), (3.0, 6.0)])


class FixedWindowsTest(unittest.TestCase):
    def test_nonoverlapping_windows_with_kept_tail(self):
        self.assertEqual(mv_cut.fixed_windows(10.0, win=4.0, min_seg=1.0),
                         [(0.0, 4.0), (4.0, 8.0), (8.0, 10.0)])

    def test_short_tail_merges(self):
        self.assertEqual(mv_cut.fixed_windows(8.5, win=4.0, min_seg=1.0),
                         [(0.0, 4.0), (4.0, 8.5)])

    def test_overlapping_hop(self):
        wins = mv_cut.fixed_windows(10.0, win=4.0, hop=2.0, min_seg=0.5)
        self.assertEqual(wins[0], (0.0, 4.0))
        self.assertEqual(wins[1], (2.0, 6.0))

    def test_zero_total(self):
        self.assertEqual(mv_cut.fixed_windows(0.0, win=4.0), [])


class ShotMidpointsTest(unittest.TestCase):
    def test_midpoints(self):
        self.assertEqual(mv_cut.shot_midpoints([(0.0, 4.0), (4.0, 6.0)]), [2.0, 5.0])


if __name__ == "__main__":
    unittest.main()
