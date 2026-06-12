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

    def test_creative_exception_reaches_runtime_and_dry_render_plan(self):
        exception = {
            "rule_bent": "hold_discipline",
            "reason": "Hold for the reveal.",
            "risk": "The shot may feel slow.",
            "requires_review": True,
        }
        script = ca.contract_to_mv_script({
            "segments": [self._seg(segment=7, creative_exception=exception)]
        })

        self.assertEqual(script["segments"][0]["creative_exception"], exception)
        self.assertEqual(ca._synth_render_plan(script)[0]["creative_exception"], exception)

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
            self.assertEqual(draft["audio_track"][0]["source_path"], str(music))
            self.assertEqual(draft["audio_track"][0]["role"], "bgm")
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
            self.assertEqual(captured.get("visual_judge"), "agent")

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
                    "presentation_feel_audit": True,
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
            for role in ("timeline_invariants", "broll_audit", "caption_audit",
                         "presentation_feel_audit"):
                self.assertTrue((outdir / f"{role}.json").exists(), f"{role}.json missing")
                self.assertEqual(manifest[role], str(outdir / f"{role}.json"))
            # ffmpeg-dependent tools were left disabled -> still null
            self.assertIsNone(manifest["keyframe_grid"])
            self.assertIsNone(manifest["visual_audit"])
            audit = json.loads((outdir / "timeline_invariants.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["artifact_role"], "timeline_invariants")
            self.assertTrue((outdir / "editor_review.json").exists())
            self.assertTrue((outdir / "model_routes.json").exists())

    def test_presentation_feel_audit_does_not_require_caption_audit(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d)
            assembly = outdir / "assembly_plan.json"
            timeline = outdir / "timeline_build.json"
            assembly.write_text(json.dumps({"segments": []}), encoding="utf-8")
            timeline.write_text(json.dumps({"clips": []}), encoding="utf-8")

            written = ca._write_p1_audits(
                outdir,
                {"verification_tools": {"presentation_feel_audit": True}},
                timeline_build_path=timeline,
                verbose=False,
            )

            self.assertTrue((outdir / "presentation_feel_audit.json").exists())
            self.assertEqual(
                written["presentation_feel_audit"],
                str(outdir / "presentation_feel_audit.json"),
            )

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
                return {"final": out_path, "plan": [{
                    "segment": 1,
                    "is_photo": True,
                    "kenburns": True,
                    "slot_index": 0,
                }]}

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
            self.assertEqual(
                manifest["light_effects_baseline_review"],
                str(outdir / "light_effects_baseline_review.json"),
            )
            baseline = json.loads(
                (outdir / "light_effects_baseline_review.json").read_text(encoding="utf-8")
            )
            effects_manifest = json.loads(
                (outdir / "light_effects_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(baseline["status"], "gaps_found")
            self.assertGreater(baseline["metrics"]["planned_count"], 0)
            self.assertIn("grade", [item["operation"] for item in plan["items"]])
            self.assertIn("kenburns", [
                item["operation"] for item in effects_manifest["render_outputs"]
            ])

    def test_run_contract_writes_motion_graphics_outputs_when_profile_enabled(self):
        contract = {
            "style": "mv",
            "segments": [self._seg(
                segment=1,
                text_layer={"label": "Opening", "reason": "chapter marker"},
            ), self._seg(segment=2), self._seg(segment=3)],
        }
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            material_db = Path(d) / "material_db.json"
            music = Path(d) / "bgm.mp3"
            profile = Path(d) / "profile.json"
            material_db.write_text(json.dumps({"files": []}), encoding="utf-8")
            music.write_bytes(b"fake")
            profile.write_text(json.dumps({
                "render_profile": "motion_graphics",
                "effects_enabled": True,
                "motion_graphics_backend": "ffmpeg_libass",
            }), encoding="utf-8")

            def fake_mv_chain(script, material_db_arg, out_path, music_path=None, mat_dir="/tmp", verbose=True, **kwargs):
                Path(out_path).write_bytes(b"mp4")
                (Path(out_path).parent / "state.json").write_text(json.dumps({}), encoding="utf-8")
                return {"final": out_path, "plan": [{
                    "segment": 1, "source": "a.mp4", "extract_start": 0,
                    "extract_dur": 3, "slot_index": 0, "slot_dur": 3,
                    "text": "Opening",
                }]}

            def fake_music_structure(audio_path, out_path, **_kwargs):
                Path(out_path).write_text(json.dumps({"source_audio": str(audio_path)}), encoding="utf-8")
                return {"ok": True, "structure": {"sections": []}}

            with patch("video_pipeline_core.mv_cut.mv_chain", fake_mv_chain), \
                 patch("video_pipeline_core.music_structure.write_music_structure", fake_music_structure):
                ca.run_contract(
                    contract,
                    material_db=material_db,
                    out_path=outdir / "final.mp4",
                    music_path=music,
                    mat_dir=outdir,
                    verbose=False,
                    build_profile_config_path=profile,
                )

            manifest = json.loads((outdir / "artifact_manifest.json").read_text(encoding="utf-8"))
            mg_manifest = json.loads((outdir / "motion_graphics_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["motion_graphics_contract"], str(outdir / "motion_graphics_contract.json"))
            self.assertEqual(manifest["motion_graphics_render_plan"], str(outdir / "motion_graphics_render_plan.json"))
            self.assertEqual(manifest["motion_graphics_manifest"], str(outdir / "motion_graphics_manifest.json"))
            self.assertEqual(mg_manifest["render_outputs"][0]["status"], "asset_ready")
            self.assertEqual(mg_manifest["composite_result"]["status"], "failed")
            self.assertTrue(Path(mg_manifest["render_outputs"][0]["path"]).exists())

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


class TimelineCaptionEntriesTest(unittest.TestCase):
    def test_excludes_labels_and_name_supers_from_subtitles(self):
        clips = [
            {
                "timeline_in_sec": 0.0,
                "timeline_out_sec": 2.0,
                "text_overlay": {"narrative": "read me"},
            },
            {
                "timeline_in_sec": 1.5,
                "timeline_out_sec": 3.0,
                "text_overlay": {"label": "decoration"},
            },
            {
                "timeline_in_sec": 3.0,
                "timeline_out_sec": 4.0,
                "text_overlay": {"name_super": "speaker"},
            },
        ]

        entries = ca._timeline_caption_entries(clips)

        self.assertEqual(entries, [{"t_in": 0.0, "t_out": 2.0, "text": "read me"}])


class AttentionBudgetRuntimeTest(unittest.TestCase):
    def test_attaches_node9_attention_budget_to_runtime_segments(self):
        payload = {
            "segments": [{
                "segment": 1,
                "raw_audio": {"role": "music", "intensity": "high"},
            }],
        }
        policy = {"default_mode": "rhythmic_mv"}

        ca._attach_attention_budgets(payload, music_structure=None, editing_policy=policy)

        budget = payload["segments"][0]["attention_budget"]
        self.assertEqual(budget["owner"], "music")
        self.assertEqual(budget["shot_sec"], [0.8, 2.0])

    def test_attaches_node9_anti_presentation_plan_to_runtime_segments(self):
        payload = {"style": "mv", "segments": [{
            "segment": 1,
            "media_pref": "photo",
            "narrative": "Explain this",
            "raw_text_layer": {"placement": "center"},
        }]}
        policy = {
            "default_mode": "warm_documentary",
            "max_still_hold_sec_by_mode": {"warm_documentary": 7.0},
        }

        ca._attach_attention_budgets(
            payload,
            music_structure={"beats": [0.0, 18.0]},
            editing_policy=policy,
        )

        anti = payload["segments"][0]["anti_presentation_plan"]
        self.assertEqual(anti["min_shots"], 3)
        self.assertEqual(payload["segments"][0]["text_placement"], "lower_third")


class ContractToNarrativeScriptTest(unittest.TestCase):
    def _seg(self, **over):
        base = {
            "segment": 1,
            "core": {
                "section_role": "opening",
                "story_purpose": "Introduce the idea",
                "timeline_source": "tts",
            },
            "material_fit": {
                "visual_desc": "A quiet city waking at sunrise",
                "material_hint": "city sunrise",
                "search_query": "quiet city sunrise",
                "media": "photo",
                "reason": "Establish the setting",
            },
            "audio": {"role": "duck", "voiceover_policy": "tts", "reason": "Narration leads"},
            "visual_style": {
                "layout": "single",
                "pace": "hold",
                "transition": "dissolve",
                "color_grade": "warm",
                "reason": "Calm opening",
            },
            "text_layer": {"label": "Morning", "subtitle": "from_voiceover", "reason": "Anchor topic"},
            "narration": {"text": "The city wakes before the first cup is poured.", "mode": "voiceover"},
        }
        base.update(over)
        return base

    def test_maps_canonical_facets_to_narrative_runtime_fields(self):
        script = ca.contract_to_narrative_script({"style": "narrative", "segments": [self._seg()]})
        seg = script["segments"][0]

        self.assertEqual(script["style"], "narrative")
        self.assertEqual(seg["text"], "The city wakes before the first cup is poured.")
        self.assertEqual(seg["title"], "Morning")
        self.assertEqual(seg["media_pref"], "photo")
        self.assertEqual(seg["search_query"], "quiet city sunrise")
        self.assertEqual(seg["visual_desc"], "A quiet city waking at sunrise")
        self.assertEqual(seg["effects"]["transition"], "dissolve")
        self.assertEqual(seg["effects"]["grade"], "warm")
        self.assertNotIn("hold", seg)
        self.assertNotIn("weight", seg)

    def test_preserves_trace_and_raw_facets(self):
        source_seg = self._seg(segment=7)
        seg = ca.contract_to_narrative_script({"segments": [source_seg]})["segments"][0]

        self.assertEqual(seg["_from_contract"], 7)
        self.assertEqual(seg["raw_narration"], source_seg["narration"])
        self.assertEqual(seg["raw_audio"], source_seg["audio"])
        self.assertEqual(seg["material_fit"], source_seg["material_fit"])
        self.assertEqual(seg["visual_style"], source_seg["visual_style"])
        self.assertEqual(seg["text_layer"], source_seg["text_layer"])

    def test_falls_back_to_text_layer_narrative_and_local_source(self):
        seg = self._seg(
            narration=None,
            source="local",
            file="materials/seg1.mp4",
            material_fit={"visual_desc": "Local interview", "reason": "Required interview"},
            text_layer={"narrative": "A direct account.", "reason": "Spoken line"},
        )
        out = ca.contract_to_narrative_script({"segments": [seg]})["segments"][0]

        self.assertEqual(out["text"], "A direct account.")
        self.assertEqual(out["source"], "local")
        self.assertEqual(out["file"], "materials/seg1.mp4")
        self.assertEqual(out["media_pref"], "video")

    def test_adapt_narrative_contract_file_writes_traceable_payload(self):
        with tempfile.TemporaryDirectory() as d:
            contract_path = Path(d) / "segment_contract.json"
            out_path = Path(d) / "generated_narrative_script.json"
            contract_path.write_text(
                json.dumps({"style": "narrative", "segments": [self._seg()]}),
                encoding="utf-8",
            )

            result = ca.adapt_narrative_contract_file(contract_path, out_path=out_path)
            payload = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(payload["_artifact_role"], "legacy_runtime_payload")
        self.assertEqual(payload["_adapter"], "contract_adapter.py")
        self.assertEqual(payload["_generated_from"], str(contract_path))
        self.assertTrue(payload["_contract_hash"].startswith("sha256:"))
        self.assertEqual(payload["segments"][0]["text"], "The city wakes before the first cup is poured.")


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
