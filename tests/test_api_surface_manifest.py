import json
import subprocess
import sys
import unittest
from pathlib import Path
from tools.api_surface_manifest import API_ENDPOINTS, audit_api_surface


class TestApiSurfaceManifest(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.registry_path = self.project_root / "docs" / "branch-contract-registry.json"

    def test_manifest_structure(self):
        self.assertIsInstance(API_ENDPOINTS, list)
        self.assertTrue(len(API_ENDPOINTS) > 0)
        
        required_keys = {"method", "path", "owner_branch", "mode", "allowed_writes", "forbidden_writes", "response_shape", "next_action", "source"}
        for idx, endpoint in enumerate(API_ENDPOINTS):
            self.assertIsInstance(endpoint, dict)
            for key in required_keys:
                self.assertIn(key, endpoint, f"Endpoint index {idx} ({endpoint.get('path')}) missing key: {key}")

    def test_audit_api_surface_passes(self):
        errors = audit_api_surface(API_ENDPOINTS, self.registry_path)
        self.assertEqual(errors, [], f"API Surface Manifest audit failed with errors: {errors}")

    def test_promote_endpoint_constraints(self):
        promote = next((ep for ep in API_ENDPOINTS if ep["path"] == "/api/control/promote"), None)
        self.assertIsNotNone(promote)
        self.assertEqual(promote["method"], "POST")
        self.assertEqual(promote["owner_branch"], "workbench-brownfield")
        self.assertEqual(promote["mode"], "request_only")
        self.assertEqual(promote["allowed_writes"], ["workbench_promotion_request.json"])
        
        for file in ("timeline.json", "segment_contract.json", "final.mp4"):
            self.assertIn(file, promote["forbidden_writes"])

    def test_workbench_patch_constraints(self):
        patch = next((ep for ep in API_ENDPOINTS if ep["path"] == "/api/workbench/patch"), None)
        self.assertIsNotNone(patch)
        self.assertEqual(patch["method"], "POST")
        self.assertEqual(patch["owner_branch"], "workbench-brownfield")
        self.assertEqual(patch["mode"], "draft_write")
        self.assertNotEqual(patch["mode"], "canonical_write")
        
        for file in ("timeline.json", "segment_contract.json", "final.mp4"):
            self.assertIn(file, patch["forbidden_writes"])

    def test_manifest_covers_known_dashboard_and_workbench_api_routes(self):
        known_routes = {
            ("GET", "/api/control/status"),
            ("GET", "/api/control/workbench-health"),
            ("GET", "/api/workbench/thumbnails"),
            ("GET", "/api/workbench/proxies"),
        }
        manifest_routes = {(ep["method"], ep["path"]) for ep in API_ENDPOINTS}
        self.assertTrue(known_routes.issubset(manifest_routes))

    def test_derived_cache_endpoints_are_not_read_only_or_canonical(self):
        by_path = {ep["path"]: ep for ep in API_ENDPOINTS}
        for path, expected_write in {
            "/api/workbench/thumbnails": "workbench_thumbs/",
            "/api/workbench/proxies": "workbench_proxy/",
        }.items():
            endpoint = by_path[path]
            self.assertEqual(endpoint["mode"], "derived_cache_write")
            self.assertIn(expected_write, endpoint["allowed_writes"])
            self.assertNotEqual(endpoint["mode"], "canonical_write")
            for file in ("timeline.json", "segment_contract.json", "final.mp4"):
                self.assertIn(file, endpoint["forbidden_writes"])

    def test_all_branches_exist_in_registry(self):
        with open(self.registry_path, "r", encoding="utf-8") as f:
            registry_data = json.load(f)
        valid_branch_ids = {b["branch_id"] for b in registry_data.get("branches", []) if "branch_id" in b}
        
        for ep in API_ENDPOINTS:
            self.assertIn(ep["owner_branch"], valid_branch_ids, f"Endpoint {ep['method']} {ep['path']} has invalid owner_branch: {ep['owner_branch']}")

    def test_cli_json_flag(self):
        script_path = self.project_root / "tools" / "api_surface_manifest.py"
        res = subprocess.run(
            [sys.executable, str(script_path), "--json"],
            capture_output=True,
            text=True,
            check=True
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), len(API_ENDPOINTS))


if __name__ == "__main__":
    unittest.main()
