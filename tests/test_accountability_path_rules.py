import hashlib
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from video_pipeline_core.capability_execution import (
    canonical_json_bytes,
    hash_file,
    normalize_repo_path,
    path_matches_rule,
    validate_execution_contract,
)


class CanonicalJsonAndPathRulesTest(unittest.TestCase):
    def test_canonical_json_is_sorted_utf8_compact_and_lf_terminated(self):
        payload = {"z": "\u4e2d\u6587", "a": {"b": 2, "a": 1}}

        self.assertEqual(
            b'{"a":{"a":1,"b":2},"z":"\xe4\xb8\xad\xe6\x96\x87"}\n',
            canonical_json_bytes(payload),
        )

    def test_canonical_json_excludes_only_the_declared_self_hash_field(self):
        payload = {"nested": {"sha256": "keep"}, "sha256": "discard", "value": 1}

        self.assertEqual(
            b'{"nested":{"sha256":"keep"},"value":1}\n',
            canonical_json_bytes(payload, self_hash_field="sha256"),
        )

    def test_hash_file_is_stable_sha256(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.json"
            path.write_bytes(b"accountable bytes\n")

            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), hash_file(path))

    def test_normalize_repo_path_preserves_posix_spelling(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "docs" / "work-order.md"
            target.parent.mkdir()
            target.write_text("fixture", encoding="utf-8")

            self.assertEqual("docs/work-order.md", normalize_repo_path(root, "docs/work-order.md"))

    def test_normalize_repo_path_rejects_nonportable_and_escaping_paths(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for raw in ("", "/absolute", "C:/drive", "\\\\server\\share", "a\\b", "a//b", "a/../b"):
                with self.subTest(raw=raw):
                    with self.assertRaises(ValueError):
                        normalize_repo_path(root, raw)

    def test_normalize_repo_path_rejects_case_collision(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "Owner" / "artifact.json"
            target.parent.mkdir()
            target.write_text("fixture", encoding="utf-8")

            with self.assertRaises(ValueError):
                normalize_repo_path(root, "owner/artifact.json")

    def test_normalize_repo_path_rejects_symlink_escape(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            outside = Path(tmp) / "outside"
            root.mkdir()
            outside.mkdir()
            (outside / "secret.json").write_text("secret", encoding="utf-8")
            link = root / "link"
            try:
                os.symlink(outside, link, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is not available")

            with self.assertRaises(ValueError):
                normalize_repo_path(root, "link/secret.json")

    def test_owner_rule_matches_exact_and_directory_prefix_but_not_siblings(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertTrue(path_matches_rule(root, "run/output.json", {"path": "run/output.json", "match": "exact"}))
            self.assertFalse(path_matches_rule(root, "run/output.json.bak", {"path": "run/output.json", "match": "exact"}))
            self.assertTrue(path_matches_rule(root, "run/assets/frame.png", {"path": "run/assets", "match": "directory_prefix"}))
            self.assertFalse(path_matches_rule(root, "run/assets-old/frame.png", {"path": "run/assets", "match": "directory_prefix"}))

    def test_deleted_tombstone_remains_valid_changed_path_evidence(self):
        contract = _contract()
        contract["initial_owner_zone_manifest"] = [{"path": "run/old.json", "sha256": None, "state": "deleted"}]

        errors = validate_execution_contract(Path.cwd(), contract, _catalog())

        self.assertEqual([], errors)


def _catalog():
    return {
        "ok": True,
        "cards": [{
            "capability_id": "cap.example.operation.v1",
            "command": "tools/example.py --run .tmp/accountability-run",
            "execution_class": "deterministic",
            "capability_role": "operation",
        }],
    }


def _contract():
    return {
        "artifact_role": "work_order_execution_contract",
        "version": 1,
        "accountability_contract_version": 1,
        "work_order_id": "path-rules",
        "work_order_path": "docs/construction-guides/work-orders/path-rules.md",
        "work_order_sha256": "a" * 64,
        "run_root": ".tmp/accountability-run",
        "accountability_root": ".tmp/accountability-run/accountability",
        "initial_run_root_manifest": [],
        "initial_owner_zone_manifest": [],
        "steps": [{
            "step_id": "L1.example",
            "loop": "L1",
            "capability_id": "cap.example.operation.v1",
            "depends_on": [],
            "command_argv": ["{python}", "tools/example.py", "--run", ".tmp/accountability-run"],
            "timeout_ms": 1000,
            "inputs": [],
            "required_outputs": [".tmp/accountability-run/output.json"],
            "required_verifier_step_ids": [],
            "max_attempts": 1,
            "allowed_retry_failure_classes": [],
        }],
        "decision_requirements": [],
        "allowed_owner_zones": [{"path": ".tmp/accountability-run", "match": "directory_prefix"}],
        "forbidden_paths": [],
        "protected_paths": [],
        "human_creative_approval": False,
        "final_delivery_claimed": False,
    }


if __name__ == "__main__":
    unittest.main()
