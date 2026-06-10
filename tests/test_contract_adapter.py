"""contract_adapter — canonical-first runtime adapter(see roadmap.md).
segment_contract.json(SPEC)→ flat MV script(execution payload)→ 既有鏈。"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core import contract_adapter as ca
from video_pipeline_core import mv_cut

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class ContractToMvScriptTest(unittest.TestCase):
    def _seg(self, **over):
        base = {"core": {"section_role": "montage", "story_purpose": "x", "timeline_source": "beat"},
                "material_fit": {"visual_desc": "拖拉電纜", "material_hint": "拖拉電纜", "reason": "r"},
                "audio": {"role": "music", "reason": "r"},
                "visual_style": {"layout": "montage", "pace": "fast", "reason": "r"},
                "text_layer": "none"}
        for k, v in over.items():
            base[k] = v
        return base

    def test_montage_maps_layout_pace(self):
        s = ca.contract_to_mv_script({"segments": [self._seg()]})
        seg = s["segments"][0]
        self.assertEqual(seg["layout"], "montage")
        self.assertEqual(seg["pace"], "fast")
        self.assertEqual(seg["audio_role"], "music")
        self.assertNotIn("keep_audio", seg)
        self.assertNotIn("label", seg)          # text_layer none → 不上字

    def test_opening_maps_kind_and_weight(self):
        seg = self._seg(core={"section_role": "opening", "story_purpose": "x",
                              "timeline_source": "fixed", "review_required": True},
                        visual_style={"layout": "single", "pace": "hold", "reason": "r"})
        s = ca.contract_to_mv_script({"segments": [seg]})
        o = s["segments"][0]
        self.assertEqual(o["kind"], "opening")
        self.assertTrue(o["needs_review"])
        self.assertEqual(o["pace"], "hold")
        self.assertTrue(o["hold"])
        self.assertNotIn("layout", o)           # single → 不輸出 layout(MV 只認 montage/collage/framed)
        self.assertGreater(o["weight"], 1.0)     # bookend 偏重

    def test_duck_keeps_audio_and_text_passthrough(self):
        seg = self._seg(audio={"role": "duck", "reason": "r"},
                        material_fit={"visual_desc": "致詞", "must_include": "主任", "reason": "r"},
                        text_layer={"subtitle": "auto", "name_super": {"text": "主任"}, "reason": "r"},
                        visual_style={"layout": "single", "pace": "hold", "reason": "r"})
        seg["core"] = {"section_role": "hold", "story_purpose": "x", "timeline_source": "fixed"}
        o = ca.contract_to_mv_script({"segments": [seg]})["segments"][0]
        self.assertEqual(o["audio_role"], "duck")
        self.assertTrue(o["keep_audio"])
        self.assertEqual(o["subtitle"], "auto")
        self.assertEqual(o["must_include"], "主任")
        self.assertEqual(o["name_super"], {"text": "主任"})

    def test_editing_grammar_hero_locked_is_heavy(self):
        seg = self._seg(editing_grammar={"role": "hero", "compressibility": "locked", "reason": "r"})
        w = ca.contract_to_mv_script({"segments": [seg]})["segments"][0]["weight"]
        self.assertGreaterEqual(w, 1.5)

    def test_trace_and_top_level_passthrough(self):
        c = {"style": "mv", "music": {"brief": "熱血"}, "segments": [self._seg(segment=7)]}
        s = ca.contract_to_mv_script(c)
        self.assertEqual(s["style"], "mv")
        self.assertEqual(s["music"]["brief"], "熱血")
        self.assertEqual(s["segments"][0]["_from_contract"], 7)   # 可追溯

    def test_example_contract_adapts_and_validates(self):
        c = json.loads((EXAMPLES / "segment_contract_graduation_mv.json").read_text(encoding="utf-8"))
        script = ca.contract_to_mv_script(c)
        self.assertEqual(len(script["segments"]), len(c["segments"]))
        v = mv_cut.validate_mv_script(script)         # 生成的 payload 必須能被既有鏈驗過
        self.assertTrue(v.get("can_run"), [i for i in v.get("issues", []) if i.get("level") == "error"])

    def test_adapt_contract_file_writes_traceable_payload(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "generated_mv_script.json"
            result = ca.adapt_contract_file(
                EXAMPLES / "segment_contract_graduation_mv.json",
                out_path=out,
                categories_path=EXAMPLES / "material_categories.json",
            )
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(result["ok"])
            self.assertEqual(payload["_artifact_role"], "legacy_runtime_payload")
            self.assertEqual(payload["_adapter"], "contract_adapter.py")
            self.assertTrue(payload["_contract_hash"].startswith("sha256:"))
            self.assertEqual(payload["_generated_from"], str(EXAMPLES / "segment_contract_graduation_mv.json"))
            self.assertEqual(len(payload["segments"]), 5)

    def test_video_tools_contract_adapt_cli_exposes_canonical_entrypoint(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "generated_mv_script.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "contract-adapt",
                    str(EXAMPLES / "segment_contract_graduation_mv.json"),
                    "--categories",
                    str(EXAMPLES / "material_categories.json"),
                    "--out",
                    str(out),
                ],
                cwd=EXAMPLES.parent,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["_artifact_role"], "legacy_runtime_payload")
            self.assertEqual(len(payload["segments"]), 5)

    def test_adapt_contract_file_rejects_unknown_category(self):
        c = json.loads((EXAMPLES / "segment_contract_graduation_mv.json").read_text(encoding="utf-8"))
        c["segments"][0]["material_fit"]["category"] = "not_a_real_category"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad_contract.json"
            p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
            result = ca.adapt_contract_file(
                p,
                out_path=Path(d) / "generated_mv_script.json",
                categories_path=EXAMPLES / "material_categories.json",
            )
            self.assertFalse(result["ok"])
            self.assertEqual(result["stage"], "validate_contract")
            self.assertFalse((Path(d) / "generated_mv_script.json").exists())

    def test_run_contract_writes_manifest_and_generated_payload(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            material_db = Path(d) / "material_db.json"
            music = Path(d) / "bgm.mp3"
            material_db.write_text(json.dumps({"files": []}), encoding="utf-8")
            music.write_bytes(b"fake")

            def fake_mv_chain(script, material_db_arg, out_path, music_path=None, mat_dir="/tmp", verbose=True, **kwargs):
                Path(out_path).write_bytes(b"mp4")
                state = Path(out_path).parent / "state.json"
                state.write_text(json.dumps({"final": out_path, "next_action": None}), encoding="utf-8")
                return {"final": out_path, "state": str(state),
                        "plan": [{"segment": 1, "source": "a.mp4", "extract_start": 0,
                                  "extract_dur": 1.5, "slot_index": 0, "slot_dur": 1.5}]}

            def fake_music_structure(audio_path, out_path, **_kwargs):
                Path(out_path).write_text(json.dumps({"source_audio": str(audio_path)}), encoding="utf-8")
                return {"ok": True, "music_structure": str(out_path)}

            with patch("video_pipeline_core.mv_cut.mv_chain", fake_mv_chain), \
                 patch("video_pipeline_core.music_structure.write_music_structure", fake_music_structure):
                result = ca.run_contract(
                    EXAMPLES / "segment_contract_graduation_mv.json",
                    material_db=material_db,
                    out_path=outdir / "final.mp4",
                    music_path=music,
                    categories_path=EXAMPLES / "material_categories.json",
                    mat_dir=outdir,
                    verbose=False,
                )

            manifest = json.loads((outdir / "artifact_manifest.json").read_text(encoding="utf-8"))
            payload = json.loads((outdir / "generated_mv_script.json").read_text(encoding="utf-8"))
            self.assertTrue(result["render_ok"])
            self.assertEqual(payload["_artifact_role"], "legacy_runtime_payload")
            self.assertEqual(manifest["canonical_contract"], str(EXAMPLES / "segment_contract_graduation_mv.json"))
            self.assertEqual(manifest["generated_payload"], str(outdir / "generated_mv_script.json"))
            self.assertEqual(manifest["final"], str(outdir / "final.mp4"))
            self.assertEqual(manifest["state"], str(outdir / "state.json"))
            self.assertEqual(manifest["material_db"], str(material_db))
            self.assertEqual(manifest["music"], str(music))
            self.assertEqual(manifest["music_structure"], str(outdir / "music_structure.json"))
            self.assertEqual(manifest["model_routes"], str(outdir / "model_routes.json"))
            self.assertEqual(manifest["assembly_plan"], str(outdir / "assembly_plan.json"))
            self.assertEqual(manifest["timeline_build"], str(outdir / "timeline_build.json"))
            self.assertEqual(manifest["editor_review"], str(outdir / "editor_review.json"))
            self.assertEqual(manifest["contract_hash"], payload["_contract_hash"])
            for optional_key in (
                "generated_asset_manifest",
                "motion_graphics_contract",
                "motion_graphics_render_plan",
                "motion_graphics_manifest",
                "revision_plan",
                "timeline_invariants",
                "broll_audit",
                "caption_audit",
                "keyframe_grid",
                "visual_audit",
                "creator_profile",
                "creator_profile_applied",
                "capcut_draft_manifest",
                "capcut_export_manifest",
            ):
                self.assertIn(optional_key, manifest)
                self.assertIsNone(manifest[optional_key])
            self.assertTrue((outdir / "assembly_plan.json").exists())
            self.assertTrue((outdir / "timeline_build.json").exists())

    def test_run_contract_emits_capcut_draft_when_backend_selected(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            material_db = Path(d) / "material_db.json"
            music = Path(d) / "bgm.mp3"
            material_db.write_text(json.dumps({"files": []}), encoding="utf-8")
            music.write_bytes(b"fake")

            profile_cfg = Path(d) / "build_profile.cfg.json"
            profile_cfg.write_text(json.dumps({
                "build_profile_version": 1,
                "render_backend": "capcut_draft",
                "requires_human_or_computer_use": True,
            }), encoding="utf-8")

            def fake_mv_chain(script, material_db_arg, out_path, music_path=None, mat_dir="/tmp", verbose=True, **kwargs):
                Path(out_path).write_bytes(b"mp4")
                state = Path(out_path).parent / "state.json"
                state.write_text(json.dumps({"final": out_path, "next_action": None}), encoding="utf-8")
                return {"final": out_path, "state": str(state),
                        "plan": [{"segment": 1, "source": "a.mp4", "extract_start": 0,
                                  "extract_dur": 1.5, "slot_index": 0, "slot_dur": 1.5}]}

            def fake_music_structure(audio_path, out_path, **_kwargs):
                Path(out_path).write_text(json.dumps({"source_audio": str(audio_path)}), encoding="utf-8")
                return {"ok": True, "music_structure": str(out_path)}

            with patch("video_pipeline_core.mv_cut.mv_chain", fake_mv_chain), \
                 patch("video_pipeline_core.music_structure.write_music_structure", fake_music_structure):
                ca.run_contract(
                    EXAMPLES / "segment_contract_graduation_mv.json",
                    material_db=material_db,
                    out_path=outdir / "final.mp4",
                    music_path=music,
                    categories_path=EXAMPLES / "material_categories.json",
                    build_profile_config_path=profile_cfg,
                    mat_dir=outdir,
                    verbose=False,
                )

            self.assertTrue((outdir / "capcut_draft_manifest.json").exists())
            draft = json.loads((outdir / "capcut_draft_manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(draft["requires_human_or_computer_use"])
            self.assertEqual(draft["draft_serialization"]["status"], "pending")
            manifest = json.loads((outdir / "artifact_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["capcut_draft_manifest"], str(outdir / "capcut_draft_manifest.json"))
            # ffmpeg final.mp4 is still the canonical render
            self.assertEqual(manifest["final"], str(outdir / "final.mp4"))

    def test_run_contract_applies_creator_profile_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            material_db = Path(d) / "material_db.json"
            music = Path(d) / "bgm.mp3"
            material_db.write_text(json.dumps({"files": []}), encoding="utf-8")
            music.write_bytes(b"fake")

            creator = Path(d) / "creator_profile.json"
            creator.write_text(json.dumps({
                "profile_version": 1,
                "editing_defaults": {"broll_ratio_target": 0.4, "max_source_repeats": 2},
            }), encoding="utf-8")

            def fake_mv_chain(script, material_db_arg, out_path, music_path=None, mat_dir="/tmp", verbose=True, **kwargs):
                Path(out_path).write_bytes(b"mp4")
                state = Path(out_path).parent / "state.json"
                state.write_text(json.dumps({"final": out_path, "next_action": None}), encoding="utf-8")
                return {"final": out_path, "state": str(state),
                        "plan": [{"segment": 1, "source": "a.mp4", "extract_start": 0,
                                  "extract_dur": 1.5, "slot_index": 0, "slot_dur": 1.5}]}

            def fake_music_structure(audio_path, out_path, **_kwargs):
                Path(out_path).write_text(json.dumps({"source_audio": str(audio_path)}), encoding="utf-8")
                return {"ok": True, "music_structure": str(out_path)}

            with patch("video_pipeline_core.mv_cut.mv_chain", fake_mv_chain), \
                 patch("video_pipeline_core.music_structure.write_music_structure", fake_music_structure):
                ca.run_contract(
                    EXAMPLES / "segment_contract_graduation_mv.json",
                    material_db=material_db,
                    out_path=outdir / "final.mp4",
                    music_path=music,
                    categories_path=EXAMPLES / "material_categories.json",
                    creator_profile_path=creator,
                    mat_dir=outdir,
                    verbose=False,
                )

            # creator defaults flow into build_profile broll policy
            bp = json.loads((outdir / "build_profile.json").read_text(encoding="utf-8"))
            self.assertEqual(bp["broll_policy"]["target_ratio"], 0.4)
            self.assertEqual(bp["broll_policy"]["max_source_repeats"], 2)
            # lineage recorded + indexed in manifest
            applied = json.loads((outdir / "creator_profile_applied.json").read_text(encoding="utf-8"))
            self.assertIn("broll_ratio_target", applied["applied"])
            manifest = json.loads((outdir / "artifact_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["creator_profile"], str(outdir / "creator_profile.json"))
            self.assertEqual(manifest["creator_profile_applied"], str(outdir / "creator_profile_applied.json"))

    def test_run_contract_blocks_on_spec_review(self):
        """A SPEC that will silently fail downstream (subtitle:auto on a no-speech
        segment) must stop at the pre-BUILD spec_review gate — before any music
        analysis or render cost — and route revise:director."""
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            material_db = Path(d) / "material_db.json"
            music = Path(d) / "bgm.mp3"
            material_db.write_text(json.dumps({"files": []}), encoding="utf-8")
            music.write_bytes(b"fake")

            contract = json.loads(
                (EXAMPLES / "segment_contract_graduation_mv.json").read_text(encoding="utf-8"))
            contract.pop("brief_ref", None)
            seg0 = contract["segments"][0]
            seg0["audio"] = {"role": "music", "reason": "r"}
            seg0["text_layer"] = {"subtitle": "auto", "reason": "r"}

            result = ca.run_contract(
                contract,
                material_db=material_db,
                out_path=outdir / "final.mp4",
                music_path=music,
                categories_path=EXAMPLES / "material_categories.json",
                mat_dir=outdir,
                verbose=False,
            )

            self.assertFalse(result["ok"])
            self.assertEqual(result["stage"], "spec_review")
            self.assertEqual(result["next_action"], "revise:director(spec_review)")
            review = json.loads((outdir / "spec_review.json").read_text(encoding="utf-8"))
            self.assertFalse(review["ready_for_build"])
            self.assertEqual(review["blocking"][0]["rule"], "subtitle_auto_no_speech")
            state = json.loads((outdir / "state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["next_action"].startswith("revise:director"))
            # No render/music side effects were paid for
            self.assertFalse((outdir / "final.mp4").exists())

    def test_run_contract_passes_brief_target_to_mv_chain(self):
        """brief.target_length must reach the engine as target_sec so allocation
        is capped at the brief runtime, not the music length (soul-v5 lesson)."""
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            outdir.mkdir(parents=True)
            (outdir / "brief.json").write_text(
                json.dumps({"target_length": "45 seconds"}), encoding="utf-8")
            material_db = Path(d) / "material_db.json"
            music = Path(d) / "bgm.mp3"
            material_db.write_text(json.dumps({"files": []}), encoding="utf-8")
            music.write_bytes(b"fake")

            captured = {}

            def fake_mv_chain(script, material_db_arg, out_path, music_path=None,
                              mat_dir="/tmp", verbose=True, **kwargs):
                captured.update(kwargs)
                Path(out_path).write_bytes(b"mp4")
                state = Path(out_path).parent / "state.json"
                state.write_text(json.dumps({"final": out_path, "next_action": None}), encoding="utf-8")
                return {"final": out_path, "state": str(state), "plan": []}

            def fake_music_structure(audio_path, out_path, **_kwargs):
                Path(out_path).write_text(json.dumps({"source_audio": str(audio_path)}), encoding="utf-8")
                return {"ok": True, "music_structure": str(out_path)}

            # Pass the contract as a dict without brief_ref so run_contract does
            # not copy the example brief over our seeded 45s one.
            contract = json.loads(
                (EXAMPLES / "segment_contract_graduation_mv.json").read_text(encoding="utf-8"))
            contract.pop("brief_ref", None)

            with patch("video_pipeline_core.mv_cut.mv_chain", fake_mv_chain), \
                 patch("video_pipeline_core.music_structure.write_music_structure", fake_music_structure):
                ca.run_contract(
                    contract,
                    material_db=material_db,
                    out_path=outdir / "final.mp4",
                    music_path=music,
                    categories_path=EXAMPLES / "material_categories.json",
                    mat_dir=outdir,
                    verbose=False,
                )

            self.assertEqual(captured.get("target_sec"), 45.0)

    def test_run_contract_auto_generates_audits_when_enabled(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            material_db = Path(d) / "material_db.json"
            music = Path(d) / "bgm.mp3"
            material_db.write_text(json.dumps({"files": []}), encoding="utf-8")
            music.write_bytes(b"fake")

            # build_profile with the deterministic verification tools enabled
            profile_cfg = Path(d) / "build_profile.cfg.json"
            profile_cfg.write_text(json.dumps({
                "build_profile_version": 1,
                "verification_tools": {
                    "timeline_invariants": True,
                    "broll_audit": True,
                    "caption_audit": True,
                },
            }), encoding="utf-8")

            def fake_mv_chain(script, material_db_arg, out_path, music_path=None, mat_dir="/tmp", verbose=True, **kwargs):
                Path(out_path).write_bytes(b"mp4")
                state = Path(out_path).parent / "state.json"
                state.write_text(json.dumps({"final": out_path, "next_action": None}), encoding="utf-8")
                return {"final": out_path, "state": str(state),
                        "plan": [{"segment": 1, "source": "a.mp4", "extract_start": 0,
                                  "extract_dur": 1.5, "slot_index": 0, "slot_dur": 1.5}]}

            def fake_music_structure(audio_path, out_path, **_kwargs):
                Path(out_path).write_text(json.dumps({"source_audio": str(audio_path)}), encoding="utf-8")
                return {"ok": True, "music_structure": str(out_path)}

            with patch("video_pipeline_core.mv_cut.mv_chain", fake_mv_chain), \
                 patch("video_pipeline_core.music_structure.write_music_structure", fake_music_structure):
                ca.run_contract(
                    EXAMPLES / "segment_contract_graduation_mv.json",
                    material_db=material_db,
                    out_path=outdir / "final.mp4",
                    music_path=music,
                    categories_path=EXAMPLES / "material_categories.json",
                    build_profile_config_path=profile_cfg,
                    mat_dir=outdir,
                    verbose=False,
                )

            manifest = json.loads((outdir / "artifact_manifest.json").read_text(encoding="utf-8"))
            # deterministic audits produced and indexed
            for role in ("timeline_invariants", "broll_audit", "caption_audit"):
                self.assertTrue((outdir / f"{role}.json").exists(), f"{role}.json missing")
                self.assertEqual(manifest[role], str(outdir / f"{role}.json"))
            # ffmpeg-dependent tools were left disabled -> still null
            self.assertIsNone(manifest["keyframe_grid"])
            self.assertIsNone(manifest["visual_audit"])
            audit = json.loads((outdir / "timeline_invariants.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["artifact_role"], "timeline_invariants")
            self.assertTrue((outdir / "editor_review.json").exists())
            self.assertTrue((outdir / "model_routes.json").exists())

    def test_run_contract_writes_light_effects_artifacts_when_profile_enabled(self):
        contract = {
            "style": "mv",
            "segments": [self._seg(
                material_fit={"visual_desc": "city opening", "media": "photo", "reason": "r"},
                visual_style={"layout": "single", "pace": "hold", "grade": "warm", "reason": "r"},
                text_layer={"label": "Opening", "reason": "r"},
            ), self._seg(segment=2)],
        }
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            material_db = Path(d) / "material_db.json"
            music = Path(d) / "bgm.mp3"
            profile = Path(d) / "profile.json"
            material_db.write_text(json.dumps({"files": []}), encoding="utf-8")
            music.write_bytes(b"fake")
            profile.write_text(json.dumps({
                "render_profile": "light_effects",
                "effects_enabled": True,
            }), encoding="utf-8")

            def fake_mv_chain(script, material_db_arg, out_path, music_path=None, mat_dir="/tmp", verbose=True, **kwargs):
                Path(out_path).write_bytes(b"mp4")
                (Path(out_path).parent / "state.json").write_text(json.dumps({}), encoding="utf-8")
                return {"final": out_path, "plan": []}

            def fake_music_structure(audio_path, out_path, **_kwargs):
                Path(out_path).write_text(json.dumps({"source_audio": str(audio_path)}), encoding="utf-8")
                return {"ok": True, "structure": {"sections": []}}

            with patch("video_pipeline_core.mv_cut.mv_chain", fake_mv_chain), \
                 patch("video_pipeline_core.music_structure.write_music_structure", fake_music_structure):
                result = ca.run_contract(
                    contract,
                    material_db=material_db,
                    out_path=outdir / "final.mp4",
                    music_path=music,
                    mat_dir=outdir,
                    verbose=False,
                    build_profile_config_path=profile,
                )

            manifest = json.loads((outdir / "artifact_manifest.json").read_text(encoding="utf-8"))
            plan = json.loads((outdir / "light_effects_plan.json").read_text(encoding="utf-8"))
            self.assertTrue(result["render_ok"])
            self.assertEqual(manifest["light_effects_plan"], str(outdir / "light_effects_plan.json"))
            self.assertEqual(manifest["light_effects_manifest"], str(outdir / "light_effects_manifest.json"))
            self.assertIn("grade", [item["operation"] for item in plan["items"]])

    def test_run_contract_stock_first_writes_route_and_stock_payload(self):
        contract = {
            "style": "mv",
            "material_source_mode": "stock_first",
            "story_truth_level": "conceptual",
            "segments": [self._seg(
                core={"section_role": "montage", "story_purpose": "城市工作流程",
                      "timeline_source": "beat"},
                material_fit={"visual_desc": "城市清晨工作車", "search_query": "city morning work truck",
                              "fallback_policy": "stock_bridge", "reason": "概念情緒段"},
            ), self._seg(segment=2), self._seg(segment=3)],
        }
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            material_db = Path(d) / "material_db.json"
            music = Path(d) / "bgm.mp3"
            material_db.write_text(json.dumps({"files": []}), encoding="utf-8")
            music.write_bytes(b"fake")

            def fake_mv_chain(script, material_db_arg, out_path, music_path=None, mat_dir="/tmp", verbose=True, **kwargs):
                Path(out_path).write_bytes(b"mp4")
                (Path(out_path).parent / "state.json").write_text(json.dumps({}), encoding="utf-8")
                return {"final": out_path, "plan": []}

            def fake_music_structure(audio_path, out_path, **_kwargs):
                Path(out_path).write_text(json.dumps({"source_audio": str(audio_path)}), encoding="utf-8")
                return {"ok": True, "structure": {"sections": []}}

            with patch("video_pipeline_core.mv_cut.mv_chain", fake_mv_chain), \
                 patch("video_pipeline_core.music_structure.write_music_structure", fake_music_structure):
                result = ca.run_contract(
                    contract,
                    material_db=material_db,
                    out_path=outdir / "final.mp4",
                    music_path=music,
                    mat_dir=outdir,
                    verbose=False,
                )

            manifest = json.loads((outdir / "artifact_manifest.json").read_text(encoding="utf-8"))
            payload = json.loads((outdir / "generated_mv_script.json").read_text(encoding="utf-8"))
            route = json.loads((outdir / "stock_first_route.json").read_text(encoding="utf-8"))
            self.assertTrue(result["render_ok"])
            self.assertEqual(manifest["stock_first_route"], str(outdir / "stock_first_route.json"))
            self.assertEqual(payload["segments"][0]["source"], "stock")
            self.assertEqual(payload["segments"][0]["search_query"], "city morning work truck")
            self.assertEqual(route["segments"][0]["selected_route"], "stock_bridge")

    def test_run_contract_writes_build_profile_and_generated_requests(self):
        contract = {
            "style": "mv",
            "segments": [self._seg(
                core={"section_role": "montage", "story_purpose": "抽象流程",
                      "timeline_source": "beat"},
                material_fit={"visual_desc": "乾淨工作空間中的團隊協作",
                              "fallback_policy": "generated", "reason": "概念補圖"},
            ), self._seg(segment=2)],
        }
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            material_db = Path(d) / "material_db.json"
            music = Path(d) / "bgm.mp3"
            profile = Path(d) / "profile.json"
            material_db.write_text(json.dumps({"files": []}), encoding="utf-8")
            music.write_bytes(b"fake")
            profile.write_text(json.dumps({
                "fallback_visual_provider": "antigravity",
                "provider_priority": ["antigravity", "assistant_imagegen"],
            }), encoding="utf-8")

            def fake_mv_chain(script, material_db_arg, out_path, music_path=None, mat_dir="/tmp", verbose=True, **kwargs):
                Path(out_path).write_bytes(b"mp4")
                (Path(out_path).parent / "state.json").write_text(json.dumps({}), encoding="utf-8")
                return {"final": out_path, "plan": []}

            def fake_music_structure(audio_path, out_path, **_kwargs):
                Path(out_path).write_text(json.dumps({"source_audio": str(audio_path)}), encoding="utf-8")
                return {"ok": True, "structure": {"sections": []}}

            with patch("video_pipeline_core.mv_cut.mv_chain", fake_mv_chain), \
                 patch("video_pipeline_core.music_structure.write_music_structure", fake_music_structure):
                result = ca.run_contract(
                    contract,
                    material_db=material_db,
                    out_path=outdir / "final.mp4",
                    music_path=music,
                    mat_dir=outdir,
                    verbose=False,
                    build_profile_config_path=profile,
                )

            manifest = json.loads((outdir / "artifact_manifest.json").read_text(encoding="utf-8"))
            build_profile = json.loads((outdir / "build_profile.json").read_text(encoding="utf-8"))
            requests = json.loads((outdir / "generated_asset_requests.json").read_text(encoding="utf-8"))
            self.assertTrue(result["render_ok"])
            self.assertEqual(manifest["build_profile"], str(outdir / "build_profile.json"))
            self.assertEqual(manifest["generated_asset_requests"], str(outdir / "generated_asset_requests.json"))
            self.assertEqual(build_profile["fallback_visual_provider"], "antigravity")
            self.assertEqual(requests["provider_priority"][0], "antigravity")
            self.assertEqual(requests["items"][0]["segment"], 1)

    def test_run_contract_failsafe_on_verification_failure(self):
        contract = {
            "style": "mv",
            "segments": [self._seg(segment=1), self._seg(segment=2)],
        }
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            material_db = Path(d) / "material_db.json"
            music = Path(d) / "bgm.mp3"
            material_db.write_text(json.dumps({"files": []}), encoding="utf-8")
            music.write_bytes(b"fake")

            def fake_mv_chain(script, material_db_arg, out_path, music_path=None, mat_dir="/tmp", verbose=True, **kwargs):
                Path(out_path).write_bytes(b"mp4")
                (Path(out_path).parent / "state.json").write_text(json.dumps({
                    "pass": True,
                    "next_action": "complete_review_final",
                    "segments": [{"segment": 1, "visual_desc": "test"}]
                }), encoding="utf-8")
                return {"final": out_path, "plan": [{"segment": 1, "source": out_path, "extract_dur": 1.0}]}

            def fake_music_structure(audio_path, out_path, **_kwargs):
                Path(out_path).write_text(json.dumps({"source_audio": str(audio_path)}), encoding="utf-8")
                return {"ok": True, "structure": {"sections": []}}

            with patch("video_pipeline_core.mv_cut.mv_chain", fake_mv_chain), \
                 patch("video_pipeline_core.music_structure.write_music_structure", fake_music_structure):
                result = ca.run_contract(
                    contract,
                    material_db=material_db,
                    out_path=outdir / "final.mp4",
                    music_path=music,
                    mat_dir=outdir,
                    verbose=False,
                )

            self.assertFalse(result["ok"])
            self.assertFalse(result["workflow_ok"])
            self.assertTrue(result["render_ok"])
            self.assertFalse(result["verify_ok"])
            self.assertEqual(result["next_action"], "verify_failed")

            state_data = json.loads((outdir / "state.json").read_text(encoding="utf-8"))
            self.assertFalse(state_data["pass"])
            self.assertEqual(state_data["next_action"], "verify_failed")


class DryBuildTest(unittest.TestCase):
    """Render-free dry build: materialize Node 8/9/10/11 BUILD artifacts offline
    so the SPEC->REVIEW chain can be validated with no material/ffmpeg/network."""

    CONTRACT = EXAMPLES / "genre_tests" / "stock_story_e2e" / "segment_contract.json"
    CATEGORIES = EXAMPLES / "genre_tests" / "stock_story_e2e" / "material_categories.json"

    def test_dry_build_materializes_chain_offline(self):
        with tempfile.TemporaryDirectory() as td:
            outdir = Path(td)
            result = ca.dry_build(
                self.CONTRACT, out_dir=outdir,
                categories_path=str(self.CATEGORIES), verbose=False)
            self.assertTrue(result["ok"])
            self.assertTrue(result["dry_run"])

            # The three previously render-only BUILD artifacts now exist offline.
            for name in ("build_profile.json", "assembly_plan.json", "timeline_build.json",
                         "editor_review.json", "generated_mv_script.json", "dry_build.json",
                         "spec_review.json"):
                self.assertTrue((outdir / name).exists(), f"{name} not written")

            # No render / verify side effects.
            self.assertFalse((outdir / "final.mp4").exists())
            self.assertFalse((outdir / "verify_result.json").exists())

            # Timeline clips carry traces (verify_timeline gate would pass).
            tl = json.loads((outdir / "timeline_build.json").read_text(encoding="utf-8"))
            self.assertEqual(len(tl["clips"]), 6)
            for clip in tl["clips"]:
                self.assertTrue(clip.get("trace"))
                self.assertEqual(clip.get("provider"), "dry")

    def test_dry_build_chain_walk_reaches_build_nodes(self):
        from video_pipeline_core import dashboard_state
        with tempfile.TemporaryDirectory() as td:
            outdir = Path(td)
            ca.dry_build(self.CONTRACT, out_dir=outdir,
                         categories_path=str(self.CATEGORIES), verbose=False)
            state = dashboard_state.load_dashboard_state(str(outdir))
            status = {str(n["node"]): n["status"] for n in state["nodes"]}
            for node in ("0", "3", "2", "8", "9", "10", "11"):
                self.assertEqual(status.get(node), "done",
                                 f"Node {node} not done: {status.get(node)}")
            # Render/verify remain unmaterialized (only a real render produces them).
            self.assertEqual(status.get("13"), "missing")


if __name__ == "__main__":
    unittest.main()
