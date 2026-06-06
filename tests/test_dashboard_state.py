import json
import tempfile
import unittest
from pathlib import Path
from video_pipeline_core.dashboard_state import load_dashboard_state

class DashboardStateSpecTest(unittest.TestCase):
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
            self.assertIn("Render", node_labels)
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
