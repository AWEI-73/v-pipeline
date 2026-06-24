from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class EffectsRoadmapAlignmentDocsTest(unittest.TestCase):
    def test_roadmap_promotes_effects_to_active_next_phase(self):
        text = read("roadmap.md")
        for expected in [
            "Next Phase ??Effects / Brownfield Edit / Node14",
            "Status: active next development direction.",
            "FX0 Effects Status Cleanup",
            "FX1 Effect Asset Spec",
            "FX2 Effect Build Wiring",
            "FX3 Brownfield Edit / Node14 Revision Orchestration",
            "FX4 Remotion Prompt-Driven Adapter Boundary",
            "delivery stays ffmpeg / `contract-run`",
            "Remotion is installed and now has a bounded Brownfield/Node14 adapter",
            "remotion_prompt_pack.json",
            "remotion_worker_outputs.json",
            "remotion_worker_bridge.mjs",
            "remotion-composite-draft",
            "Brownfield Edit is described as revision/effects orchestration",
        ]:
            self.assertIn(expected, text)
        self.assertNotIn("- Node 14 advanced effects / Remotion-like final renderer.", text)

    def test_generated_material_statuses_are_current(self):
        text = read("roadmap.md")
        for expected in [
            "Status: implemented / accepted for provider-neutral generated-material fallback.",
            "Status: implemented / accepted for offline and provider-output material flow.",
            "Status: implemented / accepted for real image-provider handoff.",
            "Status: implemented / accepted for generated candidate promotion.",
        ]:
            self.assertIn(expected, text)
        self.assertNotIn("Status: in implementation / review.", text)

    def test_decision_and_index_record_effects_boundary(self):
        decision = read("docs/archive/decisions/2026-06-19-effects-node14-roadmap-alignment.md")
        index = read("docs/INDEX.md")
        for expected in [
            "Effect assets are not real-event evidence",
            "Brownfield Edit is the local revision/effects orchestration route",
            "Node14 remains a legacy implementation node inside Brownfield Edit",
            "Remotion may author prompt-driven effects inside Brownfield Edit",
            "remotion-prompt-pack",
            "remotion_worker_bridge.mjs",
            "remotion-worker-outputs",
            "remotion-composite-draft",
        ]:
            self.assertIn(expected, decision)
        self.assertIn("2026-06-19-effects-node14-roadmap-alignment.md", index)
        self.assertIn("brownfield-edit.md", index)

    def test_brownfield_edit_skill_defines_fast_route_boundaries(self):
        text = read("skills/brownfield-edit.md")
        for expected in [
            "Brownfield Edit Route",
            "do not rewrite the blueprint",
            "effect asset / sfx / overlay",
            "remotion-prompt-pack",
            "remotion_worker_bridge.mjs",
            "remotion-worker-outputs",
            "remotion-composite-draft",
            "story evidence material",
            "reviewed artifact",
            "second contract-run",
        ]:
            self.assertIn(expected, text)

    def test_effects_director_declares_node14_and_asset_boundaries(self):
        text = read("skills/effects-director.md")
        for expected in [
            "2026-06-19 Effects / Node14 Boundary",
            "canonical final render",
            "draft preview",
            "Brownfield/Node14",
            "prompt-driven effect backend",
            "effect assets",
            "effect_asset_spec.json",
            "effect_patch.json",
        ]:
            self.assertIn(expected, text)

    def test_remotion_worker_skill_documents_material_first_memory_boundary(self):
        text = read("skills/remotion-effect-worker.md")
        for expected in [
            "MemoryPhotoWall",
            "material_wall_request.json",
            "--wall-request",
            "remotion_material_first_memory_acceptance.py",
            "remotion_material_first_memory_acceptance_report.json",
            "effect_build_spec.material_refs",
            "material_wall_keyframe",
            "not final delivery",
            "Do not add `effect_story_planner.json`",
            "`effect_build_spec` inside existing `prompt_parameters`",
        ]:
            self.assertIn(expected, text)

    def test_start_here_and_index_link_remotion_material_first_acceptance(self):
        start = read("docs/START_HERE_VIDEO_PIPELINE.md")
        index = read("docs/INDEX.md")
        for text in (start, index):
            for expected in [
                "docs/construction-guides/remotion-effect-build-api-plan.md",
                "skills/remotion-effect-worker.md",
                "tools/remotion_material_first_memory_acceptance.py",
                "remotion_material_first_memory_acceptance_report.json",
                "not final delivery",
            ]:
                self.assertIn(expected, text)

    def test_remotion_construction_plan_keeps_effect_build_spec_as_v1_surface(self):
        text = read("docs/construction-guides/remotion-effect-build-api-plan.md")
        for expected in [
            "v1 control surface is `effect_build_spec` inside existing `prompt_parameters`",
            "`effect_story_planner.json` is a future optional extraction",
            "Do not add `effect_story_planner.json` to the current mainline artifact chain",
            "story_function",
            "pacing",
            "density",
            "reveal_mode",
            "camera_motion",
            "accent_light",
        ]:
            self.assertIn(expected, text)

    def test_remotion_prompt_parameter_contract_includes_memory_wall_build_spec(self):
        text = read("docs/remotion_prompt_parameter_contract.md")
        for expected in [
            "`MemoryPhotoWall`",
            "`effect_build_spec`",
            "`story_function`",
            "`pacing`",
            "`density`",
            "`reveal_mode`",
            "`camera_motion`",
            "`accent_light`",
            "material-first recap openings",
        ]:
            self.assertIn(expected, text)
        self.assertNotIn("This contract currently hardens two high-value effect classes only", text)


if __name__ == "__main__":
    unittest.main()
