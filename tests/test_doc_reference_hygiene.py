import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class DocReferenceHygieneTest(unittest.TestCase):
    def test_unreferenced_canonical_root_doc_is_reported(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_doc_reference_hygiene

        result = evaluate_doc_reference_hygiene(
            repo_root=Path.cwd(),
            root_docs=["docs/new-canonical-route-fact.md"],
            reference_texts=["docs/INDEX.md mentions something else"],
            exemptions=[],
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["orphan_canonical_docs"], ["docs/new-canonical-route-fact.md"])

    def test_current_root_docs_are_classified(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_current_doc_reference_hygiene

        result = evaluate_current_doc_reference_hygiene(Path.cwd())

        self.assertTrue(result["ok"], result)
        self.assertGreater(result["classified_count"], 0)
        self.assertIn("docs/INDEX.md", result["referenced_docs"])

    def test_cli_runs_directly_from_tools_path(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "doc_reference_hygiene.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/doc_reference_hygiene.py",
                    "--repo-root",
                    ".",
                    "--out",
                    str(out),
                    "--json",
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(out.exists())


class EntryContractBehaviorTest(unittest.TestCase):
    VALID_HANDOFF_JSON = """{
  "artifact_role": "current_handoff_state",
  "version": 1,
  "updated_at": "2026-07-13T00:00:00+08:00",
  "state": "ACTIVE",
  "active_work_order": "docs/construction-guides/work-orders/fixture.md",
  "active_spec": null,
  "active_skill": null,
  "active_run_root": ".tmp/fixture",
  "authoritative_state_artifact": ".tmp/fixture/state.json",
  "authoritative_state_field": "state",
  "next_actions": ["continue_fixture"],
  "do_not_do": ["claim_delivery"],
  "human_creative_approval": false,
  "final_delivery_claimed": false
}"""

    def _write(self, root: Path, rel: str, text: str) -> None:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _handoff_block(self, payload: str | None = None) -> str:
        body = self.VALID_HANDOFF_JSON if payload is None else payload
        return f"<!-- HANDOFF_STATE_START -->\n{body}\n<!-- HANDOFF_STATE_END -->\n"

    def _entry_fixture(
        self,
        *,
        agents: str | None = None,
        runbook: str | None = None,
        handoff: str | None = None,
        start_here: str | None = None,
        index: str | None = None,
        state_payload: dict[str, object] | None = None,
        write_state_artifact: bool = True,
    ) -> Path:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)

        agents = agents if agents is not None else "<!-- OPERATIONAL_ENTRY_POINTER: RUNBOOK.md -->\n"
        runbook = runbook if runbook is not None else (
            "<!-- OPERATIONAL_ENTRY: RUNBOOK -->\n"
            "<!-- CURRENT_HANDOFF_POINTER: HANDOFF_CURRENT.md -->\n"
            "# Runbook\n"
        )
        handoff = handoff if handoff is not None else (
            "<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->\n" + self._handoff_block()
        )
        start_here = start_here if start_here is not None else (
            "<!-- DOCUMENT_ROLE: ORIENTATION -->\n"
            "# Start Here\n"
            "Historical link: docs/construction-guides/work-orders/fixture.md\n"
        )
        index = index if index is not None else (
            "<!-- DOCUMENT_ROLE: MAP -->\n"
            "# Index\n"
            "docs/START_HERE_VIDEO_PIPELINE.md\n"
            "Historical link: docs/construction-guides/work-orders/fixture.md\n"
        )

        self._write(root, "AGENTS.md", agents)
        self._write(root, "RUNBOOK.md", runbook)
        self._write(root, "HANDOFF_CURRENT.md", handoff)
        self._write(root, "docs/START_HERE_VIDEO_PIPELINE.md", start_here)
        self._write(root, "docs/INDEX.md", index)
        self._write(root, "docs/construction-guides/work-orders/fixture.md", "# fixture\n")
        if write_state_artifact:
            if state_payload is None:
                state_payload = {"state": "ACTIVE"}
            self._write(
                root,
                ".tmp/fixture/state.json",
                json.dumps(state_payload, ensure_ascii=False, indent=2) + "\n",
            )
        return root

    def test_entry_contract_accepts_valid_exact_markers_and_handoff_block(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        root = self._entry_fixture()
        report = evaluate_entry_contract(root)

        self.assertTrue(report["ok"], report)
        self.assertEqual([], report["errors"])
        self.assertEqual("ACTIVE", report["handoff"]["state"])

    def test_entry_contract_rejects_missing_runbook_marker(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        root = self._entry_fixture(runbook="# Runbook\n")
        report = evaluate_entry_contract(root)

        self.assertIn("entry_marker_missing:RUNBOOK.md:OPERATIONAL_ENTRY", report["errors"])

    def test_entry_contract_rejects_duplicate_marker(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        root = self._entry_fixture(
            runbook=(
                "<!-- OPERATIONAL_ENTRY: RUNBOOK -->\n"
                "<!-- OPERATIONAL_ENTRY: RUNBOOK -->\n"
                "<!-- CURRENT_HANDOFF_POINTER: HANDOFF_CURRENT.md -->\n"
            )
        )
        report = evaluate_entry_contract(root)

        self.assertIn("entry_marker_duplicate:RUNBOOK.md:OPERATIONAL_ENTRY", report["errors"])

    def test_entry_contract_rejects_marker_on_wrong_surface(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        root = self._entry_fixture(index="<!-- OPERATIONAL_ENTRY: RUNBOOK -->\n")
        report = evaluate_entry_contract(root)

        self.assertIn("entry_marker_wrong_surface:docs/INDEX.md:OPERATIONAL_ENTRY", report["errors"])

    def test_entry_contract_rejects_wrong_marker_value(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        root = self._entry_fixture(
            runbook=(
                "<!-- OPERATIONAL_ENTRY: RUNBOOK -->\n"
                "<!-- CURRENT_HANDOFF_POINTER: docs/HANDOFF_CURRENT.md -->\n"
            )
        )
        report = evaluate_entry_contract(root)

        self.assertIn("entry_marker_wrong_value:RUNBOOK.md:CURRENT_HANDOFF_POINTER", report["errors"])

    def test_entry_contract_does_not_infer_authority_from_prose(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        root = self._entry_fixture(
            start_here=(
                "# Start Here\n"
                "This is the operational entry for the whole repo.\n"
                "Historical link: docs/construction-guides/work-orders/fixture.md\n"
            )
        )
        report = evaluate_entry_contract(root)

        self.assertIn(
            "entry_marker_missing:docs/START_HERE_VIDEO_PIPELINE.md:DOCUMENT_ROLE",
            report["errors"],
        )

    def test_entry_contract_rejects_missing_handoff_block(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        root = self._entry_fixture(handoff="<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->\n# Handoff\n")
        report = evaluate_entry_contract(root)

        self.assertIn("handoff_block_missing", report["errors"])

    def test_entry_contract_rejects_duplicate_handoff_block(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        root = self._entry_fixture(
            handoff=(
                "<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->\n"
                + self._handoff_block()
                + self._handoff_block()
            )
        )
        report = evaluate_entry_contract(root)

        self.assertIn("handoff_block_duplicate", report["errors"])

    def test_entry_contract_rejects_malformed_handoff_json(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        root = self._entry_fixture(
            handoff=(
                "<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->\n"
                + self._handoff_block('{"artifact_role": "current_handoff_state",}')
            )
        )
        report = evaluate_entry_contract(root)

        self.assertIn("handoff_json_invalid", report["errors"])

    def test_entry_contract_rejects_unknown_handoff_key(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        payload = json.loads(self.VALID_HANDOFF_JSON)
        payload["unexpected_key"] = True
        root = self._entry_fixture(
            handoff=(
                "<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->\n"
                + self._handoff_block(json.dumps(payload, ensure_ascii=False, indent=2))
            )
        )
        report = evaluate_entry_contract(root)

        self.assertIn("handoff_unknown_key:unexpected_key", report["errors"])

    def test_entry_contract_rejects_missing_handoff_path(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        payload = json.loads(self.VALID_HANDOFF_JSON)
        payload["active_work_order"] = "docs/construction-guides/work-orders/missing.md"
        root = self._entry_fixture(
            handoff=(
                "<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->\n"
                + self._handoff_block(json.dumps(payload, ensure_ascii=False, indent=2))
            )
        )
        report = evaluate_entry_contract(root)

        self.assertIn("handoff_path_missing:active_work_order", report["errors"])

    def test_entry_contract_rejects_active_handoff_path_outside_repo_root(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        with TemporaryDirectory() as external_tmp:
            external_path = Path(external_tmp) / "external-work-order.md"
            external_path.write_text("# external\n", encoding="utf-8")

            payload = json.loads(self.VALID_HANDOFF_JSON)
            payload["active_work_order"] = str(external_path)
            root = self._entry_fixture(
                handoff=(
                    "<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->\n"
                    + self._handoff_block(json.dumps(payload, ensure_ascii=False, indent=2))
                )
            )
            report = evaluate_entry_contract(root)

        self.assertIn("handoff_path_missing:active_work_order", report["errors"])

    def test_entry_contract_rejects_idle_handoff_with_active_fields(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        payload = json.loads(self.VALID_HANDOFF_JSON)
        payload["state"] = "IDLE"
        root = self._entry_fixture(
            handoff=(
                "<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->\n"
                + self._handoff_block(json.dumps(payload, ensure_ascii=False, indent=2))
            )
        )
        report = evaluate_entry_contract(root)

        self.assertIn("handoff_idle_has_active_fields", report["errors"])

    def test_entry_contract_rejects_active_handoff_without_authoritative_state_pointer(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        payload = json.loads(self.VALID_HANDOFF_JSON)
        payload["authoritative_state_artifact"] = None
        payload["authoritative_state_field"] = None
        root = self._entry_fixture(
            handoff=(
                "<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->\n"
                + self._handoff_block(json.dumps(payload, ensure_ascii=False, indent=2))
            )
        )
        report = evaluate_entry_contract(root)

        self.assertIn("handoff_state_authority_missing", report["errors"])

    def test_entry_contract_rejects_active_handoff_with_missing_authoritative_state_artifact(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        root = self._entry_fixture(write_state_artifact=False)
        report = evaluate_entry_contract(root)

        self.assertIn("handoff_state_authority_missing", report["errors"])

    def test_entry_contract_rejects_active_handoff_when_authoritative_state_field_is_absent(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        root = self._entry_fixture(state_payload={})
        report = evaluate_entry_contract(root)

        self.assertIn("handoff_state_authority_missing", report["errors"])

    def test_entry_contract_rejects_state_mismatch_against_authoritative_json(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_entry_contract

        root = self._entry_fixture(state_payload={"state": "WAITING_OWNER_REVIEW"})
        report = evaluate_entry_contract(root)

        self.assertIn("handoff_state_mismatch", report["errors"])

    def test_current_doc_reference_hygiene_includes_entry_contract_results(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_current_doc_reference_hygiene

        root = self._entry_fixture(runbook="# Runbook\n")
        report = evaluate_current_doc_reference_hygiene(root)

        self.assertIn("entry_contract", report)
        self.assertFalse(report["ok"])
        self.assertIn(
            "entry_marker_missing:RUNBOOK.md:OPERATIONAL_ENTRY",
            report["entry_contract"]["errors"],
        )


if __name__ == "__main__":
    unittest.main()
