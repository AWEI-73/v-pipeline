import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from tools.package_agent_only_release import (
    PackageError,
    package_release,
    validate_handoff_for_release,
)


ROOT = Path(__file__).resolve().parents[1]


class AgentOnlyReleaseTests(unittest.TestCase):
    def test_source_package_contains_release_surface_and_excludes_local_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "package"
            result = package_release(ROOT, output, include_untracked=True)
            manifest = json.loads((output / "release_manifest.json").read_text(encoding="utf-8"))
            included = {item["path"]: item for item in manifest["included_files"]}

            self.assertEqual(result["release_status"], "PRIVATE_AGENT_ONLY_TECHNICAL_PREVIEW_V1")
            self.assertEqual(manifest["license_status"], "owner_decision_pending")
            self.assertEqual(manifest["source_head"], result["source_head"])
            for required in [
                "RUNBOOK.md",
                "HANDOFF_CURRENT.md",
                "tools/preflight.py",
                "tools/package_agent_only_release.py",
                "tests/test_preflight.py",
                "tests/test_agent_only_release.py",
            ]:
                self.assertIn(required, included)

            forbidden_fragments = [
                ".git/",
                ".tmp/",
                "runs/",
                "reference repo/",
                "archive/",
                "docs/archive/",
            ]
            for rel in included:
                normalized = rel.replace("\\", "/")
                self.assertFalse(any(fragment in normalized for fragment in forbidden_fragments), rel)
                name = normalized.rsplit("/", 1)[-1]
                self.assertNotEqual(name, ".env", rel)
                if name.startswith(".env."):
                    self.assertEqual(name, ".env.example", rel)
                self.assertFalse(normalized.lower().endswith((
                    ".mp4", ".mov", ".mkv", ".avi", ".wav", ".mp3", ".m4a", ".webm",
                )), rel)

            source_text = str(ROOT.resolve()).replace("/", "\\")
            for path in output.rglob("*"):
                if path.is_file() and path.name != "release_manifest.json":
                    try:
                        text = path.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        continue
                    self.assertNotIn(source_text, text, path)

            for rel, item in included.items():
                actual = output / rel
                self.assertTrue(actual.is_file(), rel)
                digest = hashlib.sha256(actual.read_bytes()).hexdigest()
                self.assertEqual(item["sha256"], digest, rel)

            handoff = json.loads(
                "{" + (output / "HANDOFF_CURRENT.md").read_text(encoding="utf-8").split("{", 1)[1].split("}", 1)[0] + "}"
            )
            self.assertEqual(handoff["state"], "IDLE")

    def test_optional_zip_is_deterministic_and_matches_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "package"
            zip_path = root / "package.zip"
            package_release(ROOT, output, zip_output=zip_path, include_untracked=True)

            with ZipFile(zip_path) as archive:
                names = archive.namelist()
                self.assertEqual(names, sorted(names))
                self.assertEqual(set(names), {
                    path.relative_to(output).as_posix()
                    for path in output.rglob("*")
                    if path.is_file()
                })

    def test_active_handoff_that_depends_on_excluded_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "HANDOFF_CURRENT.md").write_text(
                "<!-- HANDOFF_STATE_START -->\n"
                '{"artifact_role":"current_handoff_state","version":1,"updated_at":"2026-07-21T00:00:00+08:00",'
                '"state":"ACTIVE","active_work_order":null,"active_spec":null,"active_skill":null,'
                '"active_run_root":".tmp/run","authoritative_state_artifact":".tmp/run/state.json",'
                '"authoritative_state_sha256":"x","authoritative_state_field":"state",'
                '"campaign_status_artifact":".tmp/run/campaign.json","campaign_status_field":"state",'
                '"next_actions":[],"do_not_do":[],"human_creative_approval":false,'
                '"final_delivery_claimed":false,"review_packet":null}\n'
                "<!-- HANDOFF_STATE_END -->\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(PackageError, "excluded artifact"):
                validate_handoff_for_release(root)

    def test_non_empty_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "package"
            output.mkdir()
            (output / "keep.txt").write_text("keep\n", encoding="utf-8")

            with self.assertRaisesRegex(PackageError, "non-empty"):
                package_release(ROOT, output, include_untracked=True)


if __name__ == "__main__":
    unittest.main()
