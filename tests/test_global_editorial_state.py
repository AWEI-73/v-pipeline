import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.global_editorial_state import (
    EditorialStateError,
    apply_delta,
    build_canon67_seed,
    build_forward_delta,
    create_revision_zero,
    hash_file,
    validate_state_file,
    validate_worker_context,
)
from video_pipeline_core.skill_tool_contract import iter_tool_entries, load_contracts


ROOT = Path(__file__).resolve().parents[1]
CAPABILITY_ID = "cap.video-pipeline-route.global-editorial-state.v1"


def source_ref(path, role="fixture"):
    return {
        "role": role,
        "path": str(path),
        "sha256": hash_file(path),
    }


def seed_payload():
    return {
        "material_context": {
            "material_origin": "curated",
            "annotation_state": "unannotated",
            "intent_notes_available": False,
            "known_input_limits": ["fixture source has no capture-intent notes"],
        },
        "operational_state": {
            "segment_order": ["seg01", "seg02"],
            "segments": {
                "seg01": {
                    "factual_purpose": "establish the setting",
                    "story_function": "introduce the group",
                    "entry_state": "distance",
                    "exit_state": "expectation",
                    "new_information": "the group has arrived",
                    "source_window_refs": [
                        {"path": "fixture.mov", "start_sec": 0.0, "duration_sec": 2.0}
                    ],
                    "review_caption": "arrival",
                    "selected_visual_families": ["arrival"],
                    "reuse_justifications": [],
                    "cross_segment_repetition_risks": [],
                    "decision_completeness": "PASS",
                    "decision_reason": "direct source window",
                },
                "seg02": {
                    "factual_purpose": "show formation",
                    "story_function": "make the group legible",
                    "entry_state": "distance",
                    "exit_state": "order",
                    "new_information": "the group forms",
                    "source_window_refs": [
                        {"path": "fixture.jpg", "start_sec": 0.0, "duration_sec": 2.0}
                    ],
                    "review_caption": "formation",
                    "selected_visual_families": ["formation"],
                    "reuse_justifications": [],
                    "cross_segment_repetition_risks": [],
                    "decision_completeness": "PASS",
                    "decision_reason": "direct source window",
                },
            },
            "coverage_ledger": {},
            "visual_family_ledger": {},
            "people_ledger": {},
            "motif_ledger": {},
        },
        "editorial_intent": {
            "enforceable": False,
            "thesis": "accepted thesis",
            "logline": "accepted logline",
            "motif_guidance": ["accepted motif"],
        },
        "open_story_risks": [],
        "retired_story_intents": [],
        "verification_state": {
            "focused_tests": {"status": "PASS", "evidence": ["focused command"]},
            "full_suite": {
                "status": "STALE",
                "last_green_count": 2786,
                "evidence_path": "historical/full-suite.json",
                "stale_because": "post-green surface changed",
            },
        },
    }


