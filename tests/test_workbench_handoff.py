import json
import tempfile
import unittest
from pathlib import Path

from types import SimpleNamespace
from contextlib import redirect_stdout
from io import StringIO

import video_tools
from tools.workbench_handoff import (
    build_handoff,
    build_human_decision,
    validate_handoff,
    validate_human_decision,
)


def _write(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class WorkbenchHandoffTest(unittest.TestCase):
    def test_human_decision_binds_subject_and_current_patch_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            timeline = root / "timeline.json"
            _write(timeline, {"plan": []})
            patch = {
                "artifact_role": "timeline_patch",
                "version": 1,
                "patches": [{"op": "set_duration"}],
            }
            decision = build_human_decision(
                str(root),
                preview={"source_artifact": str(timeline), "duration_sec": 12.0},
                decision_context={
                    "duration_policy": "flexible",
                    "review_notes": [{
                        "category": "timing",
                        "scope": "segment",
                        "slot_index": 0,
                        "timeline_window": {"start_sec": 0, "end_sec": 2},
                        "text": "這段再短一點。",
                    }],
                },
                provided_patches={"timeline_patch": patch},
            )

        self.assertEqual(validate_human_decision(decision), [])
        self.assertEqual(decision["subject"]["binding_status"], "bound_exact_timeline")
        self.assertEqual(set(decision["patch_bindings"]), {"timeline_patch"})
        self.assertFalse(decision["human_creative_approval"])

        decision["review_notes"][0]["text"] = "tampered"
        self.assertIn("signature digest mismatch", validate_human_decision(decision))

    def test_handoff_routes_only_patch_bindings_from_latest_human_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            timeline = root / "timeline.json"
            _write(timeline, {"plan": []})
            timeline_patch = {
                "artifact_role": "timeline_patch",
                "version": 1,
                "patches": [{"op": "set_duration"}],
            }
            stale_effect = {
                "artifact_role": "effect_patch",
                "version": 1,
                "patches": [{"op": "add_effect"}],
            }
            _write(root / "timeline_patch.json", timeline_patch)
            _write(root / "effect_patch.json", stale_effect)
            decision = build_human_decision(
                str(root),
                preview={"source_artifact": str(timeline), "duration_sec": 12.0},
                decision_context={"duration_policy": "fixed"},
                provided_patches={"timeline_patch": timeline_patch},
            )
            _write(root / "workbench_human_decision.json", decision)

            handoff = build_handoff(str(root))

        owners = {item["owner"] for item in handoff["route_back"]}
        self.assertEqual(decision["duration_policy"]["tolerance_sec"], 0.0)
        self.assertIn("brownfield-edit", owners)
        self.assertIn("build-planning", owners)
        self.assertNotIn("effect-factory", owners)
        self.assertNotIn("effect_patch", handoff["artifacts"])
        self.assertNotIn("effect_patch", handoff["artifact_details"])
        self.assertEqual(handoff["summary"]["effect_intents"], 0)

    def test_handoff_records_draft_artifact_hashes_and_sizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            timeline_patch = {
                "artifact_role": "timeline_patch",
                "version": 1,
                "patches": [{"op": "set_duration"}],
            }
            _write(root / "timeline_patch.json", timeline_patch)
            _write(root / "patched_draft_timeline.json", {"plan": []})

            handoff = build_handoff(str(root))

        self.assertEqual(handoff["artifact_role"], "workbench_handoff")
        self.assertIn("timeline_patch", handoff["artifacts"])
        self.assertEqual(handoff["artifacts"]["timeline_patch"], "timeline_patch.json")
        detail = handoff["artifact_details"]["timeline_patch"]
        self.assertEqual(detail["path"], "timeline_patch.json")
        self.assertGreater(detail["size_bytes"], 0)
        self.assertRegex(detail["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(handoff["summary"]["timeline_edits"], 1)

    def test_handoff_records_review_report_artifacts_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "workbench_review_report.json", {"artifact_role": "workbench_review_report"})
            (root / "workbench_review_report.md").write_text("# report", encoding="utf-8")
            handoff = build_handoff(str(root))

        self.assertIn("workbench_review_report", handoff["artifacts"])
        self.assertIn("workbench_review_report_md", handoff["artifacts"])
        self.assertRegex(
            handoff["artifact_details"]["workbench_review_report"]["sha256"],
            r"^[0-9a-f]{64}$",
        )

    def test_handoff_records_preview_timeline_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "preview_timeline.json", {
                "artifact_role": "preview_timeline",
                "version": 1,
                "clips": [],
            })

            handoff = build_handoff(str(root))
            _write(root / "workbench_handoff.json", handoff)
            validation = validate_handoff(str(root))

        self.assertEqual(handoff["artifacts"]["preview_timeline"], "preview_timeline.json")
        self.assertRegex(handoff["artifact_details"]["preview_timeline"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(validation["ok"], validation["errors"])
        self.assertIn("preview_timeline", validation["present_artifacts"])

    def test_handoff_records_workbench_revision_request_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "workbench_revision_request.json", {
                "artifact_role": "workbench_revision_request",
                "version": 1,
                "issues": [],
            })

            handoff = build_handoff(str(root))
            _write(root / "workbench_handoff.json", handoff)
            validation = validate_handoff(str(root))

        self.assertEqual(
            handoff["artifacts"]["workbench_revision_request"],
            "workbench_revision_request.json",
        )
        self.assertTrue(validation["ok"], validation["errors"])
        self.assertIn("workbench_revision_request", validation["present_artifacts"])

    def test_handoff_routes_draft_patches_back_to_owning_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "timeline_patch.json", {
                "artifact_role": "timeline_patch",
                "version": 1,
                "patches": [
                    {"op": "replace_clip", "slot_index": 0, "after": {"asset_id": "clip-b", "scene_index": 0}},
                    {"op": "set_duration", "slot_index": 1, "after": {"duration_sec": 3.0}},
                ],
            })
            _write(root / "subtitle_patch.json", {
                "artifact_role": "subtitle_patch",
                "version": 1,
                "patches": [{"op": "replace_text", "cue_index": 0}],
            })
            _write(root / "audio_cue_patch.json", {
                "artifact_role": "audio_cue_patch",
                "version": 1,
                "patches": [{"op": "add_cue", "at_sec": 10.0}],
            })
            _write(root / "effect_patch.json", {
                "artifact_role": "effect_patch",
                "version": 1,
                "patches": [{"op": "add_effect", "segment": 2}],
            })

            handoff = build_handoff(str(root))

        route_back = {item["owner"]: item for item in handoff["route_back"]}
        self.assertEqual(route_back["material-map"]["reason"], "timeline replacement changes material truth")
        self.assertEqual(route_back["build-planning"]["artifact"], "timeline_patch")
        self.assertEqual(route_back["subtitle-director"]["artifact"], "subtitle_patch")
        self.assertEqual(route_back["audio-director"]["artifact"], "audio_cue_patch")
        self.assertEqual(route_back["effect-factory"]["artifact"], "effect_patch")
        self.assertEqual(handoff["next_action"], "review_workbench_route_back")

    def test_handoff_ignores_canonical_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "timeline.json", {"canonical": True})
            _write(root / "final.mp4", {"not": "real video"})
            handoff = build_handoff(str(root))

        self.assertEqual(handoff["artifacts"], {})
        self.assertEqual(handoff["artifact_details"], {})
        self.assertEqual(handoff["summary"]["timeline_edits"], 0)

    def test_validate_handoff_accepts_consistent_draft_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "timeline_patch.json", {
                "artifact_role": "timeline_patch",
                "version": 1,
                "patches": [{"op": "set_duration"}],
            })
            _write(root / "patched_draft_timeline.json", {
                "artifact_role": "patched_draft_timeline",
                "plan": [],
            })
            _write(root / "workbench_review_report.json", {
                "artifact_role": "workbench_review_report",
                "summary": {"ok": True},
            })
            _write(root / "workbench_handoff.json", build_handoff(str(root)))

            report = validate_handoff(str(root))

        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["artifact_role"], "workbench_handoff_validation")
        self.assertCountEqual(report["present_artifacts"], [
            "timeline_patch",
            "patched_draft_timeline",
            "workbench_review_report",
        ])
        self.assertEqual(report["missing_artifacts"], [])

    def test_validate_handoff_fails_missing_handoff_or_missing_referenced_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = validate_handoff(str(root))
            self.assertFalse(missing["ok"])
            self.assertEqual(missing["errors"][0]["code"], "missing_handoff")

            _write(root / "workbench_handoff.json", {
                "artifact_role": "workbench_handoff",
                "version": 1,
                "artifacts": {"timeline_patch": "timeline_patch.json"},
                "artifact_details": {
                    "timeline_patch": {
                        "path": "timeline_patch.json",
                        "size_bytes": 10,
                        "sha256": "0" * 64,
                    }
                },
            })
            report = validate_handoff(str(root))

        self.assertFalse(report["ok"])
        self.assertIn("missing_referenced_artifact", {e["code"] for e in report["errors"]})

    def test_validate_handoff_rejects_hash_mismatch_and_canonical_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "timeline_patch.json", {
                "artifact_role": "timeline_patch",
                "version": 1,
                "patches": [],
            })
            _write(root / "workbench_handoff.json", {
                "artifact_role": "workbench_handoff",
                "version": 1,
                "artifacts": {
                    "timeline_patch": "timeline_patch.json",
                    "bad_final": "final.mp4",
                },
                "artifact_details": {
                    "timeline_patch": {
                        "path": "timeline_patch.json",
                        "size_bytes": 999,
                        "sha256": "f" * 64,
                    },
                    "bad_final": {
                        "path": "final.mp4",
                        "size_bytes": 1,
                        "sha256": "0" * 64,
                    },
                },
            })
            (root / "final.mp4").write_bytes(b"x")

            report = validate_handoff(str(root))

        self.assertFalse(report["ok"])
        codes = {e["code"] for e in report["errors"]}
        self.assertIn("hash_mismatch", codes)
        self.assertIn("size_mismatch", codes)
        self.assertIn("canonical_artifact_reference", codes)

    def test_validate_handoff_rejects_malformed_referenced_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "timeline_patch.json").write_text("{bad", encoding="utf-8")
            _write(root / "workbench_handoff.json", build_handoff(str(root)))

            report = validate_handoff(str(root))

        self.assertFalse(report["ok"])
        self.assertIn("malformed_referenced_json", {e["code"] for e in report["errors"]})

    def test_video_tools_workbench_handoff_validate_writes_report_and_fails_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "timeline_patch.json", {
                "artifact_role": "timeline_patch",
                "version": 1,
                "patches": [],
            })
            _write(root / "workbench_handoff.json", build_handoff(str(root)))
            out = root / "handoff_validation.json"

            with redirect_stdout(StringIO()):
                video_tools.cmd_workbench_handoff_validate(
                    SimpleNamespace(artifact_root=str(root), out=str(out))
                )
            self.assertTrue(json.loads(out.read_text(encoding="utf-8"))["ok"])

            (root / "timeline_patch.json").unlink()
            with self.assertRaises(Exception):
                with redirect_stdout(StringIO()):
                    video_tools.cmd_workbench_handoff_validate(
                        SimpleNamespace(artifact_root=str(root), out=None)
                    )


if __name__ == "__main__":
    unittest.main()
