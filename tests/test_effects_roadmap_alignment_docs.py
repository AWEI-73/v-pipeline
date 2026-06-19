from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class EffectsRoadmapAlignmentDocsTest(unittest.TestCase):
    def test_roadmap_promotes_effects_to_active_next_phase(self):
        text = read("roadmap.md")
        for expected in [
            "Next Phase — Effects / Brownfield Edit / Node14",
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
        decision = read("docs/decisions/2026-06-19-effects-node14-roadmap-alignment.md")
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
            "Workbench 只做 draft preview",
            "Remotion 是 Brownfield/Node14 的 prompt-driven effect backend",
            "effect assets 不等於事件素材",
            "effect_asset_spec.json",
            "effect_patch.json",
        ]:
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