class GlobalEditorialStateTest(unittest.TestCase):
    def write_fixture_sources(self, root):
        paths = []
        for name in ["fixture.mov", "fixture.jpg"]:
            path = root / name
            path.write_bytes(name.encode("ascii"))
            paths.append(path)
        return paths

    def test_revision_zero_initializes_and_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = self.write_fixture_sources(root)
            state_path = create_revision_zero(
                output_dir=root / "editorial_state",
                project_id="fixture-project",
                seed=seed_payload(),
                source_artifacts=[source_ref(path) for path in sources],
            )
            result = validate_state_file(state_path)
            self.assertEqual("PASS", result["status"])
            self.assertEqual(0, result["revision_id"])
            self.assertEqual("global_editorial_state", result["artifact_role"])

    def test_create_exclusive_writes_reject_existing_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = self.write_fixture_sources(root)
            kwargs = {
                "output_dir": root / "editorial_state",
                "project_id": "fixture-project",
                "seed": seed_payload(),
                "source_artifacts": [source_ref(path) for path in sources],
            }
            create_revision_zero(**kwargs)
            with self.assertRaises(EditorialStateError) as caught:
                create_revision_zero(**kwargs)
            self.assertEqual("immutable_artifact_exists", caught.exception.code)

    def test_delta_creates_revision_one_and_bound_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = self.write_fixture_sources(root)
            state0 = create_revision_zero(
                output_dir=root / "editorial_state",
                project_id="fixture-project",
                seed=seed_payload(),
                source_artifacts=[source_ref(path) for path in sources],
            )
            delta = build_forward_delta(state0, repo_root=root)
            state1 = apply_delta(
                base_state_path=state0,
                delta_path=delta,
                output_dir=root / "editorial_state",
            )
            result = validate_state_file(state1)
            self.assertEqual("PASS", result["status"])
            self.assertEqual(1, result["revision_id"])
            receipt = json.loads(
                (state1.parent / "receipt_0000_to_0001.json").read_text(encoding="utf-8")
            )
            self.assertEqual(hash_file(state0), receipt["base_state_file_sha256"])
            self.assertEqual(result["state_payload_sha256"], receipt["new_state_payload_sha256"])

    def test_wrong_base_hash_rejects_with_stale_base_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = self.write_fixture_sources(root)
            state0 = create_revision_zero(
                output_dir=root / "editorial_state",
                project_id="fixture-project",
                seed=seed_payload(),
                source_artifacts=[source_ref(path) for path in sources],
            )
            delta = build_forward_delta(state0, repo_root=root)
            data = json.loads(delta.read_text(encoding="utf-8"))
            data["base_state_sha256"] = "0" * 64
            bad_delta = root / "bad_delta.json"
            bad_delta.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(EditorialStateError) as caught:
                apply_delta(
                    base_state_path=state0,
                    delta_path=bad_delta,
                    output_dir=root / "editorial_state",
                )
            self.assertEqual("stale_base_state", caught.exception.code)

    def test_state_and_receipt_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = self.write_fixture_sources(root)
            state0 = create_revision_zero(
                output_dir=root / "editorial_state",
                project_id="fixture-project",
                seed=seed_payload(),
                source_artifacts=[source_ref(path) for path in sources],
            )
            delta = build_forward_delta(state0, repo_root=root)
            state1 = apply_delta(
                base_state_path=state0,
                delta_path=delta,
                output_dir=root / "editorial_state",
            )
            state_data = json.loads(state1.read_text(encoding="utf-8"))
            state_data["last_updated_by_receipt"]["sha256"] = "1" * 64
            state1.write_text(json.dumps(state_data), encoding="utf-8")
            with self.assertRaises(EditorialStateError) as caught:
                validate_state_file(state1)
            self.assertEqual("state_receipt_hash_mismatch", caught.exception.code)

            state_data["last_updated_by_receipt"]["sha256"] = hash_file(
                state1.parent / "receipt_0000_to_0001.json"
            )
            state1.write_text(json.dumps(state_data), encoding="utf-8")
            receipt_path = state1.parent / "receipt_0000_to_0001.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["new_state_payload_sha256"] = "2" * 64
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            state_data["last_updated_by_receipt"]["sha256"] = hash_file(receipt_path)
            state1.write_text(json.dumps(state_data), encoding="utf-8")
            with self.assertRaises(EditorialStateError) as caught:
                validate_state_file(state1)
            self.assertEqual("receipt_payload_hash_mismatch", caught.exception.code)

    def test_invalid_provenance_axes_are_rejected(self):
        for field, value, code in [
            ("material_origin", "invented", "invalid_material_origin"),
            ("annotation_state", "invented", "invalid_annotation_state"),
        ]:
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    sources = self.write_fixture_sources(root)
                    seed = seed_payload()
                    seed["material_context"][field] = value
                    with self.assertRaises(EditorialStateError) as caught:
                        create_revision_zero(
                            output_dir=root / "editorial_state",
                            project_id="fixture-project",
                            seed=seed,
                            source_artifacts=[source_ref(path) for path in sources],
                        )
                    self.assertEqual(code, caught.exception.code)

    def test_pass_segment_without_source_windows_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = self.write_fixture_sources(root)
            seed = seed_payload()
            seed["operational_state"]["segments"]["seg01"]["source_window_refs"] = []
            with self.assertRaises(EditorialStateError) as caught:
                create_revision_zero(
                    output_dir=root / "editorial_state",
                    project_id="fixture-project",
                    seed=seed,
                    source_artifacts=[source_ref(path) for path in sources],
                )
            self.assertEqual("pass_without_source_window_refs", caught.exception.code)

    def test_worker_context_rejects_stale_revision_and_accepts_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = self.write_fixture_sources(root)
            state0 = create_revision_zero(
                output_dir=root / "editorial_state",
                project_id="fixture-project",
                seed=seed_payload(),
                source_artifacts=[source_ref(path) for path in sources],
            )
            delta = build_forward_delta(state0, repo_root=root)
            state1 = apply_delta(
                base_state_path=state0,
                delta_path=delta,
                output_dir=root / "editorial_state",
            )
            stale = {
                "pinned_state_path": str(state0),
                "pinned_state_sha256": hash_file(state0),
            }
            with self.assertRaises(EditorialStateError) as caught:
                validate_worker_context(stale, current_state_path=state1)
            self.assertEqual("stale_base_state", caught.exception.code)
            current = {
                "pinned_state_path": str(state1),
                "pinned_state_sha256": hash_file(state1),
            }
            self.assertEqual(
                "PASS",
                validate_worker_context(current, current_state_path=state1)["status"],
            )

    def test_registered_tool_is_discoverable_without_orphan(self):
        contracts, parse_errors = load_contracts(ROOT / "skills")
        self.assertEqual([], parse_errors)
        entries = [
            entry
            for contract in contracts
            for entry in iter_tool_entries(contract)
            if entry.get("capability_id") == CAPABILITY_ID
        ]
        self.assertEqual(1, len(entries))
        self.assertEqual("tools/global_editorial_state.py", entries[0]["tool"])
        self.assertEqual("deterministic", entries[0]["execution_class"])
        self.assertEqual("adapter", entries[0]["capability_role"])
        self.assertEqual([], entries[0]["loops"])
        self.assertEqual("experimental", entries[0]["maturity"])

    def test_cli_emits_stable_json_error_code(self):
        completed = subprocess.run(
            [
                sys.executable,
                "tools/global_editorial_state.py",
                "validate-worker-context",
                "--context-json",
                "missing-context.json",
                "--current-state",
                "missing-state.json",
                "--json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(1, completed.returncode)
        payload = json.loads(completed.stdout)
        self.assertIn("code", payload)

    def test_non_calibrated_segments_are_unknown(self):
        seed, _ = build_canon67_seed(ROOT)
        segments = seed["operational_state"]["segments"]
        self.assertEqual("PASS", segments["seg01_time_moves_people_begin"]["decision_completeness"])
        self.assertEqual("PASS", segments["seg02_first_gathering"]["decision_completeness"])
        for segment_id in [
            "seg03_discipline_before_skill",
            "seg04_cable_teamwork",
            "seg05_height_and_pressure",
            "seg06_standards_make_ready",
            "seg07_life_builds_belonging",
            "seg08_supervisor_witness",
            "seg10_departure_with_responsibility",
        ]:
            with self.subTest(segment_id=segment_id):
                self.assertEqual("UNKNOWN", segments[segment_id]["decision_completeness"])
                self.assertEqual(
                    "not_calibrated_in_v0_forward_test",
                    segments[segment_id]["decision_reason"],
                )
        self.assertEqual(
            "UNKNOWN",
            segments["seg09_people_who_held_the_line"]["decision_completeness"],
        )
        self.assertEqual(
            "deferred_due_to_incomplete_all_or_none_roster",
            seed["operational_state"]["coverage_ledger"]["teacher_adviser_sequence"]["status"],
        )

    def test_tampered_delta_is_rejected_with_receipt_delta_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = self.write_fixture_sources(root)
            state0 = create_revision_zero(
                output_dir=root / "editorial_state",
                project_id="fixture-project",
                seed=seed_payload(),
                source_artifacts=[source_ref(path) for path in sources],
            )
            delta = build_forward_delta(state0, repo_root=root)
            state1 = apply_delta(
                base_state_path=state0,
                delta_path=delta,
                output_dir=root / "editorial_state",
            )
            delta.write_text(delta.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaises(EditorialStateError) as caught:
                validate_state_file(state1)
            self.assertEqual("receipt_delta_hash_mismatch", caught.exception.code)

    def test_revision_one_to_two_uses_dynamic_filenames(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = self.write_fixture_sources(root)
            state0 = create_revision_zero(
                output_dir=root / "editorial_state",
                project_id="fixture-project",
                seed=seed_payload(),
                source_artifacts=[source_ref(path) for path in sources],
            )
            delta1 = build_forward_delta(state0, repo_root=root)
            state1 = apply_delta(
                base_state_path=state0,
                delta_path=delta1,
                output_dir=root / "editorial_state",
            )
            delta2 = build_forward_delta(state1, repo_root=root)
            state2 = apply_delta(
                base_state_path=state1,
                delta_path=delta2,
                output_dir=root / "editorial_state",
            )
            self.assertEqual("revision_0002.json", state2.name)
            self.assertTrue((state2.parent / "delta_0001_to_0002.json").is_file())
            self.assertTrue((state2.parent / "receipt_0001_to_0002.json").is_file())
            self.assertEqual(2, validate_state_file(state2)["revision_id"])

    def test_genesis_receipt_binding_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = self.write_fixture_sources(root)
            state0 = create_revision_zero(
                output_dir=root / "editorial_state",
                project_id="fixture-project",
                seed=seed_payload(),
                source_artifacts=[source_ref(path) for path in sources],
            )
            state = json.loads(state0.read_text(encoding="utf-8"))
            receipt_ref = state["last_updated_by_receipt"]
            self.assertIsNotNone(receipt_ref)
            receipt_path = state0.parent / receipt_ref["path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertIsNone(receipt["base_state_file_sha256"])
            self.assertIsNone(receipt["delta_path"])
            self.assertEqual("PASS", validate_state_file(state0)["status"])
            receipt["new_state_payload_sha256"] = "3" * 64
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            state["last_updated_by_receipt"]["sha256"] = hash_file(receipt_path)
            state0.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaises(EditorialStateError) as caught:
                validate_state_file(state0)
            self.assertEqual("receipt_payload_hash_mismatch", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
