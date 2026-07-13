import unittest

from video_pipeline_core import skill_tool_contract


class AccountabilityRetirementUnitTest(unittest.TestCase):
    def _validate(self, pre_ids, post_ids, rows):
        validator = getattr(skill_tool_contract, "validate_retirement_delta", None)
        if validator is None:
            self.fail("validate_retirement_delta is missing from video_pipeline_core.skill_tool_contract")
        return validator(set(pre_ids), set(post_ids), list(rows))

    def _row(
        self,
        candidate_id,
        *,
        surface_type="capability",
        paths=None,
        outcome="keep",
        replacement=None,
        live_consumer=None,
        legacy_reader=None,
        approved_by=None,
    ):
        return {
            "candidate_id": candidate_id,
            "surface_type": surface_type,
            "paths": list(paths or ["skills/x.md"]),
            "outcome": outcome,
            "replacement": replacement,
            "live_consumer": live_consumer or {"status": "PASS", "refs": ["rg:no references"]},
            "legacy_reader": legacy_reader or {"status": "PASS", "refs": ["rg:no references"]},
            "approved_by": approved_by,
        }

    def test_row_missing_fields_are_rejected(self):
        for field in (
            "surface_type",
            "paths",
            "outcome",
            "replacement",
            "live_consumer",
            "legacy_reader",
            "approved_by",
        ):
            with self.subTest(field=field):
                row = self._row("cap.x.y.v1")
                row.pop(field)
                errors = self._validate({"cap.x.y.v1"}, {"cap.x.y.v1"}, [row])
                self.assertIn(
                    f"retirement_row_missing:cap.x.y.v1:{field}",
                    [e["code"] for e in errors],
                )

    def test_candidate_id_missing_is_rejected(self):
        row = self._row("cap.x.y.v1")
        row.pop("candidate_id")
        errors = self._validate({"cap.x.y.v1"}, {"cap.x.y.v1"}, [row])
        self.assertIn(
            "retirement_row_missing:<candidate>:candidate_id",
            [e["code"] for e in errors],
        )

    def test_invalid_outcome_is_rejected(self):
        rows = [self._row("cap.x.y.v1", outcome="archive")]
        errors = self._validate({"cap.x.y.v1"}, {"cap.x.y.v1"}, rows)
        self.assertIn(
            "retirement_outcome_invalid:cap.x.y.v1",
            [e["code"] for e in errors],
        )

    def test_delete_without_approval_is_rejected(self):
        rows = [self._row("cap.x.y.v1", outcome="delete")]
        errors = self._validate({"cap.x.y.v1"}, set(), rows)
        self.assertIn(
            "retirement_delete_not_approved:cap.x.y.v1",
            [e["code"] for e in errors],
        )

    def test_delete_with_live_consumer_is_rejected(self):
        rows = [
            self._row(
                "cap.x.y.v1",
                outcome="delete",
                approved_by="design:2026-07-13",
                live_consumer={"status": "FAIL", "refs": ["skills/director.md:12"]},
            )
        ]
        errors = self._validate({"cap.x.y.v1"}, set(), rows)
        self.assertIn(
            "retirement_delete_live_consumer:cap.x.y.v1",
            [e["code"] for e in errors],
        )

    def test_delete_with_required_legacy_reader_is_rejected(self):
        rows = [
            self._row(
                "cap.x.y.v1",
                outcome="delete",
                approved_by="design:2026-07-13",
                legacy_reader={"status": "FAIL", "refs": ["RUNBOOK.md:44"]},
            )
        ]
        errors = self._validate({"cap.x.y.v1"}, set(), rows)
        self.assertIn(
            "retirement_delete_legacy_reader:cap.x.y.v1",
            [e["code"] for e in errors],
        )

    def test_delete_with_unknown_consumer_is_rejected(self):
        rows = [{
            "candidate_id": "cap.x.y.v1",
            "surface_type": "capability",
            "paths": ["skills/x.md"],
            "outcome": "delete",
            "replacement": None,
            "live_consumer": {"status": "UNKNOWN", "refs": []},
            "legacy_reader": {"status": "PASS", "refs": ["rg:no references"]},
            "approved_by": "design:2026-07-13",
        }]
        errors = self._validate({"cap.x.y.v1"}, set(), rows)
        self.assertIn(
            "retirement_delete_unknown:cap.x.y.v1",
            [e["code"] for e in errors],
        )

    def test_delete_with_unknown_legacy_reader_is_rejected(self):
        rows = [{
            "candidate_id": "cap.x.y.v1",
            "surface_type": "capability",
            "paths": ["skills/x.md"],
            "outcome": "delete",
            "replacement": None,
            "live_consumer": {"status": "PASS", "refs": ["rg:no references"]},
            "legacy_reader": {"status": "UNKNOWN", "refs": []},
            "approved_by": "design:2026-07-13",
        }]
        errors = self._validate({"cap.x.y.v1"}, set(), rows)
        self.assertIn(
            "retirement_delete_unknown:cap.x.y.v1",
            [e["code"] for e in errors],
        )

    def test_removed_capability_without_approved_delete_row_is_rejected(self):
        rows = [self._row("cap.keep.v1", outcome="keep")]
        errors = self._validate(
            {"cap.keep.v1", "cap.delete.v1"},
            {"cap.keep.v1"},
            rows,
        )
        self.assertIn(
            "retirement_unapproved_catalog_removal:cap.delete.v1",
            [e["code"] for e in errors],
        )

    def test_keep_and_legacy_read_only_ids_cannot_disappear(self):
        rows = [
            self._row("cap.keep.v1", outcome="keep"),
            self._row("cap.legacy.v1", outcome="legacy_read_only"),
            self._row(
                "cap.delete.v1",
                outcome="delete",
                approved_by="design:2026-07-13",
            ),
        ]
        errors = self._validate(
            {"cap.keep.v1", "cap.legacy.v1", "cap.delete.v1"},
            set(),
            rows,
        )
        codes = {e["code"] for e in errors}
        self.assertIn("retirement_preserved_id_missing:cap.keep.v1", codes)
        self.assertIn("retirement_preserved_id_missing:cap.legacy.v1", codes)

    def test_only_approved_delete_ids_may_disappear(self):
        rows = [
            self._row("cap.keep.v1", outcome="keep"),
            self._row("cap.legacy.v1", outcome="legacy_read_only"),
            self._row(
                "cap.delete.v1",
                outcome="delete",
                approved_by="design:2026-07-13",
            ),
        ]
        self.assertEqual(
            [],
            self._validate(
                {"cap.keep.v1", "cap.legacy.v1", "cap.delete.v1"},
                {"cap.keep.v1", "cap.legacy.v1"},
                rows,
            ),
        )


if __name__ == "__main__":
    unittest.main()
