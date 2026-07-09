"""Guard: the graduation product-route harness must compose registered branches.

The harness (video_pipeline_core/graduation_product_route_runner.py) tags every
stage it records with an ``owner`` branch and calls that branch's owner tools.
This guard fails if the harness ever names a stage owner that is not a real
branch in the decision-tree registry, so the hardcoded stage list cannot
silently drift from docs/branch-contract-registry.json.

(A full registry-driven harness that derives the stage order from the registry
is a separate, larger change; this test locks the composition contract in the
meantime.)
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "video_pipeline_core" / "graduation_product_route_runner.py"
REGISTRY = ROOT / "docs" / "branch-contract-registry.json"


class GraduationRouteRegistryConsistencyTest(unittest.TestCase):
    def _branch_ids(self) -> set[str]:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        return {branch["branch_id"] for branch in registry["branches"]}

    def _harness_owners(self) -> set[str]:
        source = RUNNER.read_text(encoding="utf-8")
        return set(re.findall(r'owner\s*=\s*"([^"]+)"', source))

    def test_harness_stage_owners_are_registered_branches(self):
        owners = self._harness_owners()
        self.assertTrue(owners, "expected the harness to declare stage owners")
        unregistered = sorted(owners - self._branch_ids())
        self.assertEqual(
            unregistered,
            [],
            f"harness stages owned by branches missing from the registry: {unregistered}",
        )


if __name__ == "__main__":
    unittest.main()
