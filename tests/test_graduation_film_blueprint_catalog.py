import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.graduation_film_blueprint_catalog import (
    CANON_SECTION_IDS,
    TRAINING_MODULE_IDS,
    build_graduation_film_dry_run,
    build_graduation_film_real_source_dry_run,
    write_graduation_film_dry_run,
    write_graduation_film_real_source_dry_run,
)
from video_pipeline_core.film_canon_registry import (
    get_film_canon_route,
    list_supported_film_types,
    write_film_canon_route_dry_run,
)
from video_pipeline_core.film_canon_production_readiness import (
    build_product_route_review_decision,
    write_film_canon_production_readiness,
)
from video_pipeline_core.visual_selection_gate import evaluate_visual_selection_gate


def _fixture_materials(root: Path) -> Path:
    source_root = root / "fixture_source"
    for relative in [
        "basic/basic_drill_01.mp4",
        "basic/basic_drill_02.mp4",
        "advanced/advanced_teamwork_01.mp4",
        "certification/cert_award_01.mp4",
        "physical/rope_run_01.mp4",
        "encouragement/team_cheer_01.mp4",
        "daily_life/lunch_record_01.jpg",
        "special_activity/night_event_01.mp4",
        "misc/unknown_clip_01.mp4",
    ]:
        path = source_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture media")
    return source_root


def _real_source_style_materials(root: Path) -> Path:
    source_root = root / "real_source_style"
    for relative in [
        "01_工安體感/工安體感_01.mp4",
        "02_拖拉電纜/拖拉電纜_練習.mp4",
        "03_換桿/換桿_分組.mp4",
        "04_活線作業/活線作業_示範.mp4",
        "05_主任勉勵/主任勉勵_致詞.mp4",
        "06_感謝導師/感謝導師_結尾.mp4",
        "07_體能/體能跑步.mp4",
        "08_午餐/午餐生活.jpg",
        "09_檢定/檢定測驗.mp4",
    ]:
        path = source_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture media")
    return source_root


def _daily_kids_fixture_materials(root: Path) -> Path:
    source_root = root / "daily_kids_fixture"
    for relative in [
        "eating/breakfast_smile.mp4",
        "playing/toy_blocks.mov",
        "learning/first_words.mp4",
        "family/grandma_hug.jpg",
        "outdoor/park_walk.mp4",
        "school/kindergarten_day.jpg",
        "birthday/birthday_cake.mp4",
        "random/cute_dance.mp4",
    ]:
        path = source_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture media")
    return source_root


def _sparse_graduation_materials(root: Path) -> Path:
    source_root = root / "sparse_graduation_fixture"
    for relative in [
        "01_basic/basic_training.mp4",
        "02_advanced/advanced_training.mp4",
        "03_supervisor/\u4e3b\u4efb_speech.mp4",
        "04_teacher/\u5c0e\u5e2b_intro.mp4",
        "05_closing/\u611f\u8b1d_closing.mp4",
        "06_physical/physical_run.mp4",
        "07_daily/daily_life.mp4",
        "08_special/special_event.mp4",
    ]:
        path = source_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture media")
    return source_root


