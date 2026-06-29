import json
import tempfile
import unittest
from pathlib import Path
from video_pipeline_core.dashboard_state import load_dashboard_state

class DashboardStateSpecTest(unittest.TestCase):
    def test_stale_spec_review_state_does_not_override_current_passing_spec_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "brief.json").write_text(json.dumps({"title": "T"}), encoding="utf-8")
            (workdir / "segment_contract.json").write_text(
                json.dumps({"segments": [{"segment": 1, "source": "local"}]}),
                encoding="utf-8",
            )
            (workdir / "spec_review.json").write_text(json.dumps({
                "artifact_role": "spec_review",
                "ready_for_build": True,
                "blocking": [],
                "next_action": None,
            }), encoding="utf-8")
            (workdir / "state.json").write_text(json.dumps({
                "pass": False,
                "next_action": "revise:director(spec_review)",
                "blocking": [{
                    "rule": "script_overreach",
                    "segment": 1,
                    "reason": "stale",
                }],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertNotEqual(state["run"]["next_action"], "revise:director(spec_review)")
            self.assertFalse(any(
                "script_overreach" in (finding.get("message") or "")
                for finding in state["findings"]
            ))

    def test_invalid_timeline_build_json_blocks_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "brief.json").write_text(json.dumps({"title": "T"}), encoding="utf-8")
            (workdir / "segment_contract.json").write_text(
                json.dumps({"segments": [{"segment": 1, "source": "local"}]}),
                encoding="utf-8",
            )
            (workdir / "timeline_build.json").write_text(
                '{"clips":[{"segment":1,"source_path":"C:\\bad\\_clip.mp4"}]}',
                encoding="utf-8",
            )
            (workdir / "verify_result.json").write_text(
                json.dumps({"pass": True}), encoding="utf-8"
            )
            (workdir / "final.mp4").write_bytes(b"placeholder")

            state = load_dashboard_state(str(workdir))

            self.assertEqual(state["run"]["next_action"], "fix_timeline_or_assembly")
            self.assertTrue(any(
                finding.get("artifact") == "timeline_build"
                and finding.get("type") == "error"
                for finding in state["findings"]
            ))

    def test_control_surface_is_artifact_first_and_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "build_profile.json").write_text(json.dumps({
                "render_profile": "motion_graphics",
                "fallback_visual_provider": "assistant_imagegen",
                "motion_graphics_backend": "ffmpeg_libass",
                "effects_enabled": True,
            }), encoding="utf-8")
            (workdir / "generated_asset_requests.json").write_text(json.dumps({
                "items": [{"segment": 1, "provider": "assistant_imagegen", "prompt": "city"}],
            }), encoding="utf-8")
            (workdir / "motion_graphics_render_plan.json").write_text(
                json.dumps({"items": []}), encoding="utf-8"
            )

            state = load_dashboard_state(str(workdir))
            controls = state["controls"]

            self.assertTrue(controls["read_only"])
            self.assertEqual(controls["profile"]["render_profile"], "motion_graphics")
            self.assertEqual(controls["generated_assets"]["requested"], 1)
            self.assertEqual(controls["generated_assets"]["status"], "waiting")
            self.assertEqual(controls["route"]["next_action"], "wait_for_generated_provider")
            effects = next(n for n in state["nodes"] if n["node"] == 14)
            self.assertTrue(any(link["role"] == "motion_graphics_render_plan" for link in effects["artifact_links"]))
            self.assertTrue(all(Path(link["path"]).is_absolute() for link in effects["artifact_links"]))

    def test_light_effects_baseline_gaps_surface_under_revision_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "build_profile.json").write_text(json.dumps({
                "render_profile": "light_effects",
                "effects_enabled": True,
            }), encoding="utf-8")
            (workdir / "light_effects_baseline_review.json").write_text(json.dumps({
                "artifact_role": "light_effects_baseline_review",
                "status": "gaps_found",
                "metrics": {"planned_count": 3, "rendered_count": 0, "gap_count": 3},
                "gaps": [{"effect_id": "seg1_title_card_1", "reason": "no_render_output"}],
                "next_action": "implement_or_wire_effect_recipe",
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))
            revision = next(n for n in state["nodes"] if n["node"] == 14)

            self.assertEqual(revision["status"], "warn")
            self.assertIn("3 light-effects render gap", revision["reason"])
            self.assertTrue(any(
                link["role"] == "light_effects_baseline_review"
                for link in revision["artifact_links"]
            ))

    def test_effect_revision_request_surfaces_under_revision_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "build_profile.json").write_text(json.dumps({
                "render_profile": "light_effects",
                "effects_enabled": True,
            }), encoding="utf-8")
            (workdir / "light_effects_baseline_review.json").write_text(json.dumps({
                "artifact_role": "light_effects_baseline_review",
                "status": "gaps_found",
                "metrics": {"gap_count": 1},
                "gaps": [{"effect_id": "fxintent_2_external_effect_1"}],
            }), encoding="utf-8")
            (workdir / "effect_revision_request.json").write_text(json.dumps({
                "artifact_role": "effect_revision_request",
                "version": 1,
                "status": "pending",
                "summary": {"request_count": 1},
                "requests": [{
                    "request_id": "fxrev_fxintent_2_external_effect_1",
                    "effect_id": "fxintent_2_external_effect_1",
                    "route": "route_to_node14_or_remotion_adapter",
                    "status": "pending",
                }],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))
            revision = next(n for n in state["nodes"] if n["node"] == 14)

            self.assertEqual(revision["status"], "warn")
            self.assertIn("1 effect revision request", revision["reason"])
            self.assertTrue(any(
                link["role"] == "effect_revision_request"
                for link in revision["artifact_links"]
            ))

    def test_effect_recipe_patch_surfaces_under_revision_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "effect_revision_request.json").write_text(json.dumps({
                "artifact_role": "effect_revision_request",
                "version": 1,
                "status": "pending",
                "summary": {"request_count": 1},
                "requests": [],
            }), encoding="utf-8")
            (workdir / "effect_recipe_patch.json").write_text(json.dumps({
                "artifact_role": "effect_recipe_patch",
                "version": 1,
                "status": "pending",
                "summary": {"patch_count": 1},
                "patches": [],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))
            revision = next(n for n in state["nodes"] if n["node"] == 14)

            self.assertEqual(revision["status"], "warn")
            self.assertIn("1 effect recipe patch", revision["reason"])
            self.assertTrue(any(
                link["role"] == "effect_recipe_patch"
                for link in revision["artifact_links"]
            ))

    def test_manifest_based_state_includes_all_nodes(self):
        """1. Manifest-based dashboard state includes required nodes."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            
            # Write mock files
            manifest = {
                "brief": "brief.json",
                "canonical_contract": "segment_contract.json",
                "material_coverage_map": "material_coverage_map.json",
                "music_structure": "music_structure.json",
                "build_profile": "build_profile.json",
                "generated_asset_requests": "generated_asset_requests.json",
                "assembly_plan": "assembly_plan.json",
                "timeline_build": "timeline_build.json",
                "editor_review": "editor_review.json",
                "state": "state.json",
                "verify_result": "qa_report.json"
            }
            (workdir / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (workdir / "brief.json").write_text(json.dumps({"title": "Brief test"}), encoding="utf-8")
            (workdir / "segment_contract.json").write_text(json.dumps([{
                "segment": 1,
                "title": "Seg 1",
                "core": {"story_purpose": "open"},
                "material_fit": {"visual_desc": "city", "reason": "story opening needs city image"},
                "audio": {"role": "music", "reason": "music carries the montage"},
                "text_layer": {"subtitle": "hello", "reason": "subtitle anchors meaning"},
                "visual_style": {"layout": "hold", "reason": "hold keeps focus"},
                "editing_grammar": {"role": "hero", "reason": "opening hero shot"},
            }]), encoding="utf-8")
            (workdir / "material_coverage_map.json").write_text(json.dumps({"covered": [1]}), encoding="utf-8")
            (workdir / "music_structure.json").write_text(json.dumps({"bpm": 120}), encoding="utf-8")
            (workdir / "build_profile.json").write_text(json.dumps({"fallback_visual_provider": "pexels", "effects_enabled": False}), encoding="utf-8")
            (workdir / "generated_asset_requests.json").write_text(json.dumps([]), encoding="utf-8")
            (workdir / "assembly_plan.json").write_text(json.dumps([]), encoding="utf-8")
            (workdir / "timeline_build.json").write_text(json.dumps([]), encoding="utf-8")
            (workdir / "editor_review.json").write_text(json.dumps({"decision": "approve"}), encoding="utf-8")
            (workdir / "state.json").write_text(json.dumps({"pass": True}), encoding="utf-8")
            (workdir / "qa_report.json").write_text(json.dumps({"pass": True}), encoding="utf-8")

            state = load_dashboard_state(str(workdir))
            
            # Check nodes exist
            node_labels = [n["label"] for n in state["nodes"]]
            self.assertIn("Brief", node_labels)
            self.assertIn("Material Coverage", node_labels)
            self.assertIn("Contract", node_labels)
            self.assertIn("Contract Facets", node_labels)
            self.assertIn("Audio", node_labels)
            self.assertIn("Fallback/Profile", node_labels)
            self.assertIn("Assembly", node_labels)
            self.assertIn("Timeline", node_labels)
            self.assertIn("Editor Review", node_labels)
            self.assertIn("Verify", node_labels)
            self.assertIn("Render Candidate", node_labels)
            self.assertIn("Brownfield Edit", node_labels)

            # Assert states are done/optional/etc.
            nodes_by_label = {n["label"]: n for n in state["nodes"]}
            self.assertEqual(nodes_by_label["Brief"]["status"], "done")
            self.assertEqual(nodes_by_label["Material Coverage"]["status"], "done")
            self.assertEqual(nodes_by_label["Contract"]["status"], "done")
            self.assertEqual(nodes_by_label["Contract Facets"]["status"], "done")
            self.assertEqual(nodes_by_label["Audio"]["status"], "done")
            self.assertEqual(nodes_by_label["Fallback/Profile"]["status"], "done")
            self.assertEqual(nodes_by_label["Brownfield Edit"]["status"], "optional")

    def test_missing_optional_effects_does_not_fail_when_effects_disabled(self):
        """2. Missing optional effects artifact does not fail when effects_enabled=false."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            
            manifest = {
                "build_profile": "build_profile.json"
            }
            (workdir / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (workdir / "build_profile.json").write_text(json.dumps({"effects_enabled": False}), encoding="utf-8")

            state = load_dashboard_state(str(workdir))
            nodes_by_label = {n["label"]: n for n in state["nodes"]}
            self.assertEqual(nodes_by_label["Brownfield Edit"]["status"], "optional")

    def test_generated_requests_without_manifest_produces_warn_status(self):
        """3. Generated requests without generated manifest produce warn status on Fallback/Profile node."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            
            manifest = {
                "build_profile": "build_profile.json",
                "generated_asset_requests": "generated_asset_requests.json"
            }
            (workdir / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (workdir / "build_profile.json").write_text(json.dumps({"fallback_visual_provider": "pexels"}), encoding="utf-8")
            # Requests exist
            (workdir / "generated_asset_requests.json").write_text(json.dumps([{"segment": 1, "prompt": "test"}]), encoding="utf-8")

            state = load_dashboard_state(str(workdir))
            nodes_by_label = {n["label"]: n for n in state["nodes"]}
            self.assertEqual(nodes_by_label["Fallback/Profile"]["status"], "warn")
            self.assertEqual(nodes_by_label["Fallback/Profile"]["reason"], "wait_for_generated_provider")
            
            # Check warning in findings
            messages = [f["message"] for f in state["findings"]]
            self.assertIn("Generated requests exist but no generated manifest", messages)

    def test_generated_requests_object_items_without_manifest_produces_warn_status(self):
        """Generated request artifact uses the canonical object shape with items."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)

            manifest = {
                "build_profile": "build_profile.json",
                "generated_asset_requests": "generated_asset_requests.json",
            }
            (workdir / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (workdir / "build_profile.json").write_text(json.dumps({
                "fallback_visual_provider": "assistant_imagegen",
                "effects_enabled": False,
            }), encoding="utf-8")
            (workdir / "generated_asset_requests.json").write_text(json.dumps({
                "artifact_role": "generated_asset_requests",
                "generated_asset_requests_version": 1,
                "items": [{"segment": 1, "provider": "assistant_imagegen", "prompt": "clean workspace"}],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))
            nodes_by_label = {n["label"]: n for n in state["nodes"]}
            self.assertEqual(nodes_by_label["Fallback/Profile"]["status"], "warn")
            self.assertEqual(state["next_action"], "wait_for_generated_provider")
            self.assertIn("Generated requests exist but no generated manifest",
                          [f["message"] for f in state["findings"]])

    def test_visual_review_request_routes_to_single_agent_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "visual_review_request.json").write_text(json.dumps({
                "artifact_role": "visual_review_request",
                "next_action": "await_visual_review",
                "clips": [{"segment": 2, "montage": "visual_review/seg2.jpg"}],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

        self.assertEqual(state["next_action"], "await_visual_review")
        nodes_by_label = {node["label"]: node for node in state["nodes"]}
        self.assertEqual(nodes_by_label["Visual Judge"]["node"], "10.5")
        self.assertEqual(nodes_by_label["Visual Judge"]["status"], "warn")
        self.assertIn(
            "Visual review request awaits agent verdict",
            [finding["message"] for finding in state["findings"]],
        )

    def test_visual_judge_node_is_done_when_request_has_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "visual_review_request.json").write_text(json.dumps({
                "artifact_role": "visual_review_request",
                "clips": [{"segment": 2}],
            }), encoding="utf-8")
            (workdir / "visual_review_verdict.json").write_text(json.dumps({
                "artifact_role": "visual_review_verdict",
                "clips": [{"segment": 2, "accept": True}],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

        nodes_by_label = {node["label"]: node for node in state["nodes"]}
        self.assertEqual(nodes_by_label["Visual Judge"]["status"], "done")
        self.assertEqual(nodes_by_label["Visual Judge"]["reason"],
                         "Visual review verdict recorded")

    def test_generated_manifest_path_from_artifact_manifest_satisfies_node8(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)

            manifest = {
                "build_profile": "build_profile.json",
                "generated_asset_requests": "generated_asset_requests.json",
                "generated_asset_manifest": "build/generated_manifest.json",
            }
            (workdir / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (workdir / "build").mkdir()
            (workdir / "build_profile.json").write_text(json.dumps({
                "fallback_visual_provider": "assistant_imagegen",
                "effects_enabled": False,
            }), encoding="utf-8")
            (workdir / "generated_asset_requests.json").write_text(json.dumps({
                "items": [{"segment": 1, "provider": "assistant_imagegen", "prompt": "clean workspace"}],
            }), encoding="utf-8")
            (workdir / "build" / "generated_manifest.json").write_text(json.dumps({
                "items": [{"segment": 1, "file": "materials/generated/seg1.jpg"}],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))
            nodes_by_label = {n["label"]: n for n in state["nodes"]}
            self.assertEqual(nodes_by_label["Fallback/Profile"]["status"], "done")
            self.assertNotEqual(state["next_action"], "wait_for_generated_provider")

    def test_contract_facets_warn_when_reasons_are_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "segment_contract.json").write_text(json.dumps([{
                "segment": 1,
                "core": {"story_purpose": "open"},
                "material_fit": {"visual_desc": "city"},
                "audio": {"role": "music"},
                "text_layer": {"subtitle": "hello"},
                "visual_style": {"layout": "hold"},
                "editing_grammar": {"role": "hero"},
            }]), encoding="utf-8")

            state = load_dashboard_state(str(workdir))
            nodes_by_label = {n["label"]: n for n in state["nodes"]}
            self.assertEqual(nodes_by_label["Contract Facets"]["status"], "warn")
            self.assertIn("Facet reasons incomplete", nodes_by_label["Contract Facets"]["reason"])

    def test_comfyui_provider_in_profile_produces_blocked_finding(self):
        """4. ComfyUI provider in build profile produces blocked/deprecated finding."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            
            manifest = {
                "build_profile": "build_profile.json"
            }
            (workdir / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (workdir / "build_profile.json").write_text(json.dumps({"fallback_visual_provider": "comfyui"}), encoding="utf-8")

            state = load_dashboard_state(str(workdir))
            nodes_by_label = {n["label"]: n for n in state["nodes"]}
            self.assertEqual(nodes_by_label["Fallback/Profile"]["status"], "blocked")
            self.assertEqual(nodes_by_label["Fallback/Profile"]["reason"], "blocked/deprecated provider comfyui")

            # Check finding exists
            messages = [f["message"] for f in state["findings"]]
            self.assertIn("ComfyUI provider in build profile produces blocked/deprecated finding", messages)

    def test_text_layer_none_string_satisfies_facet_reason(self):
        """The string 'none' IS the explicit text_layer declaration (留白也是顯式
        設計) — it must not leave the facet gate stuck at warn forever."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            seg = {
                "segment": 1,
                "core": {"section_role": "develop"},
                "material_fit": {"visual_desc": "x", "reason": "r"},
                "audio": {"role": "music", "reason": "r"},
                "text_layer": "none",
                "visual_style": {"layout": "single", "pace": "hold", "reason": "r"},
                "editing_grammar": {"role": "filler", "reason": "r"},
            }
            (workdir / "segment_contract.json").write_text(
                json.dumps({"segments": [seg]}), encoding="utf-8")
            state = load_dashboard_state(str(workdir))
            facets = next(n for n in state["nodes"] if str(n["node"]) == "4-7")
            self.assertEqual(facets["status"], "done", facets["reason"])

    def test_soul_declared_without_editing_policy_produces_warning_finding(self):
        """Soul fields in the contract with an inactive editing_policy must surface
        a finding — the guards (visual_fatigue/editorial_qa) silently skip otherwise."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            contract = {"segments": [{
                "segment": 1,
                "core": {"section_role": "develop"},
                "editing_intent": {"content_pattern": "establishing"},
            }]}
            (workdir / "segment_contract.json").write_text(json.dumps(contract), encoding="utf-8")
            (workdir / "build_profile.json").write_text(json.dumps({"editing_policy": None}), encoding="utf-8")

            state = load_dashboard_state(str(workdir))
            messages = [f["message"] for f in state["findings"]]
            self.assertTrue(any("editing_policy is inactive" in m for m in messages), messages)

    def test_soul_with_active_editing_policy_has_no_inactive_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            contract = {"segments": [{
                "segment": 1,
                "core": {"section_role": "develop"},
                "editing_intent": {"content_pattern": "process"},
            }]}
            (workdir / "segment_contract.json").write_text(json.dumps(contract), encoding="utf-8")
            (workdir / "build_profile.json").write_text(
                json.dumps({"editing_policy": {"subtitle_strategy": {"placement": "bottom_safe"}}}),
                encoding="utf-8")

            state = load_dashboard_state(str(workdir))
            messages = [f["message"] for f in state["findings"]]
            self.assertFalse(any("editing_policy is inactive" in m for m in messages), messages)

    def test_no_soul_fields_no_editing_policy_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            contract = {"segments": [{"segment": 1, "core": {"section_role": "opening"}}]}
            (workdir / "segment_contract.json").write_text(json.dumps(contract), encoding="utf-8")

            state = load_dashboard_state(str(workdir))
            messages = [f["message"] for f in state["findings"]]
            self.assertFalse(any("editing_policy is inactive" in m for m in messages), messages)

    def test_existing_route_state_json_fallback_works(self):
        """5. Existing route state.json dashboard mode still works."""
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            # No artifact_manifest.json, just state.json
            state_json = {
                "schema_version": 1,
                "next_action": "await_material",
                "segments": [
                    {"segment": 1, "title": "Smoke test", "status": "blocked", "block_reason": "No material"}
                ]
            }
            (workdir / "state.json").write_text(json.dumps(state_json), encoding="utf-8")

            state = load_dashboard_state(str(workdir))
            self.assertEqual(state["next_action"], "await_material")
            self.assertEqual(len(state["segments"]), 1)
            self.assertEqual(state["segments"][0]["segment"], 1)
            self.assertEqual(state["segments"][0]["verify"]["status"], "blocked")

    def test_ready_material_delta_suppresses_stale_coverage_gap_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "material_coverage_map.json").write_text(json.dumps({
                "artifact_role": "material_coverage_map",
                "gaps": [{"segment": 1, "reason": "legacy gap"}],
            }), encoding="utf-8")
            (workdir / "material_delta.json").write_text(json.dumps({
                "artifact_role": "material_delta",
                "ok": True,
                "ready_for_build": True,
                "summary": {"covered": 1, "thin": 0, "missing": 0, "excess": 0},
            }), encoding="utf-8")
            (workdir / "material_map_lifecycle.json").write_text(json.dumps({
                "artifact_role": "material_map_lifecycle",
                "can_build": True,
                "next_action": "build",
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertFalse(any(
                f.get("artifact") == "material_coverage" and f.get("type") == "error"
                for f in state["findings"]
            ))

    def test_verified_final_with_ready_delta_overrides_stale_await_material_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "final.mp4").write_bytes(b"video")
            (workdir / "verify_result.json").write_text(json.dumps({
                "pass": True,
                "score": 92,
            }), encoding="utf-8")
            (workdir / "state.json").write_text(json.dumps({
                "pass": False,
                "next_action": "await_material",
            }), encoding="utf-8")
            (workdir / "material_coverage_map.json").write_text(json.dumps({
                "artifact_role": "material_coverage_map",
                "gaps": [{"segment": 1, "reason": "legacy gap"}],
            }), encoding="utf-8")
            (workdir / "material_delta.json").write_text(json.dumps({
                "artifact_role": "material_delta",
                "ok": True,
                "ready_for_build": True,
                "blocks_ready_for_build": False,
                "summary": {"covered": 0, "thin": 0, "missing": 0, "excess": 1},
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertTrue(state["run"]["pass"])
            self.assertEqual(state["run"]["next_action"], "complete_review_final")

    def test_verified_legacy_render_can_complete_without_canonical_build_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "final.mp4").write_bytes(b"video")
            (workdir / "verify_result.json").write_text(json.dumps({
                "pass": True,
                "score": 100,
                "issues": [],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertEqual(state["next_action"], "complete_review_final")

    def test_audit_artifacts_surface_under_node_11_and_12(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            manifest = {
                "timeline_build": "timeline_build.json",
                "editor_review": "editor_review.json",
                "timeline_invariants": "timeline_invariants.json",
                "broll_audit": "broll_audit.json",
                "visual_audit": "visual_audit.json",
                "presentation_feel_audit": "presentation_feel_audit.json",
            }
            (workdir / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (workdir / "timeline_build.json").write_text(json.dumps([]), encoding="utf-8")
            (workdir / "editor_review.json").write_text(json.dumps({"decision": "approve"}), encoding="utf-8")
            (workdir / "timeline_invariants.json").write_text(json.dumps({
                "artifact_role": "timeline_invariants", "version": 1, "pass": False,
                "checks": [{"name": "clip_trace_present", "status": "fail",
                            "affected_segments": [2], "details": "missing trace"}],
                "next_action": "fix_timeline_or_assembly",
            }), encoding="utf-8")
            (workdir / "broll_audit.json").write_text(json.dumps({
                "artifact_role": "broll_audit", "version": 1, "pass": True,
                "metrics": {"broll_ratio": 0.4, "unique_source_ratio": 1.0, "max_source_repeats": 1},
                "findings": [], "next_action": None,
            }), encoding="utf-8")
            (workdir / "visual_audit.json").write_text(json.dumps({
                "artifact_role": "visual_audit", "version": 1, "pass": True,
                "grid": "keyframe_grid.jpg", "samples": [{"timestamp_sec": 1.0, "cell": 1}],
                "mechanical_findings": [], "model_review": None, "next_action": None,
            }), encoding="utf-8")
            (workdir / "presentation_feel_audit.json").write_text(json.dumps({
                "artifact_role": "presentation_feel_audit", "version": 1, "pass": False,
                "score": 40,
                "findings": [{"check": "text_blocks_dominate", "level": "fail"}],
                "next_action": "fix_timeline_or_assembly",
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            # artifacts section indexes the audits
            self.assertFalse(state["artifacts"]["timeline_invariants"]["pass"])
            self.assertTrue(state["artifacts"]["visual_audit"]["pass"])

            nodes_by_label = {n["label"]: n for n in state["nodes"]}
            er = nodes_by_label["Editor Review"]
            roles_11 = {a["role"] for a in er.get("audits", [])}
            self.assertIn("timeline_invariants", roles_11)
            self.assertIn("broll_audit", roles_11)

            verify_node = nodes_by_label["Verify"]
            roles_12 = {a["role"] for a in verify_node.get("audits", [])}
            self.assertIn("visual_audit", roles_12)
            self.assertIn("presentation_feel_audit", roles_12)

            # failing audit surfaces a finding tagged to its node
            failing = [f for f in state["findings"]
                       if f.get("artifact") == "timeline_invariants"]
            self.assertTrue(failing)
            self.assertEqual(failing[0]["node"], 11)
            self.assertEqual(failing[0]["type"], "error")

    def test_failed_quality_audit_surfaces_as_nonblocking_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "final.mp4").write_bytes(b"video")
            (workdir / "verify_result.json").write_text(
                json.dumps({"pass": True}), encoding="utf-8")
            (workdir / "visual_fatigue_audit.json").write_text(json.dumps({
                "artifact_role": "visual_fatigue_audit",
                "pass": False,
                "next_action": "review_visual_diversity",
                "findings": [{"level": "fail"}],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            finding = next(
                f for f in state["findings"]
                if f.get("artifact") == "visual_fatigue_audit"
            )
            self.assertEqual(finding["type"], "warning")
            self.assertNotEqual(state["next_action"], "review_visual_diversity")
            self.assertFalse(any(
                f.get("type") == "error"
                and f.get("artifact") == "visual_fatigue_audit"
                for f in state["findings"]
            ))

    def test_no_audit_artifacts_keeps_nodes_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "editor_review.json").write_text(
                json.dumps({"decision": "approve"}), encoding="utf-8")
            state = load_dashboard_state(str(workdir))
            nodes_by_label = {n["label"]: n for n in state["nodes"]}
            # no audits present -> empty audits list, no audit findings
            self.assertEqual(nodes_by_label["Editor Review"].get("audits", []), [])
            self.assertEqual(
                [f for f in state["findings"] if "artifact" in f], [])

    def test_failed_broll_audit_prevents_complete_review_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "final.mp4").write_bytes(b"video")
            (workdir / "verify_result.json").write_text(
                json.dumps({"pass": True}), encoding="utf-8")
            (workdir / "broll_audit.json").write_text(json.dumps({
                "artifact_role": "broll_audit",
                "pass": False,
                "next_action": "curator",
                "findings": [{"level": "fail"}],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertEqual(state["next_action"], "curator")
            self.assertFalse(state["run"]["pass"])

    def test_failed_new_visual_information_audit_prevents_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "final.mp4").write_bytes(b"video")
            (workdir / "verify_result.json").write_text(
                json.dumps({"pass": True}), encoding="utf-8")
            (workdir / "new_visual_information_audit.json").write_text(json.dumps({
                "artifact_role": "new_visual_information_audit",
                "pass": False,
                "next_action": "curator",
                "findings": [{"level": "fail"}],
            }), encoding="utf-8")
            state = load_dashboard_state(str(workdir))
            self.assertEqual(state["next_action"], "curator")
            self.assertFalse(state["run"]["pass"])

    def test_rough_cut_plan_gap_surfaces_as_final_review_blocker(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "verify_result.json").write_text(
                json.dumps({"pass": True}), encoding="utf-8")
            (workdir / "rough_cut_plan.json").write_text(json.dumps({
                "artifact_role": "rough_cut_plan",
                "ok": False,
                "gaps": [{
                    "segment": 2,
                    "need_id": "nd_closing",
                    "reason": "no accepted scene satisfies the segment need",
                }],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertEqual(state["next_action"], "revise_material_selection_or_review")
            self.assertFalse(state["run"]["pass"])
            self.assertTrue(any(
                finding.get("artifact") == "rough_cut_plan"
                and finding.get("type") == "error"
                for finding in state["findings"]
            ))

    def test_timeline_material_contract_mismatch_surfaces_as_final_review_blocker(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "brief.json").write_text(
                json.dumps({"title": "material mismatch fixture"}), encoding="utf-8")
            (workdir / "verify_result.json").write_text(
                json.dumps({"pass": True}), encoding="utf-8")
            (workdir / "material_coverage_map.json").write_text(
                json.dumps({"coverage": []}), encoding="utf-8")
            (workdir / "segment_contract.json").write_text(json.dumps({
                "segments": [{
                    "segment": 2,
                    "material_map_ids": ["commute_001"],
                    "need_refs": ["need_commute_motion"],
                }],
            }), encoding="utf-8")
            (workdir / "project_material_map.json").write_text(json.dumps({
                "assets": [{
                    "asset_id": "city_dawn_001",
                    "scenes": [{
                        "scene_id": "city_dawn_001:0",
                        "satisfies": ["need_city_dawn"],
                    }],
                }],
            }), encoding="utf-8")
            (workdir / "timeline_build.json").write_text(json.dumps({
                "clips": [{
                    "segment": 2,
                    "scene_id": "city_dawn_001:0",
                    "source_path": "city_dawn.mp4",
                }],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertEqual(state["next_action"], "revise_material_selection_or_review")
            self.assertFalse(state["run"]["pass"])
            self.assertTrue(any(
                finding.get("artifact") == "timeline_build"
                and "city_dawn_001:0" in finding.get("message", "")
                for finding in state["findings"]
            ))

    def test_material_wall_handoff_report_surfaces_in_artifacts_and_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "material_wall_handoff_report.json").write_text(json.dumps({
                "artifact_role": "material_wall_handoff_report",
                "selected_asset_ids": ["real_0001", "real_0002"],
                "rejected_asset_ids": ["real_0003"],
                "duplicate_asset_ids": [],
                "need_coverage": {
                    "nd_opening": ["real_0001", "real_0002"],
                    "nd_training": [],
                    "nd_closing": [],
                },
                "missing_need_ids": ["nd_training", "nd_closing"],
                "duplicate_need_ids": ["nd_opening"],
                "ready_for_mapping": False,
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            report = state["artifacts"]["material_wall_handoff_report"]
            self.assertEqual(report["selected_asset_ids"], ["real_0001", "real_0002"])
            self.assertTrue(any(
                finding.get("artifact") == "material_wall_handoff_report"
                and "missing needs" in finding.get("message", "")
                for finding in state["findings"]
            ))

    def test_material_first_boundary_acceptance_report_surfaces_in_artifacts_and_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "material_first_boundary_acceptance_report.json").write_text(json.dumps({
                "artifact_role": "material_first_boundary_acceptance_report",
                "route": "material-first",
                "ok": False,
                "next_action": "repair:stage4_build",
                "failed_stage": "stage4_build",
                "stages": [
                    {"stage": "stage2_3_material_wall_to_review_apply", "ok": True},
                    {
                        "stage": "stage4_build",
                        "ok": False,
                        "blocking": [{"rule": "timeline_mismatch", "message": "timeline clip mismatch"}],
                    },
                ],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            report = state["artifacts"]["material_first_boundary_acceptance_report"]
            self.assertEqual(report["failed_stage"], "stage4_build")
            self.assertEqual(state["next_action"], "repair:stage4_build")
            self.assertFalse(state["run"]["pass"])
            self.assertTrue(any(
                finding.get("artifact") == "material_first_boundary_acceptance_report"
                and "timeline clip mismatch" in finding.get("message", "")
                for finding in state["findings"]
            ))

    def test_material_inventory_summary_surfaces_in_artifacts_and_next_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "video_intent.json").write_text(json.dumps({
                "artifact_role": "video_intent",
                "entry_path": "material-first",
                "material_scan_decision": {
                    "needed": True,
                    "default_scope": "all_materials",
                    "scan_depth": "quick_inventory_first",
                },
            }), encoding="utf-8")
            (workdir / "material_inventory_summary.json").write_text(json.dumps({
                "artifact_role": "material_inventory_summary",
                "ok": True,
                "counts": {"total_files": 12, "videos": 8, "images": 4},
                "recommended_next_actions": [
                    "review_material_inventory_summary",
                    "continue_to_material_map_deep_review",
                ],
                "suggested_followup_questions": ["要全量深篩，還是只看候選資料夾？"],
            }, ensure_ascii=False), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertEqual(state["artifacts"]["material_inventory_summary"]["counts"]["total_files"], 12)
            self.assertEqual(state["next_action"], "review_material_inventory_summary")
            self.assertFalse(state["run"]["pass"])
            self.assertTrue(any(
                finding.get("artifact") == "material_inventory_summary"
                and "12" in finding.get("message", "")
                for finding in state["findings"]
            ))

    def test_stage0_child_contracts_surface_for_dashboard_and_workbench(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "video_intent.json").write_text(json.dumps({
                "artifact_role": "video_intent",
                "entry_path": "material-first",
                "material_contract": {
                    "artifact_role": "stage0_material_intent",
                    "first_action": "material_map_quick_inventory",
                },
                "soundtrack_contract": {
                    "artifact_role": "stage0_soundtrack_intent",
                    "music_role": "mixed",
                    "handoff_to": "soundtrack-arranger",
                },
                "effect_policy": {
                    "artifact_role": "stage0_effect_policy",
                    "activation": "defer_to_brownfield_or_segment_review",
                    "handoff_to": "video-effect-factory_when_segment_requires_effect",
                },
                "subtitle_voiceover_contract": {
                    "artifact_role": "stage0_subtitle_voiceover_intent",
                    "language": "zh-TW",
                    "subtitle_required": True,
                    "voiceover_required": True,
                    "handoff_to": "subtitle-director+audio-director",
                },
                "communication_intent": {
                    "artifact_role": "stage0_communication_intent",
                    "original_audio_policy": "mixed",
                    "music_policy": "mixed",
                    "handoff_to": ["soundtrack_arranger", "audio_director"],
                },
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertEqual(state["artifacts"]["video_intent"]["entry_path"], "material-first")
            self.assertEqual(
                state["artifacts"]["stage0_contracts"]["material"]["first_action"],
                "material_map_quick_inventory",
            )
            self.assertEqual(
                state["artifacts"]["stage0_contracts"]["soundtrack"]["music_role"],
                "mixed",
            )
            self.assertEqual(
                state["artifacts"]["stage0_contracts"]["effect"]["activation"],
                "defer_to_brownfield_or_segment_review",
            )
            self.assertEqual(
                state["controls"]["stage0_contracts"]["soundtrack"]["handoff_to"],
                "soundtrack-arranger",
            )
            self.assertEqual(
                state["artifacts"]["stage0_contracts"]["subtitle_voiceover"]["language"],
                "zh-TW",
            )
            self.assertEqual(
                state["controls"]["stage0_contracts"]["subtitle_voiceover"]["handoff_to"],
                "subtitle-director+audio-director",
            )
            self.assertEqual(
                state["artifacts"]["stage0_contracts"]["communication"]["original_audio_policy"],
                "mixed",
            )
            self.assertEqual(
                state["controls"]["stage0_contracts"]["communication"]["handoff_to"],
                ["soundtrack_arranger", "audio_director"],
            )

    def test_dashboard_routes_material_pass_to_soundtrack_when_stage0_requests_music(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "material_first_boundary_acceptance_report.json").write_text(json.dumps({
                "artifact_role": "material_first_boundary_acceptance_report",
                "route": "material-first",
                "ok": True,
                "next_action": "ready_for_render_or_human_review",
                "stage0_contracts": {
                    "soundtrack": {
                        "artifact_role": "stage0_soundtrack_intent",
                        "status": "requested",
                        "music_role": "mixed",
                        "handoff_to": "soundtrack-arranger",
                    }
                },
                "stages": [
                    {"stage": "stage2_3_material_wall_to_review_apply", "ok": True},
                    {"stage": "stage4_build", "ok": True},
                    {"stage": "stage5_final_review", "ok": True},
                ],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertEqual(state["next_action"], "soundtrack-arrange")
            self.assertFalse(state["run"]["pass"])
            self.assertTrue(any(
                finding.get("artifact") == "stage0_soundtrack_intent"
                and "mixed" in finding.get("message", "")
                for finding in state["findings"]
            ))

    def test_remotion_material_first_memory_acceptance_report_surfaces_in_artifacts_and_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "remotion_material_first_memory_acceptance_report.json").write_text(json.dumps({
                "artifact_role": "remotion_material_first_memory_acceptance_report",
                "ok": False,
                "failed_stage": "effect_collage_refs",
                "next_action": "provide_material_wall_keyframes_or_reviewed_stills",
                "errors": ["no reviewed material refs available for MemoryPhotoWall"],
                "summary": {
                    "build_component": "MemoryPhotoWall",
                    "selected_ref_count": 0,
                },
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            report = state["artifacts"]["remotion_material_first_memory_acceptance_report"]
            self.assertEqual(report["failed_stage"], "effect_collage_refs")
            self.assertEqual(state["next_action"], "provide_material_wall_keyframes_or_reviewed_stills")
            self.assertFalse(state["run"]["pass"])
            self.assertTrue(any(
                finding.get("artifact") == "remotion_material_first_memory_acceptance_report"
                and "no reviewed material refs" in finding.get("message", "")
                for finding in state["findings"]
            ))

    def test_remotion_material_first_memory_acceptance_pass_sets_dashboard_next_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "remotion_material_first_memory_acceptance_report.json").write_text(json.dumps({
                "artifact_role": "remotion_material_first_memory_acceptance_report",
                "ok": True,
                "failed_stage": None,
                "next_action": "ready_for_human_effect_review_or_pipeline_promotion",
                "summary": {
                    "build_component": "MemoryPhotoWall",
                    "selected_ref_count": 3,
                },
            }), encoding="utf-8")
            (workdir / "remotion_effect_handoff.json").write_text(json.dumps({
                "artifact_role": "remotion_effect_handoff",
                "version": 1,
                "status": "ready_for_human_review",
                "accepted_assets": [{"job_id": "rm_fx_material_memory_wall_01"}],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertEqual(state["next_action"], "ready_for_human_effect_review_or_pipeline_promotion")
            self.assertFalse(state["run"]["pass"])
            self.assertEqual(
                state["artifacts"]["remotion_material_first_memory_acceptance_report"]["summary"]["build_component"],
                "MemoryPhotoWall",
            )
            self.assertEqual(
                state["artifacts"]["remotion_effect_handoff"]["status"],
                "ready_for_human_review",
            )

    def test_soundtrack_artifacts_surface_and_block_next_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "soundtrack_plan.json").write_text(json.dumps({
                "artifact_role": "soundtrack_plan",
                "sections": [{"section_id": "mv_climax", "music_role": "song"}],
            }), encoding="utf-8")
            (workdir / "music_source_candidates.json").write_text(json.dumps({
                "artifact_role": "music_source_candidates",
                "candidates": [{"candidate_id": "music_mv_climax", "source_type": "reference_only"}],
            }), encoding="utf-8")
            (workdir / "sound_license_manifest.json").write_text(json.dumps({
                "artifact_role": "sound_license_manifest",
                "delivery_allowed": False,
                "blocked_reasons": ["reference_only"],
            }), encoding="utf-8")
            (workdir / "audio_director_handoff.json").write_text(json.dumps({
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": False,
                "blocks": ["reference_only"],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertEqual(state["next_action"], "resolve_soundtrack_license_or_reference_only")
            self.assertFalse(state["run"]["pass"])
            self.assertEqual(
                state["artifacts"]["soundtrack_plan"]["sections"][0]["section_id"],
                "mv_climax",
            )
            self.assertEqual(
                state["artifacts"]["music_source_candidates"]["candidates"][0]["source_type"],
                "reference_only",
            )
            self.assertEqual(
                state["artifacts"]["audio_director_handoff"]["blocks"],
                ["reference_only"],
            )
            self.assertTrue(any(
                finding.get("artifact") == "audio_director_handoff"
                and "reference_only" in finding.get("message", "")
                for finding in state["findings"]
            ))

    def test_audio_handoff_acceptance_surfaces_in_artifacts_and_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "audio_handoff_acceptance.json").write_text(json.dumps({
                "artifact_role": "audio_handoff_acceptance",
                "ok": False,
                "blocking": [{"rule": "audio_file_missing", "message": "selected audio_file does not exist"}],
                "next_action": "repair_audio_handoff",
            }), encoding="utf-8")
            (workdir / "audio_mix_plan.json").write_text(json.dumps({
                "artifact_role": "audio_mix_plan",
                "ready_for_mix": False,
                "tracks": [],
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertEqual(state["next_action"], "repair_audio_handoff")
            self.assertFalse(state["run"]["pass"])
            self.assertFalse(state["artifacts"]["audio_handoff_acceptance"]["ok"])
            self.assertFalse(state["artifacts"]["audio_mix_plan"]["ready_for_mix"])
            self.assertTrue(any(
                finding.get("artifact") == "audio_handoff_acceptance"
                and "audio_file_missing" in finding.get("message", "")
                for finding in state["findings"]
            ))

    def test_audio_build_handoff_surfaces_in_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "audio_build_handoff.json").write_text(json.dumps({
                "artifact_role": "audio_build_handoff",
                "selected_audio": str(workdir / "final_audio.wav"),
                "selection_reason": "audio_ready_final_audio",
                "audio_ready": True,
            }), encoding="utf-8")
            (workdir / "state.json").write_text(json.dumps({
                "pass": False,
                "next_action": "mix_audio_from_audio_mix_plan",
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertEqual(
                state["artifacts"]["audio_build_handoff"]["selection_reason"],
                "audio_ready_final_audio",
            )

    def test_audio_build_handoff_prevents_audio_mix_backtracking(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "final_audio.wav").write_bytes(b"audio")
            (workdir / "audio_mix_plan.json").write_text(json.dumps({
                "artifact_role": "audio_mix_plan",
                "ready_for_mix": True,
                "tracks": [{"section_id": "mv"}],
            }), encoding="utf-8")
            (workdir / "audio_handoff_acceptance.json").write_text(json.dumps({
                "artifact_role": "audio_handoff_acceptance",
                "ok": True,
            }), encoding="utf-8")
            (workdir / "audio_build_handoff.json").write_text(json.dumps({
                "artifact_role": "audio_build_handoff",
                "selected_audio": str(workdir / "final_audio.wav"),
                "selection_reason": "audio_ready_final_audio",
                "audio_ready": True,
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertNotEqual(state["next_action"], "mix_audio_from_audio_mix_plan")

    def test_subtitle_voiceover_handoff_surfaces_in_artifacts_and_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "subtitle_voiceover_handoff_acceptance.json").write_text(json.dumps({
                "artifact_role": "subtitle_voiceover_handoff_acceptance",
                "ok": False,
                "blocking": [{"rule": "subtitles_missing", "message": "required subtitles.srt is missing"}],
                "next_action": "repair_subtitle_voiceover_handoff",
            }), encoding="utf-8")
            (workdir / "subtitle_voiceover_build_handoff.json").write_text(json.dumps({
                "artifact_role": "subtitle_voiceover_build_handoff",
                "subtitle_ready": False,
                "voiceover_ready": False,
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertEqual(state["next_action"], "repair_subtitle_voiceover_handoff")
            self.assertFalse(state["run"]["pass"])
            self.assertFalse(state["artifacts"]["subtitle_voiceover_handoff_acceptance"]["ok"])
            self.assertFalse(state["artifacts"]["subtitle_voiceover_build_handoff"]["subtitle_ready"])
            self.assertTrue(any(
                finding.get("artifact") == "subtitle_voiceover_handoff_acceptance"
                and "subtitles_missing" in finding.get("message", "")
                for finding in state["findings"]
            ))

    def test_selected_materials_folder_is_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            selected = workdir / "materials" / "selected"
            selected.mkdir(parents=True)
            (selected / "seg1_pick.mp4").write_bytes(b"video")

            state = load_dashboard_state(str(workdir))

            self.assertEqual(len(state["materials"]), 1)
            self.assertEqual(state["materials"][0]["category"], "selected_material")
            self.assertEqual(state["materials"][0]["segment"], 1)

    def test_delivery_gate_report_file_surfaces_as_dashboard_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "verify_result.json").write_text(
                json.dumps({"pass": True}), encoding="utf-8"
            )
            (workdir / "delivery_gate.json").write_text(json.dumps({
                "artifact_role": "delivery_gate",
                "version": 1,
                "pass": False,
                "blocking": [{
                    "rule": "timeline_need_ref_mismatch",
                    "artifact": "timeline_build",
                    "message": "timeline clip does not satisfy segment need_refs",
                    "next_action": "revise_material_selection_or_review",
                }],
                "next_action": "revise_material_selection_or_review",
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertIn("delivery_gate_report", state["artifacts"])
            self.assertEqual(
                state["artifacts"]["delivery_gate_report"]["blocking"][0]["rule"],
                "timeline_need_ref_mismatch",
            )
            self.assertFalse(state["artifacts"]["delivery_gate_report"]["pass"])

    def test_workbench_handoff_route_back_surfaces_as_dashboard_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "workbench_handoff.json").write_text(json.dumps({
                "artifact_role": "workbench_handoff",
                "version": 1,
                "artifacts": {"timeline_patch": "timeline_patch.json"},
                "route_back": [{
                    "owner": "material-map",
                    "artifact": "timeline_patch",
                    "reason": "timeline replacement changes material truth",
                    "next_action": "review_material_map_or_rough_cut_patch",
                }],
                "next_action": "review_workbench_route_back",
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertIn("workbench_handoff", state["artifacts"])
            self.assertEqual(
                state["artifacts"]["workbench_handoff"]["route_back"][0]["owner"],
                "material-map",
            )
            self.assertEqual(state["next_action"], "review_workbench_route_back")
            self.assertTrue(any(
                finding.get("artifact") == "workbench_handoff"
                and "material-map" in finding.get("message", "")
                for finding in state["findings"]
            ))

    def test_source_highlight_artifacts_surface_without_missing_brief_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "source_timeline_map.json").write_text(json.dumps({
                "artifact_role": "source_timeline_map",
                "windows": [{"window_id": "win_000"}],
            }), encoding="utf-8")
            (workdir / "highlight_selection_plan.json").write_text(json.dumps({
                "artifact_role": "highlight_selection_plan",
                "clips": [{"segment_id": "seg01_opening"}],
            }), encoding="utf-8")
            (workdir / "rough_cut_plan.json").write_text(json.dumps({
                "artifact_role": "rough_cut_plan",
                "route": "single_source_highlight",
                "clips": [{"segment_id": "seg01_opening"}],
            }), encoding="utf-8")
            (workdir / "highlight_cut_report.json").write_text(json.dumps({
                "artifact_role": "highlight_cut_report",
                "duration_sec": 70.0,
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertEqual(state["next_action"], "write_delivery_gate_report_or_review_highlight_candidate")
            self.assertIn("source_timeline_map", state["artifacts"])
            self.assertIn("highlight_selection_plan", state["artifacts"])

    def test_source_matrix_and_final_verify_bundle_surface_as_dashboard_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "source_material_matrix.json").write_text(json.dumps({
                "artifact_role": "source_material_matrix",
                "windows": [{"window_id": "win_000", "visual": {"keyframe": "frame.jpg"}}],
                "audio": {"soundtrack_probe_report": "source_soundtrack_probe_report.json"},
            }), encoding="utf-8")
            (workdir / "final_product_verify_bundle.json").write_text(json.dumps({
                "artifact_role": "final_product_verify_bundle",
                "pass": True,
                "visual": {"keyframe_grid": "keyframe_grid.jpg", "pass": True},
                "audio": {"soundtrack_probe_report": "soundtrack_probe_report.json", "pass": True},
            }), encoding="utf-8")

            state = load_dashboard_state(str(workdir))

            self.assertIn("source_material_matrix", state["artifacts"])
            self.assertIn("final_product_verify_bundle", state["artifacts"])
            self.assertEqual(
                state["artifacts"]["source_material_matrix"]["windows"][0]["window_id"],
                "win_000",
            )
            self.assertTrue(state["artifacts"]["final_product_verify_bundle"]["pass"])

if __name__ == "__main__":
    unittest.main()
