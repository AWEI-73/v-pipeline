import json
import tempfile
import unittest
from pathlib import Path
from video_pipeline_core.dashboard_state import load_dashboard_state

class DashboardStateSpecTest(unittest.TestCase):
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
            self.assertIn("Revision", node_labels)

            # Assert states are done/optional/etc.
            nodes_by_label = {n["label"]: n for n in state["nodes"]}
            self.assertEqual(nodes_by_label["Brief"]["status"], "done")
            self.assertEqual(nodes_by_label["Material Coverage"]["status"], "done")
            self.assertEqual(nodes_by_label["Contract"]["status"], "done")
            self.assertEqual(nodes_by_label["Contract Facets"]["status"], "done")
            self.assertEqual(nodes_by_label["Audio"]["status"], "done")
            self.assertEqual(nodes_by_label["Fallback/Profile"]["status"], "done")
            self.assertEqual(nodes_by_label["Revision"]["status"], "optional")

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
            self.assertEqual(nodes_by_label["Revision"]["status"], "optional")

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
        self.assertIn(
            "Visual review request awaits agent verdict",
            [finding["message"] for finding in state["findings"]],
        )

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

if __name__ == "__main__":
    unittest.main()
