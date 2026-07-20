import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


class TimelineReviewPacketTest(unittest.TestCase):
    def _fake_renderer(self, _video, walls_dir, *, expected_page_count, **_kwargs):
        paths = []
        for page in range(1, expected_page_count + 1):
            path = Path(walls_dir) / f"wall_30s_{page:02d}.jpg"
            Image.new("RGB", (320, 180), "#123456").save(path)
            paths.append(path)
        return paths

    def test_builds_uniform_wall_index_and_binds_audio_subtitle_context(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "candidate.mp4"
            video.write_bytes(b"candidate")
            probe = root / "soundtrack_probe_report.json"
            probe.write_text(json.dumps({
                "artifact_role": "soundtrack_probe_report",
                "pass": True,
                "duration_sec": 61.0,
                "analysis_depth": "basic_ffmpeg",
                "features": {
                    "has_audio": True,
                    "mean_dbfs": -25.0,
                    "peak_dbfs": -4.0,
                    "tempo_bpm": 96.0,
                    "beat_times": [0.5, 1.0],
                    "energy_curve": [{"start_sec": 0.0, "end_sec": 10.0, "relative_energy": 0.2}],
                    "vocal_analysis": {"has_vocals": True, "segments": [{"start_sec": 10.0, "end_sec": 15.0}]},
                },
                "sections": [{"start_sec": 0.0, "end_sec": 30.0, "role": "opening"}],
                "sampling_anchors": {"beat_times": [0.5], "speech_starts": [10.0]},
            }), encoding="utf-8")
            srt = root / "subtitles.srt"
            srt.write_text(
                "1\n00:00:10,000 --> 00:00:12,000\nFirst line\n\n"
                "2\n00:00:30,000 --> 00:00:33,500\nSecond line\n",
                encoding="utf-8",
            )

            packet = build_timeline_review_packet(
                video,
                root / "review",
                review_subject_type="current_candidate",
                duration_sec=61.0,
                wall_renderer=self._fake_renderer,
                soundtrack_probe_path=probe,
                srt_path=srt,
                text_authority="owner_approved",
            )

            self.assertEqual(packet["artifact_role"], "timeline_review_packet")
            self.assertEqual(packet["status"], "ready_for_agent_review")
            self.assertEqual(packet["review_subject"]["type"], "current_candidate")
            self.assertEqual(packet["reviewer_contract"]["authority"], "candidate_findings_only")
            self.assertEqual(packet["uniform_timeline_wall"]["sample_count"], 122)
            self.assertEqual(packet["uniform_timeline_wall"]["page_count"], 3)
            index = json.loads((root / "review" / "wall_index.json").read_text(encoding="utf-8"))
            self.assertEqual([wall["sample_count"] for wall in index["walls"]], [60, 60, 2])
            self.assertEqual(index["walls"][-1]["last_sample_sec"], 60.5)
            self.assertEqual(packet["review_tracks"]["audio"]["status"], "bound")
            self.assertEqual(packet["review_tracks"]["audio"]["beat_count"], 2)
            self.assertEqual(packet["review_tracks"]["audio"]["duration_binding"]["status"], "match")
            self.assertEqual(packet["review_tracks"]["audio"]["audio_stream_fingerprint"]["status"], "unbound")
            self.assertEqual(
                packet["review_tracks"]["audio"]["audio_probe_artifact_fingerprint"]["sha256"],
                packet["review_tracks"]["audio"]["sha256"],
            )
            self.assertEqual(packet["review_tracks"]["subtitles"]["cue_count"], 2)
            self.assertEqual(packet["review_tracks"]["subtitles"]["text_authority"], "owner_approved")
            self.assertEqual(packet["review_tracks"]["subtitles"]["cues"][1]["text"], "Second line")
            self.assertEqual(packet["evidence_manifest"]["artifact_role"], "editorial_evidence_manifest")
            self.assertEqual(packet["evidence_manifest"]["subject"]["sha256"], packet["source"]["sha256"])
            self.assertTrue((root / "review" / "editorial_evidence_manifest.json").is_file())
            self.assertIn("timeline_wall_index", {
                item["evidence_id"] for item in packet["evidence_manifest"]["evidence_items"]
            })
            self.assertEqual(
                packet["reviewer_contract"]["visible_evidence_precedence"][0],
                "rendered_pixels_over_declared_metadata_for_visible_content",
            )
            questions = "\n".join(packet["reviewer_contract"]["questions"])
            self.assertIn("adjacent shots", questions)
            self.assertIn("rendered pixels contradict", questions)
            findings_template = json.loads(
                (root / "review" / "editorial_review.template.json").read_text(encoding="utf-8")
            )
            self.assertEqual(findings_template["packet_sha256"], packet["packet_sha256"])
            self.assertEqual(findings_template["artifact_role"], "editorial_review")
            self.assertEqual(findings_template["status"], "ready_for_owner_verdict")
            self.assertEqual(findings_template["reviewer_identity"], "editorial_reviewer")
            self.assertEqual(findings_template["binding_contract_version"], 1)
            self.assertEqual(
                findings_template["reviewed_subject_sha256"],
                packet["subject"]["sha256"],
            )
            self.assertEqual(
                findings_template["applies_to_candidate_sha256"],
                findings_template["reviewed_subject_sha256"],
            )
            self.assertEqual(findings_template["subject_hash_method"], "sha256_file_bytes_v1")
            self.assertTrue((root / "review" / "reviewer_write_contract.json").is_file())

    def test_audio_binding_requires_exact_probe_source_hash(self):
        from video_pipeline_core.timeline_review_packet import _sha256, build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "candidate.mp4"
            video.write_bytes(b"candidate")
            candidate_sha = _sha256(video)

            def write_probe(path, source_binding=None):
                payload = {
                    "artifact_role": "soundtrack_probe_report",
                    "pass": True,
                    "duration_sec": 4.0,
                    "analysis_depth": "basic_ffmpeg",
                    "features": {"has_audio": True, "beat_times": []},
                }
                if source_binding is not None:
                    payload["source_binding"] = source_binding
                path.write_text(json.dumps(payload), encoding="utf-8")

            legacy_probe = root / "legacy_probe.json"
            write_probe(legacy_probe)
            legacy_packet = build_timeline_review_packet(
                video,
                root / "legacy_review",
                review_subject_type="current_candidate",
                duration_sec=4.0,
                wall_renderer=self._fake_renderer,
                soundtrack_probe_path=legacy_probe,
            )
            self.assertEqual(
                legacy_packet["review_tracks"]["audio"]["candidate_binding_status"],
                "unbound_probe_source_binding_missing",
            )

            mismatch_probe = root / "mismatch_probe.json"
            write_probe(mismatch_probe, {
                "path": str(video),
                "sha256": "f" * 64,
                "hash_method": "sha256_file_bytes_v1",
            })
            mismatch_packet = build_timeline_review_packet(
                video,
                root / "mismatch_review",
                review_subject_type="current_candidate",
                duration_sec=4.0,
                wall_renderer=self._fake_renderer,
                soundtrack_probe_path=mismatch_probe,
            )
            self.assertEqual(
                mismatch_packet["review_tracks"]["audio"]["candidate_binding_status"],
                "unbound_probe_source_mismatch",
            )

            exact_probe = root / "exact_probe.json"
            write_probe(exact_probe, {
                "path": str(video),
                "sha256": candidate_sha,
                "hash_method": "sha256_file_bytes_v1",
            })
            exact_packet = build_timeline_review_packet(
                video,
                root / "exact_review",
                review_subject_type="current_candidate",
                duration_sec=4.0,
                wall_renderer=self._fake_renderer,
                soundtrack_probe_path=exact_probe,
            )
            self.assertEqual(
                exact_packet["review_tracks"]["audio"]["candidate_binding_status"],
                "bound_exact_candidate",
            )
            self.assertEqual(exact_packet["source"]["hash_method"], "sha256_file_bytes_v1")
            self.assertEqual(exact_packet["subject"]["hash_method"], "sha256_file_bytes_v1")
            self.assertEqual(
                exact_packet["evidence_manifest"]["subject"]["hash_method"],
                "sha256_file_bytes_v1",
            )
            self.assertIn(
                "bound_exact_candidate",
                json.dumps(exact_packet["reviewer_contract"]),
            )

    def test_duration_match_alone_does_not_bind_audio(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "candidate.mp4"
            video.write_bytes(b"candidate")
            probe = root / "duration_only_probe.json"
            probe.write_text(json.dumps({
                "artifact_role": "soundtrack_probe_report",
                "pass": True,
                "duration_sec": 4.0,
                "features": {"has_audio": True, "beat_times": [1.0]},
            }), encoding="utf-8")
            packet = build_timeline_review_packet(
                video,
                root / "review",
                review_subject_type="current_candidate",
                duration_sec=4.0,
                wall_renderer=self._fake_renderer,
                soundtrack_probe_path=probe,
            )

        self.assertEqual(packet["review_tracks"]["audio"]["duration_binding"]["status"], "match")
        self.assertEqual(
            packet["review_tracks"]["audio"]["candidate_binding_status"],
            "unbound_probe_source_binding_missing",
        )

    def test_optional_tracks_remain_explicitly_unbound(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "silent.mp4"
            video.write_bytes(b"candidate")
            packet = build_timeline_review_packet(
                video,
                root / "review",
                review_subject_type="current_candidate",
                duration_sec=4.0,
                wall_renderer=self._fake_renderer,
            )
            self.assertEqual(packet["review_tracks"]["audio"]["status"], "not_supplied")
            self.assertEqual(
                packet["review_tracks"]["audio"]["candidate_binding_status"],
                "unbound_not_supplied",
            )
            self.assertEqual(packet["review_tracks"]["audio"]["audio_stream_fingerprint"]["status"], "unbound")
            self.assertEqual(packet["review_tracks"]["subtitles"]["status"], "not_supplied")
            self.assertTrue(packet["uniform_timeline_wall"]["coverage_pass"])

    def test_rejects_wrong_audio_artifact_and_existing_wall_outputs(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "candidate.mp4"
            video.write_bytes(b"candidate")
            bad_probe = root / "bad.json"
            bad_probe.write_text(json.dumps({"artifact_role": "not_a_probe"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "soundtrack_probe_contract_mismatch"):
                build_timeline_review_packet(
                    video,
                    root / "review_bad",
                    review_subject_type="current_candidate",
                    duration_sec=4.0,
                    wall_renderer=self._fake_renderer,
                    soundtrack_probe_path=bad_probe,
                )
            self.assertFalse((root / "review_bad").exists())

            wrong_duration_probe = root / "wrong_duration.json"
            wrong_duration_probe.write_text(json.dumps({
                "artifact_role": "soundtrack_probe_report",
                "duration_sec": 18.0,
                "features": {},
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "soundtrack_probe_duration_mismatch"):
                build_timeline_review_packet(
                    video,
                    root / "review_wrong_duration",
                    review_subject_type="current_candidate",
                    duration_sec=4.0,
                    wall_renderer=self._fake_renderer,
                    soundtrack_probe_path=wrong_duration_probe,
                )
            self.assertFalse((root / "review_wrong_duration").exists())

            occupied = root / "occupied"
            (occupied / "walls").mkdir(parents=True)
            (occupied / "walls" / "wall_30s_01.jpg").write_bytes(b"old")
            with self.assertRaisesRegex(FileExistsError, "timeline_review_output_exists"):
                build_timeline_review_packet(
                    video,
                    occupied,
                    review_subject_type="current_candidate",
                    duration_sec=4.0,
                    wall_renderer=self._fake_renderer,
                )

    def test_reference_film_is_non_blocking_and_effects_remain_observations(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "reference.mp4"
            video.write_bytes(b"reference")
            packet = build_timeline_review_packet(
                video,
                root / "review",
                review_subject_type="reference_film",
                duration_sec=4.0,
                wall_renderer=self._fake_renderer,
            )
            self.assertEqual(packet["review_subject"]["type"], "reference_film")
            self.assertEqual(packet["review_subject"]["decision_effect"], "non_blocking_reference")
            self.assertEqual(packet["reviewer_contract"]["authority"], "reference_observations_only")
            self.assertFalse(packet["reviewer_contract"]["effect_boundary"]["effect_factory_handoff_allowed"])
            self.assertIn(
                "evidence_refs",
                packet["reviewer_contract"]["effect_boundary"]["observation_schema"],
            )
            findings = json.loads(
                (root / "review" / "editorial_review.template.json").read_text(encoding="utf-8")
            )
            self.assertEqual(findings["review_subject"]["type"], "reference_film")
            self.assertEqual(findings["reviewer_identity"], "editorial_reviewer")
            self.assertEqual(findings["findings"], [])

    def test_srt_requires_explicit_text_authority(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "candidate.mp4"
            video.write_bytes(b"candidate")
            srt = root / "subtitles.srt"
            srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nDraft\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "timeline_review_text_authority_required"):
                build_timeline_review_packet(
                    video,
                    root / "missing_authority",
                    review_subject_type="current_candidate",
                    duration_sec=4.0,
                    wall_renderer=self._fake_renderer,
                    srt_path=srt,
                )
            self.assertFalse((root / "missing_authority").exists())
            with self.assertRaisesRegex(ValueError, "timeline_review_text_authority_without_srt"):
                build_timeline_review_packet(
                    video,
                    root / "authority_without_srt",
                    review_subject_type="current_candidate",
                    text_authority="asr_draft",
                    duration_sec=4.0,
                    wall_renderer=self._fake_renderer,
                )
            self.assertFalse((root / "authority_without_srt").exists())

    def test_rejects_unknown_review_subject_type(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "candidate.mp4"
            video.write_bytes(b"candidate")
            with self.assertRaisesRegex(ValueError, "timeline_review_subject_type_invalid"):
                build_timeline_review_packet(
                    video,
                    root / "review",
                    review_subject_type="delivery_candidate",
                    duration_sec=4.0,
                    wall_renderer=self._fake_renderer,
                )

    def test_evidence_reuse_plans_audio_and_subtitle_deltas(self):
        from video_pipeline_core.timeline_review_packet import plan_evidence_reuse

        def manifest(audio, subtitle, subject_sha="a" * 64):
            return {
                "artifact_role": "editorial_evidence_manifest",
                "version": 1,
                "subject": {
                    "path": "candidate.mp4",
                    "artifact_role": "timeline_review_subject",
                    "sha256": subject_sha,
                    "duration_sec": 60.0,
                    "media_role": "current_candidate",
                },
                "picture_stream_fingerprint": {"status": "bound", "sha256": "b" * 64},
                "audio_stream_fingerprint": {"status": "bound", "sha256": audio},
                "subtitle_fingerprint": {"status": "bound", "sha256": subtitle},
                "evidence_items": [
                    {"evidence_id": "timeline_wall_index", "kind": "wall_index", "covered_timeline_window": [0, 60]},
                    {"evidence_id": "wall_1", "kind": "timeline_wall", "covered_timeline_window": [0, 30]},
                    {"evidence_id": "wall_2", "kind": "timeline_wall", "covered_timeline_window": [30, 60]},
                    {"evidence_id": "soundtrack_probe", "kind": "audio_probe", "covered_timeline_window": [0, 60]},
                    {"evidence_id": "subtitle_binding", "kind": "subtitle_binding", "covered_timeline_window": [0, 60]},
                ],
            }

        previous = manifest("c" * 64, "d" * 64)
        audio_changed = manifest("e" * 64, "d" * 64, "1" * 64)
        audio_plan = plan_evidence_reuse(previous, audio_changed)
        self.assertEqual(audio_plan["reason"], "identical_picture_audio_only_change")
        self.assertIn("wall_1", audio_plan["reused_evidence_ids"])
        self.assertIn("soundtrack_probe", audio_plan["regenerated_evidence_ids"])

        subtitle_changed = manifest("c" * 64, "f" * 64, "2" * 64)
        subtitle_plan = plan_evidence_reuse(previous, subtitle_changed)
        self.assertEqual(subtitle_plan["reason"], "identical_picture_audio_subtitle_only_change")
        self.assertIn("soundtrack_probe", subtitle_plan["reused_evidence_ids"])
        self.assertIn("subtitle_binding", subtitle_plan["regenerated_evidence_ids"])

        combined_changed = manifest("e" * 64, "f" * 64, "3" * 64)
        combined_plan = plan_evidence_reuse(previous, combined_changed)
        self.assertEqual(combined_plan["reason"], "identical_picture_audio_and_subtitle_change")
        self.assertIn("soundtrack_probe", combined_plan["regenerated_evidence_ids"])
        self.assertIn("subtitle_binding", combined_plan["regenerated_evidence_ids"])

    def test_evidence_reuse_invalidates_only_intersecting_picture_wall(self):
        from video_pipeline_core.timeline_review_packet import plan_evidence_reuse

        def manifest(picture, subject_sha):
            return {
                "artifact_role": "editorial_evidence_manifest",
                "version": 1,
                "subject": {
                    "path": "candidate.mp4",
                    "artifact_role": "timeline_review_subject",
                    "sha256": subject_sha,
                    "duration_sec": 60.0,
                    "media_role": "current_candidate",
                },
                "picture_stream_fingerprint": {"status": "bound", "sha256": picture},
                "audio_stream_fingerprint": {"status": "bound", "sha256": "c" * 64},
                "subtitle_fingerprint": {"status": "bound", "sha256": "d" * 64},
                "evidence_items": [
                    {"evidence_id": "timeline_wall_index", "kind": "wall_index", "covered_timeline_window": [0, 60]},
                    {"evidence_id": "wall_1", "kind": "timeline_wall", "covered_timeline_window": [0, 30]},
                    {"evidence_id": "wall_2", "kind": "timeline_wall", "covered_timeline_window": [30, 60]},
                ],
            }

        plan = plan_evidence_reuse(
            manifest("b" * 64, "a" * 64),
            manifest("c" * 64, "3" * 64),
            changed_picture_window={"start_sec": 35.0, "end_sec": 40.0},
        )
        self.assertIn("wall_1", plan["reused_evidence_ids"])
        self.assertIn("wall_2", plan["invalidated_evidence_ids"])
        self.assertIn("wall_2", plan["regenerated_evidence_ids"])
        self.assertIn("timeline_wall_index", plan["invalidated_evidence_ids"])
        self.assertIn("timeline_wall_index", plan["regenerated_evidence_ids"])

    def test_evidence_reuse_fails_closed_for_unknown_picture_fingerprint(self):
        from video_pipeline_core.timeline_review_packet import plan_evidence_reuse

        manifest = {
            "artifact_role": "editorial_evidence_manifest",
            "version": 1,
            "subject": {"path": "candidate.mp4", "artifact_role": "timeline_review_subject", "sha256": "a" * 64, "duration_sec": 1.0, "media_role": "current_candidate"},
            "picture_stream_fingerprint": {"status": "unbound", "reason": "not_probed"},
            "evidence_items": [],
        }
        with self.assertRaisesRegex(ValueError, "picture_fingerprint_unknown"):
            plan_evidence_reuse(manifest, manifest)

    def test_evidence_reuse_fails_closed_for_unknown_audio_stream_fingerprint(self):
        from video_pipeline_core.timeline_review_packet import plan_evidence_reuse

        manifest = {
            "artifact_role": "editorial_evidence_manifest",
            "version": 1,
            "subject": {
                "path": "candidate.mp4",
                "artifact_role": "timeline_review_subject",
                "sha256": "a" * 64,
                "duration_sec": 1.0,
                "media_role": "current_candidate",
            },
            "picture_stream_fingerprint": {"status": "bound", "sha256": "b" * 64},
            "audio_stream_fingerprint": {"status": "unbound", "reason": "probe_json_is_not_stream"},
            "evidence_items": [
                {"evidence_id": "wall_1", "kind": "timeline_wall", "covered_timeline_window": [0, 1]},
                {"evidence_id": "soundtrack_probe", "kind": "audio_probe", "covered_timeline_window": [0, 1]},
            ],
        }
        with self.assertRaisesRegex(ValueError, "audio_fingerprint_unknown"):
            plan_evidence_reuse(manifest, manifest)

    def test_binds_real_shape_context_and_generates_live_write_contract(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "candidate.mp4"
            video.write_bytes(b"candidate")
            from video_pipeline_core.timeline_review_packet import _sha256

            video_sha256 = _sha256(video)
            context = root / "capcut_finishing_handoff.json"
            context.write_text(json.dumps({
                "artifact_role": "capcut_brownfield_finishing_handoff",
                "version": 1,
                "input": {"path": str(video), "sha256": video_sha256},
                "locked_truth": {
                    "story": True,
                    "allow_recut": False,
                    "approved_subtitles": True,
                },
                "finishing_contract": {"free_only": True},
                "audio_policy": {"preserve_embedded_verified_mix": True},
                "ignored_context_field": "must_not_be_copied",
            }), encoding="utf-8")
            packet = build_timeline_review_packet(
                video,
                root / "review",
                review_subject_type="current_candidate",
                duration_sec=4.0,
                wall_renderer=self._fake_renderer,
                context_path=context,
            )
            decision_context = packet["decision_context"]
            self.assertEqual(decision_context["status"], "bound")
            self.assertEqual(decision_context["locked_truth"]["allow_recut"], False)
            self.assertEqual(decision_context["source"]["path"], str(context))
            self.assertEqual(decision_context["source"]["artifact_role"], "capcut_brownfield_finishing_handoff")
            self.assertEqual(decision_context["source"]["sha256"], packet["decision_context_ref"]["sha256"])
            self.assertEqual(decision_context["subject_binding"]["status"], "verified")
            self.assertEqual(decision_context["subject_binding"]["subject_sha256"], video_sha256)
            self.assertEqual(decision_context["subject_binding"]["source_field"], "input.sha256")
            self.assertNotIn("ignored_context_field", decision_context)
            contract_path = root / "review" / "reviewer_write_contract.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            self.assertIn("full_context", contract["allowed_enums"]["review_modes"])
            self.assertIn("no_existing_route", contract["allowed_enums"]["routes"])
            self.assertIn(
                "cap.editorial-reviewer.structured-review-validation.v1",
                contract["routing_capability_ids"],
            )

    def test_rejects_decision_context_bound_to_a_different_subject(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "candidate.mp4"
            video.write_bytes(b"candidate")
            context = root / "unrelated_context.json"
            context.write_text(json.dumps({
                "artifact_role": "capcut_brownfield_finishing_handoff",
                "input": {"path": "other.mp4", "sha256": "a" * 64},
                "locked_truth": {"allow_recut": False},
            }), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "timeline_review_context_subject_mismatch"):
                build_timeline_review_packet(
                    video,
                    root / "review",
                    review_subject_type="current_candidate",
                    duration_sec=4.0,
                    wall_renderer=self._fake_renderer,
                    context_path=context,
                )
            self.assertFalse((root / "review").exists())

    def test_rejects_decision_context_without_subject_binding(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "candidate.mp4"
            video.write_bytes(b"candidate")
            context = root / "unbound_context.json"
            context.write_text(json.dumps({
                "artifact_role": "capcut_brownfield_finishing_handoff",
                "locked_truth": {"allow_recut": False},
            }), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "timeline_review_context_subject_binding_missing"):
                build_timeline_review_packet(
                    video,
                    root / "review",
                    review_subject_type="current_candidate",
                    duration_sec=4.0,
                    wall_renderer=self._fake_renderer,
                    context_path=context,
                )
            self.assertFalse((root / "review").exists())

    def test_generated_editorial_template_passes_public_validator(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "candidate.mp4"
            video.write_bytes(b"candidate")
            build_timeline_review_packet(
                video,
                root / "review",
                review_subject_type="current_candidate",
                duration_sec=4.0,
                wall_renderer=self._fake_renderer,
            )
            template = root / "review" / "editorial_review.template.json"
            proc = subprocess.run(
                [sys.executable, "video_tools.py", "reviewer-policy", "--validate-review", str(template)],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_real_renderer_writes_one_uniform_wall_for_short_video(self):
        try:
            from video_pipeline_core.platform_tools import resolve_ffmpeg
            ffmpeg = resolve_ffmpeg()
        except Exception:
            self.skipTest("ffmpeg not available")
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "fixture.mp4"
            subprocess.run(
                [
                    ffmpeg, "-y", "-f", "lavfi", "-i",
                    "testsrc=duration=4:size=320x180:rate=12",
                    "-pix_fmt", "yuv420p", str(video),
                ],
                capture_output=True,
                check=True,
            )
            packet = build_timeline_review_packet(
                video,
                root / "review",
                review_subject_type="current_candidate",
            )
            self.assertEqual(packet["uniform_timeline_wall"]["sample_count"], 8)
            self.assertEqual(packet["uniform_timeline_wall"]["page_count"], 1)
            wall = root / "review" / "walls" / "wall_30s_01.jpg"
            self.assertTrue(wall.is_file())
            self.assertGreater(wall.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