class GraduationFilmBlueprintCatalogTest(unittest.TestCase):
    def test_film_canon_registry_lists_supported_product_routes(self):
        supported = list_supported_film_types()

        self.assertIn("graduation_training_film", supported)
        self.assertIn("daily_kids_memory_film", supported)
        self.assertEqual(
            get_film_canon_route("graduation_training_film")["film_type"],
            "graduation_training_film",
        )

    def test_film_canon_registry_selects_graduation_without_breaking_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "graduation"
            source_root = _fixture_materials(Path(tmp))
            summary = write_film_canon_route_dry_run(
                "graduation_training_film",
                source_root,
                out_dir,
            )

            canon = json.loads((out_dir / "graduation_film_canon.json").read_text(encoding="utf-8"))
            self.assertEqual([section["section_id"] for section in canon["sections"]], CANON_SECTION_IDS)
            self.assertIn("graduation_real_source_review_packet.json", summary["artifacts"])
            self.assertFalse((out_dir / "final.mp4").exists())
            self.assertFalse((out_dir / "story_human_review_decision.json").exists())

    def test_film_canon_registry_selects_daily_kids_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "daily_kids"
            source_root = _daily_kids_fixture_materials(Path(tmp))
            summary = write_film_canon_route_dry_run(
                "daily_kids_memory_film",
                source_root,
                out_dir,
            )

            canon = json.loads((out_dir / "film_canon.json").read_text(encoding="utf-8"))
            self.assertEqual(canon["film_type"], "daily_kids_memory_film")
            self.assertEqual(
                [section["section_id"] for section in canon["sections"]],
                [
                    "opening_memory_hook",
                    "daily_life_montage",
                    "milestone_moments",
                    "cute_funny_moments",
                    "family_interaction",
                    "closing_memory_note",
                ],
            )
            catalog = json.loads((out_dir / "catalog_map.json").read_text(encoding="utf-8"))
            module_ids = [module["module_id"] for module in catalog["modules"]]
            self.assertEqual(
                module_ids,
                [
                    "eating",
                    "playing",
                    "learning",
                    "family",
                    "outdoor",
                    "school",
                    "birthday_or_special_event",
                    "random_cute_optional",
                ],
            )
            self.assertTrue(summary["review_packet"])
            self.assertFalse((out_dir / "final.mp4").exists())
            self.assertFalse((out_dir / "story_human_review_decision.json").exists())
            for path in out_dir.iterdir():
                if path.suffix in {".json", ".md"}:
                    text = path.read_text(encoding="utf-8")
                    self.assertNotIn("\ufffd", text)
                    self.assertNotIn("????", text)

    def test_unknown_film_type_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                write_film_canon_route_dry_run(
                    "unknown_product",
                    Path(tmp),
                    Path(tmp) / "out",
                )

    def test_human_product_route_approval_creates_production_readiness_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = _daily_kids_fixture_materials(root)
            out_dir = root / "readiness"
            decision = build_product_route_review_decision(
                decision="approved",
                reviewer="human",
                notes="fixture product route approved for planning",
                approve_all_reviewed=True,
            )

            summary = write_film_canon_production_readiness(
                "daily_kids_memory_film",
                source_root,
                out_dir,
                decision=decision,
            )

            required = [
                "product_route_review_decision.json",
                "reviewed_catalog_map.json",
                "story_material_planning_handoff.json",
                "opener_closer_design_handoff.json",
                "audio_subtitle_review_handoff.json",
                "production_readiness_gate.json",
                "production_worker_handoff_prompt.md",
                "product_route_review_packet.md",
                "product_route_review_packet.json",
            ]
            self.assertEqual(sorted(summary["artifacts"]), sorted(required))
            gate = json.loads((out_dir / "production_readiness_gate.json").read_text(encoding="utf-8"))
            self.assertTrue(gate["ready_for_production"])
            self.assertEqual(gate["next_owner"], "production_worker")
            reviewed = json.loads((out_dir / "reviewed_catalog_map.json").read_text(encoding="utf-8"))
            statuses = reviewed["summary"]["status_counts"]
            self.assertGreater(statuses["accepted"], 0)
            self.assertFalse((out_dir / "final.mp4").exists())
            self.assertFalse((out_dir / "story_human_review_decision.json").exists())

    def test_non_human_approval_revision_and_rejected_are_not_production_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = _daily_kids_fixture_materials(root)
            cases = [
                ("approved", "agent", "waiting_product_review"),
                ("revision_requested", "human", "repair_product_route"),
                ("rejected", "human", "repair_product_route"),
            ]
            for decision_value, reviewer, next_owner in cases:
                out_dir = root / f"{decision_value}_{reviewer}"
                summary = write_film_canon_production_readiness(
                    "daily_kids_memory_film",
                    source_root,
                    out_dir,
                    decision=build_product_route_review_decision(
                        decision=decision_value,
                        reviewer=reviewer,
                        notes="needs route handling",
                    ),
                )
                gate = json.loads((out_dir / "production_readiness_gate.json").read_text(encoding="utf-8"))
                self.assertFalse(gate["ready_for_production"], summary)
                self.assertEqual(gate["next_owner"], next_owner)
                self.assertFalse((out_dir / "final.mp4").exists())
                self.assertFalse((out_dir / "story_human_review_decision.json").exists())

    def test_pending_product_route_review_is_not_catalog_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = _daily_kids_fixture_materials(root)
            out_dir = root / "pending_review"

            summary = write_film_canon_production_readiness(
                "daily_kids_memory_film",
                source_root,
                out_dir,
                decision=build_product_route_review_decision(
                    decision="pending_review",
                    reviewer="none",
                    notes="waiting for product route review",
                ),
            )

            statuses = summary["reviewed_catalog_status_counts"]
            self.assertGreater(statuses["pending_review"], 0)
            self.assertEqual(statuses["missing"], 0)
            gate = json.loads((out_dir / "production_readiness_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(gate["ready_for_production"])
            self.assertEqual(gate["blockers"], ["product_route_review_required"])
            self.assertNotIn("catalog_has_missing_modules", gate["warnings"])

    def test_product_route_review_writer_writes_human_decision_and_rejects_unsafe_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = _daily_kids_fixture_materials(root)
            out_dir = root / "writer_run"
            write_film_canon_production_readiness(
                "daily_kids_memory_film",
                source_root,
                out_dir,
                decision=build_product_route_review_decision(
                    decision="pending_review",
                    reviewer="none",
                    notes="waiting for product route review",
                ),
            )
            tool = Path(__file__).resolve().parents[1] / "tools" / "write_product_route_review_decision.py"

            ok = subprocess.run(
                [
                    sys.executable,
                    str(tool),
                    "--run",
                    str(out_dir),
                    "--decision",
                    "approved",
                    "--reviewer",
                    "human",
                    "--approve-all-reviewed",
                    "--module-status",
                    "random_cute_optional=optional:operator accepted as optional",
                    "--json",
                ],
                text=True,
                capture_output=True,
            )
            self.assertEqual(ok.returncode, 0, ok.stderr)
            written = json.loads((out_dir / "product_route_review_decision.json").read_text(encoding="utf-8"))
            self.assertEqual(written["decision"], "approved")
            self.assertEqual(written["reviewer"], "human")
            self.assertFalse(written["is_final_delivery_approval"])
            self.assertFalse(written["clears_story_human_review"])
            self.assertEqual(written["module_overrides"][0]["module_id"], "random_cute_optional")
            self.assertFalse((out_dir / "story_human_review_decision.json").exists())

            non_human = subprocess.run(
                [
                    sys.executable,
                    str(tool),
                    "--run",
                    str(out_dir),
                    "--decision",
                    "approved",
                    "--reviewer",
                    "agent",
                    "--approve-all-reviewed",
                    "--json",
                ],
                text=True,
                capture_output=True,
            )
            self.assertEqual(non_human.returncode, 2)

            ambiguous = subprocess.run(
                [
                    sys.executable,
                    str(tool),
                    "--run",
                    str(out_dir),
                    "--decision",
                    "approved",
                    "--reviewer",
                    "human",
                    "--json",
                ],
                text=True,
                capture_output=True,
            )
            self.assertEqual(ambiguous.returncode, 2)

            pathlike = subprocess.run(
                [
                    sys.executable,
                    str(tool),
                    "--run",
                    str(out_dir),
                    "--decision",
                    "revision_requested",
                    "--reviewer",
                    "human",
                    "--note",
                    "needs route revision",
                    "--out-name",
                    "../bad.json",
                    "--json",
                ],
                text=True,
                capture_output=True,
            )
            self.assertEqual(pathlike.returncode, 2)

    def test_readiness_consumes_decision_path_and_optional_missing_module_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = _sparse_graduation_materials(root)
            initial = root / "initial"
            write_film_canon_production_readiness(
                "graduation_training_film",
                source_root,
                initial,
                decision=build_product_route_review_decision(
                    decision="pending_review",
                    reviewer="none",
                    notes="waiting for product route review",
                ),
            )
            initial_counts = json.loads((initial / "reviewed_catalog_map.json").read_text(encoding="utf-8"))["summary"]["status_counts"]
            self.assertGreater(initial_counts["pending_review"], 0)
            self.assertGreater(initial_counts["missing"], 0)

            decision_path = initial / "product_route_review_decision.json"
            decision_path.write_text(
                json.dumps(
                    build_product_route_review_decision(
                        decision="approved",
                        reviewer="human",
                        notes="human product route approved with optional gaps",
                        approve_all_reviewed=True,
                        module_overrides=[
                            {
                                "module_id": "certification",
                                "status": "optional",
                                "review_note": "not required for this production route",
                            },
                            {
                                "module_id": "encouragement_activity",
                                "status": "optional",
                                "review_note": "not required for this production route",
                            },
                        ],
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            approved = root / "approved"
            summary = write_film_canon_production_readiness(
                "graduation_training_film",
                source_root,
                approved,
                decision_path=decision_path,
            )
            counts = summary["reviewed_catalog_status_counts"]
            self.assertGreater(counts["accepted"], 0)
            self.assertGreaterEqual(counts["optional"], 2)
            self.assertEqual(counts["missing"], 0)
            self.assertEqual(counts["pending_review"], 0)
            gate = summary["production_readiness_gate"]
            self.assertTrue(gate["ready_for_production"], gate)

    def test_production_worker_prompt_contains_required_basis_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = _daily_kids_fixture_materials(root)
            out_dir = root / "prompt"
            write_film_canon_production_readiness(
                "daily_kids_memory_film",
                source_root,
                out_dir,
                decision=build_product_route_review_decision(
                    decision="pending_review",
                    reviewer="none",
                    notes="waiting for product route review",
                ),
            )

            prompt = (out_dir / "production_worker_handoff_prompt.md").read_text(encoding="utf-8")
            self.assertIn("Film type: daily_kids_memory_film", prompt)
            self.assertIn("Selected story shell", prompt)
            self.assertIn("Reviewed module status summary", prompt)
            self.assertIn("Opener/closer design requirements", prompt)
            self.assertIn("Training MV music policy", prompt)
            self.assertIn("Source speech/subtitle/readability requirements", prompt)
            self.assertIn("Do not render until product readiness is true", prompt)

    def test_product_readiness_outputs_are_utf8_and_include_handoffs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = _daily_kids_fixture_materials(root)
            out_dir = root / "readiness_utf8"
            write_film_canon_production_readiness(
                "daily_kids_memory_film",
                source_root,
                out_dir,
                decision=build_product_route_review_decision(
                    decision="approved",
                    reviewer="human",
                    notes="fixture approved",
                    approve_all_reviewed=True,
                ),
            )

            for name in [
                "story_material_planning_handoff.json",
                "opener_closer_design_handoff.json",
                "audio_subtitle_review_handoff.json",
                "product_route_review_packet.md",
                "product_route_review_packet.json",
            ]:
                path = out_dir / name
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("\ufffd", text)
                self.assertNotIn("????", text)

    def test_visual_selection_gate_blocks_token_only_sensitive_selections(self):
        report = evaluate_visual_selection_gate({
            "selections": [
                {
                    "beat_id": "newcomer_training_start",
                    "source_relative_path": "工安早會/IMG_2120.JPG",
                    "candidate_source": "token_folder_match",
                },
                {
                    "beat_id": "basic_training",
                    "source_relative_path": "工安早會/IMG_2124.JPG",
                    "candidate_source": "token_folder_match",
                },
            ]
        })

        self.assertFalse(report["pass"])
        rules = {item["rule"] for item in report["blocking"]}
        self.assertIn("visual_confirmation_missing", rules)
        self.assertIn("token_only_selection_not_accepted", rules)
        self.assertEqual(
            sorted(report["blocked_token_only_selections"]),
            ["basic_training", "newcomer_training_start"],
        )

    def test_visual_selection_gate_requires_supervisor_video_audio_speech_evidence(self):
        report = evaluate_visual_selection_gate({
            "selections": [
                {
                    "beat_id": "supervisor_source_speech",
                    "source_relative_path": "主任勉勵/IMG_2141.MOV",
                    "candidate_source": "agent_visual_review",
                    "visual_confirmation_status": "accepted",
                    "reviewer_type": "agent_visual_review",
                    "representative_frame": "frames/supervisor.jpg",
                    "forbidden_role_flags_checked": True,
                    "video_evidence": True,
                }
            ]
        })

        self.assertFalse(report["pass"])
        self.assertIn(
            "supervisor_source_speech_missing_audio_speech_evidence",
            {item["rule"] for item in report["blocking"]},
        )

    def test_visual_selection_gate_blocks_rejected_and_needs_repick(self):
        report = evaluate_visual_selection_gate({
            "selections": [
                {
                    "beat_id": "newcomer_training_start",
                    "source_relative_path": "工安早會/IMG_2120.JPG",
                    "candidate_source": "agent_visual_review",
                    "visual_confirmation_status": "rejected",
                    "reviewer_type": "agent_visual_review",
                    "representative_frame": "frames/newcomer.jpg",
                    "forbidden_role_flags_checked": True,
                },
                {
                    "beat_id": "basic_training",
                    "source_relative_path": "工安早會/IMG_2124.JPG",
                    "candidate_source": "agent_visual_review",
                    "visual_confirmation_status": "needs_repick",
                    "reviewer_type": "agent_visual_review",
                    "representative_frame": "frames/basic.jpg",
                    "forbidden_role_flags_checked": True,
                },
            ]
        })

        self.assertFalse(report["pass"])
        self.assertEqual(
            [item["rule"] for item in report["blocking"]],
            ["visual_selection_rejected", "visual_selection_needs_repick"],
        )

    def test_visual_selection_gate_accepts_explicit_visual_evidence(self):
        report = evaluate_visual_selection_gate({
            "selections": [
                {
                    "beat_id": "newcomer_training_start",
                    "source_relative_path": "工安早會/IMG_2120.JPG",
                    "candidate_source": "agent_visual_review",
                    "visual_confirmation_status": "accepted",
                    "reviewer_type": "agent_visual_review",
                    "representative_frame": "frames/newcomer.jpg",
                    "reason": "visible trainees at morning roll call",
                    "forbidden_role_flags_checked": True,
                    "forbidden_role_flags": {
                        "supervisor_primary": False,
                        "director_primary": False,
                        "portrait_primary": False,
                    },
                },
                {
                    "beat_id": "basic_training",
                    "source_relative_path": "工安早會/IMG_2124.JPG",
                    "candidate_source": "agent_visual_review",
                    "visual_confirmation_status": "accepted",
                    "reviewer_type": "agent_visual_review",
                    "representative_frame": "frames/basic.jpg",
                    "reason": "visible training preparation",
                    "forbidden_role_flags_checked": True,
                    "forbidden_role_flags": {
                        "supervisor_primary": False,
                        "director_primary": False,
                        "portrait_primary": False,
                    },
                },
                {
                    "beat_id": "supervisor_source_speech",
                    "source_relative_path": "主任勉勵/IMG_2141.MOV",
                    "candidate_source": "agent_visual_review",
                    "visual_confirmation_status": "accepted",
                    "reviewer_type": "agent_visual_review",
                    "representative_frame": "frames/supervisor.jpg",
                    "reason": "talking-head supervisor source-speech clip",
                    "forbidden_role_flags_checked": True,
                    "video_evidence": True,
                    "audio_evidence": True,
                    "speech_evidence": True,
                },
            ]
        })

        self.assertTrue(report["pass"], report)
        self.assertEqual(report["accepted_visual_evidence_count"], 3)

    def test_canon_defines_fixed_sections_and_training_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_root = _fixture_materials(Path(tmp))
            result = build_graduation_film_dry_run(
                {"theme": "class growth", "title": "Graduation Film"},
                source_root=source_root,
            )

        canon = result["graduation_film_canon"]
        self.assertEqual([section["section_id"] for section in canon["sections"]], CANON_SECTION_IDS)
        self.assertEqual(canon["longest_body_section"], "training_mv_catalog")
        modules = canon["training_mv_catalog"]["modules"]
        self.assertEqual([module["module_id"] for module in modules], TRAINING_MODULE_IDS)

    def test_story_shell_can_retarget_theme_without_changing_canon(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_root = _fixture_materials(Path(tmp))
            first = build_graduation_film_dry_run(
                {"theme": "discipline to confidence", "title": "First Shell"},
                source_root=source_root,
            )
            second = build_graduation_film_dry_run(
                {"theme": "ordinary days become courage", "title": "Second Shell"},
                source_root=source_root,
            )

        self.assertEqual(first["graduation_film_canon"], second["graduation_film_canon"])
        self.assertNotEqual(first["story_shell"]["theme"], second["story_shell"]["theme"])
        self.assertEqual(
            set(first["story_retargeting_notes"]["retargetable_parts"]),
            {"opening_story", "closing_story", "transition_logic", "module_ordering_emphasis"},
        )
        self.assertIn("training_mv_catalog", first["story_retargeting_notes"]["stable_parts"])

    def test_catalog_map_marks_agent_filled_assignments_for_human_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_root = _fixture_materials(Path(tmp))
            result = build_graduation_film_dry_run(
                {"theme": "training memory", "title": "Catalog"},
                source_root=source_root,
            )

        catalog = result["training_catalog_map"]
        assignments = [
            item
            for module in catalog["modules"]
            for item in module["material_assignments"]
        ]
        self.assertTrue(any(item["authority"] == "agent_filled" for item in assignments))
        self.assertTrue(all(
            item["needs_human_confirmation"]
            for item in assignments
            if item["authority"] == "agent_filled"
        ))
        self.assertTrue(all(
            item["visual_selection_role"] == "candidate"
            and item["render_facing_status"] == "candidate_only"
            and item["requires_visual_selection_gate"]
            for item in assignments
            if item["authority"] == "agent_filled"
        ))
        self.assertGreaterEqual(catalog["summary"]["agent_filled_count"], 1)
        self.assertEqual(
            catalog["summary"]["agent_filled_count"],
            catalog["summary"]["needs_human_confirmation_count"],
        )

    def test_write_dry_run_outputs_required_artifacts_without_render_or_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = _fixture_materials(tmp_path)
            out_dir = tmp_path / "dry_run"

            written = write_graduation_film_dry_run(
                {"theme": "training memory", "title": "Review Packet"},
                out_dir,
                source_root=source_root,
            )

            required = [
                "graduation_film_canon.json",
                "graduation_film_blueprint.json",
                "story_shell.json",
                "training_catalog_map.json",
                "story_retargeting_notes.json",
                "graduation_dry_run_review_packet.md",
                "graduation_dry_run_review_packet.json",
            ]
            self.assertEqual(sorted(written["artifacts"]), sorted(required))
            for name in required:
                path = out_dir / name
                self.assertTrue(path.is_file(), name)
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("\ufffd", text)
                self.assertNotIn("????", text)
            self.assertFalse((out_dir / "final.mp4").exists())
            self.assertFalse((out_dir / "story_human_review_decision.json").exists())
            packet = json.loads((out_dir / "graduation_dry_run_review_packet.json").read_text(encoding="utf-8"))
            self.assertFalse(packet["rendered"])
            self.assertFalse(packet["human_approval_written"])

    def test_real_source_style_signals_map_to_deep_graduation_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_root = _real_source_style_materials(Path(tmp))
            result = build_graduation_film_real_source_dry_run(source_root)

        catalog = result["training_catalog_map"]
        by_module = {module["module_id"]: module for module in catalog["modules"]}
        self.assertTrue(any(
            "工安體感" in item["source_relative_path"]
            and item["matched_signals"]
            and item["agent_filled"]
            and item["needs_human_confirmation"]
            for item in by_module["basic_training"]["material_assignments"]
        ))
        self.assertTrue(any("拖拉電纜" in item["source_relative_path"] for item in by_module["basic_training"]["material_assignments"]))
        self.assertTrue(any("換桿" in item["source_relative_path"] for item in by_module["advanced_training"]["material_assignments"]))
        self.assertTrue(any("活線" in item["source_relative_path"] for item in by_module["advanced_training"]["material_assignments"]))
        self.assertTrue(any("主任勉勵" in item["source_relative_path"] for item in by_module["supervisor_speech"]["material_assignments"]))
        self.assertTrue(any("感謝導師" in item["source_relative_path"] for item in by_module["teacher_class_intro"]["material_assignments"]))
        self.assertTrue(any("感謝導師" in item["source_relative_path"] for item in by_module["closing_story"]["material_assignments"]))
        self.assertGreaterEqual(catalog["summary"]["media_count"], 9)

    def test_real_source_dry_run_builds_ab_retarget_diff_and_handoffs(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_root = _real_source_style_materials(Path(tmp))
            result = build_graduation_film_real_source_dry_run(source_root)

        self.assertEqual(result["story_shell_A"]["theme"], "從新人到現場人員")
        self.assertEqual(result["story_shell_B"]["theme"], "5.5 個月，把安全變成反射")
        diff = result["story_retarget_diff_A_to_B"]
        self.assertTrue(diff["canon_unchanged"])
        self.assertIn("opening_story", diff["changed_sections"])
        self.assertIn("closing_story", diff["changed_sections"])
        self.assertIn("story_shell_A.json", diff["future_artifacts_to_regenerate"])
        self.assertIn("story_shell_B.json", diff["future_artifacts_to_regenerate"])
        self.assertFalse(diff["human_approval_reusable"])
        self.assertTrue(result["production_readiness_plan"]["requires_human_review"])
        self.assertIn("opening_story", result["opener_closer_design_handoff"]["sections"])
        self.assertTrue(result["audio_subtitle_review_requirements"]["requires_supervisor_speech_subtitles"])

    def test_write_real_source_dry_run_outputs_review_packet_without_render_or_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = _real_source_style_materials(tmp_path)
            out_dir = tmp_path / "real_source_dry_run"

            written = write_graduation_film_real_source_dry_run(source_root, out_dir)

            required = [
                "graduation_film_canon.json",
                "graduation_film_blueprint_A.json",
                "graduation_film_blueprint_B.json",
                "story_shell_A.json",
                "story_shell_B.json",
                "training_catalog_map.real_source.json",
                "story_retarget_diff_A_to_B.json",
                "production_readiness_plan.json",
                "opener_closer_design_handoff.json",
                "audio_subtitle_review_requirements.json",
                "graduation_real_source_review_packet.md",
                "graduation_real_source_review_packet.json",
            ]
            self.assertEqual(sorted(written["artifacts"]), sorted(required))
            self.assertFalse((out_dir / "final.mp4").exists())
            self.assertFalse((out_dir / "story_human_review_decision.json").exists())
            for name in required:
                text = (out_dir / name).read_text(encoding="utf-8")
                self.assertNotIn("\ufffd", text)
                self.assertNotIn("????", text)
            packet = json.loads((out_dir / "graduation_real_source_review_packet.json").read_text(encoding="utf-8"))
            self.assertIn("module_counts", packet)
            self.assertIn("representative_source_relative_paths", packet)
            self.assertIn("retarget_summary", packet)
            self.assertIn("next_production_handoffs", packet)
            self.assertFalse(packet["rendered"])
            self.assertFalse(packet["human_approval_written"])


if __name__ == "__main__":
    unittest.main()
