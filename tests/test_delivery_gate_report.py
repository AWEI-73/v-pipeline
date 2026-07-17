import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class DeliveryGateReportCliTest(unittest.TestCase):
    def test_external_temp_run_does_not_invoke_repo_strict_resolver(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            _write(run / "video_intent.json", {"artifact_role": "video_intent", "entry_path": "material-first"})
            with patch(
                "tools.write_delivery_gate_report.resolve_strict_contract",
                side_effect=AssertionError("external temp root must use legacy delivery behavior"),
            ):
                from tools.write_delivery_gate_report import write_delivery_gate_report
                gate = write_delivery_gate_report(run)

            self.assertFalse(gate["pass"])
            self.assertTrue((run / "delivery_gate.json").is_file())

    def test_complete_delivery_run_uses_complete_video_gate_not_dashboard_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            _write(run / "delivery_requirements.json", {
                "requires_audio": True,
                "requires_music": True,
                "requires_soundtrack_probe": True,
            })
            (run / "final.mp4").write_bytes(b"placeholder")
            _write(run / "delivery_gate.json", {
                "artifact_role": "delivery_gate",
                "version": 1,
                "pass": True,
                "blocking": [],
                "next_action": None,
            })

            complete_gate = {
                "artifact_role": "complete_video_delivery_gate",
                "version": 1,
                "pass": False,
                "blocking": [{
                    "rule": "soundtrack_probe_has_no_section_fit",
                    "artifact": "soundtrack_probe_report.json",
                    "next_action": "rerun_soundtrack_probe",
                }],
                "next_action": "rerun_soundtrack_probe",
            }
            with patch("tools.write_delivery_gate_report.evaluate_complete_video_delivery", return_value=complete_gate) as mocked:
                from tools.write_delivery_gate_report import write_delivery_gate_report
                gate = write_delivery_gate_report(run)

            mocked.assert_called_once_with(run)
            self.assertFalse(gate["pass"])
            self.assertEqual(gate["report_source"], "complete_video_delivery_gate")
            self.assertEqual(gate["next_action"], "rerun_soundtrack_probe")
            self.assertEqual(gate["blocking"][0]["rule"], "soundtrack_probe_has_no_section_fit")

    def test_writes_delivery_gate_json_even_when_verify_result_passes(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            _write(run / "brief.json", {"title": "material mismatch fixture"})
            _write(run / "verify_result.json", {"pass": True})
            _write(run / "material_coverage_map.json", {"coverage": []})
            _write(run / "segment_contract.json", {
                "segments": [{
                    "segment": 2,
                    "material_map_ids": ["commute_001"],
                    "need_refs": ["need_commute_motion"],
                }],
            })
            _write(run / "project_material_map.json", {
                "assets": [
                    {
                        "asset_id": "city_dawn_001",
                        "scenes": [{
                            "scene_id": "city_dawn_001:0",
                            "satisfies": ["need_city_dawn"],
                        }],
                    },
                ],
            })
            _write(run / "timeline_build.json", {
                "clips": [{
                    "segment": 2,
                    "scene_id": "city_dawn_001:0",
                    "source_path": "city_dawn.mp4",
                }],
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/write_delivery_gate_report.py",
                    "--run",
                    str(run),
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertFalse(summary["pass"])
            self.assertEqual(summary["next_action"], "revise_material_selection_or_review")

            gate = json.loads((run / "delivery_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(gate["pass"])
            self.assertEqual(gate["generated_by"], "tools/write_delivery_gate_report.py")
            self.assertEqual(gate["report_source"], "dashboard_state.artifacts.delivery_gate")
            self.assertTrue(any(
                item.get("rule") == "timeline_need_ref_mismatch"
                for item in gate.get("blocking", [])
            ))
            self.assertEqual(
                json.loads((run / "verify_result.json").read_text(encoding="utf-8")),
                {"pass": True},
            )

    def test_dashboard_gate_pass_without_video_candidate_fails_closed(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            _write(run / "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "material-first",
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/write_delivery_gate_report.py",
                    "--run",
                    str(run),
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertFalse(summary["pass"])
            self.assertEqual(summary["next_action"], "create_or_verify_video_candidate")
            self.assertTrue(any(
                item.get("rule") == "missing_video_candidate"
                for item in summary.get("blocking", [])
            ))

    def test_dashboard_gate_applies_video_only_waiver_to_soundtrack_blocks(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            preview = run / "rough_cut_preview.mp4"
            preview.write_bytes(b"preview")
            _write(run / "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "material-first",
                "target_length": "60-90 seconds preview first",
            })
            _write(run / "rough_cut_preview_report.json", {
                "artifact_role": "rough_cut_preview_report",
                "ok": True,
                "output_video": str(preview),
                "duration_sec": 64.0,
            })
            _write(run / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": True,
                "video": str(preview),
            })
            _write(run / "sound_license_manifest.json", {
                "artifact_role": "sound_license_manifest",
                "delivery_allowed": False,
                "blocks": ["license_missing"],
            })
            _write(run / "video_only_delivery_waiver.json", {
                "artifact_role": "video_only_delivery_waiver",
                "version": 1,
                "scope": "video_only_delivery",
                "reviewer": "operator",
                "reason": "reviewed picture-only handoff",
                "at": "2026-07-05T00:00:00+08:00",
                "waives": ["soundtrack_license", "music", "audio"],
                "limitations": ["Video-only handoff; no deliverable soundtrack."],
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/write_delivery_gate_report.py",
                    "--run",
                    str(run),
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertTrue(summary["pass"], summary)
            self.assertEqual(summary["generated_by"], "tools/write_delivery_gate_report.py")
            self.assertEqual(summary["report_source"], "dashboard_state.artifacts.delivery_gate")
            self.assertTrue(summary["waivers_applied"])
            self.assertTrue(summary["limitations"])

    def test_dashboard_gate_reads_utf8_sig_video_only_waiver(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            preview = run / "rough_cut_preview.mp4"
            preview.write_bytes(b"preview")
            _write(run / "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "material-first",
            })
            _write(run / "rough_cut_preview_report.json", {
                "artifact_role": "rough_cut_preview_report",
                "ok": True,
                "output_video": str(preview),
                "duration_sec": 64.0,
            })
            _write(run / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": True,
                "video": str(preview),
            })
            waiver = {
                "artifact_role": "video_only_delivery_waiver",
                "version": 1,
                "scope": "video_only_delivery",
                "reviewer": "operator",
                "reason": "PowerShell-authored waiver",
                "at": "2026-07-05T00:00:00+08:00",
                "waives": ["audio"],
                "limitations": ["Video-only handoff; no deliverable audio."],
            }
            (run / "video_only_delivery_waiver.json").write_bytes(
                ("\ufeff" + json.dumps(waiver, ensure_ascii=False)).encode("utf-8")
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/write_delivery_gate_report.py",
                    "--run",
                    str(run),
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertTrue(summary["waivers_applied"])
            self.assertTrue(summary["limitations"])

    def test_dashboard_gate_keeps_missing_video_candidate_block_with_waiver(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            _write(run / "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "material-first",
            })
            _write(run / "video_only_delivery_waiver.json", {
                "artifact_role": "video_only_delivery_waiver",
                "version": 1,
                "scope": "video_only_delivery",
                "reviewer": "operator",
                "reason": "reviewed picture-only handoff",
                "at": "2026-07-05T00:00:00+08:00",
                "waives": ["audio", "music", "soundtrack_license"],
                "limitations": ["Video-only handoff; no deliverable soundtrack."],
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/write_delivery_gate_report.py",
                    "--run",
                    str(run),
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertFalse(summary["pass"])
            self.assertTrue(any(item.get("rule") == "missing_video_candidate" for item in summary["blocking"]))

    def test_rough_cut_preview_candidate_satisfies_dashboard_video_candidate_gate(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            preview = run / "rough_cut_preview.mp4"
            preview.write_bytes(b"preview")
            _write(run / "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "material-first",
            })
            _write(run / "rough_cut_preview_report.json", {
                "artifact_role": "rough_cut_preview_report",
                "ok": True,
                "output_video": str(preview),
                "next_action": "human_review_or_final_product_verify",
            })
            _write(run / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": True,
                "video": str(preview),
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/write_delivery_gate_report.py",
                    "--run",
                    str(run),
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertTrue(summary["pass"])
            self.assertFalse(any(
                item.get("rule") == "missing_video_candidate"
                for item in summary.get("blocking", [])
            ))

    def test_rough_cut_preview_shorter_than_stage0_target_fails_closed(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            preview = run / "rough_cut_preview.mp4"
            preview.write_bytes(b"preview")
            _write(run / "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "material-first",
                "target_length": "60-90 seconds preview first",
            })
            _write(run / "rough_cut_preview_report.json", {
                "artifact_role": "rough_cut_preview_report",
                "ok": True,
                "output_video": str(preview),
                "duration_sec": 12.0,
            })
            _write(run / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": True,
                "video": str(preview),
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/write_delivery_gate_report.py",
                    "--run",
                    str(run),
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertFalse(summary["pass"])
            self.assertEqual(summary["next_action"], "extend_or_rebuild_preview_to_target_length")
            self.assertTrue(any(
                item.get("rule") == "preview_duration_below_stage0_target"
                for item in summary.get("blocking", [])
            ))

    def test_storyboard_preview_candidate_can_satisfy_stage0_target(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            preview = run / "rough_cut_storyboard_preview.mp4"
            preview.write_bytes(b"preview")
            _write(run / "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "material-first",
                "target_length": "60-90 seconds preview first",
            })
            _write(run / "rough_cut_storyboard_preview_report.json", {
                "artifact_role": "rough_cut_storyboard_preview_report",
                "ok": True,
                "output_video": str(preview),
                "output_probe": {"format": {"duration": "64.0"}},
            })
            _write(run / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": True,
                "video": str(preview),
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/write_delivery_gate_report.py",
                    "--run",
                    str(run),
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertTrue(summary["pass"])
            self.assertFalse(summary.get("blocking"))

    def test_utf16_json_sidecar_does_not_break_candidate_scan(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            preview = run / "verified_preview.mp4"
            preview.write_bytes(b"preview")
            _write(run / "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "material-first",
            })
            _write(run / "highlight_cut_report.json", {
                "artifact_role": "highlight_cut_report",
                "ok": True,
                "out": str(preview),
                "duration_sec": 20.0,
            })
            _write(run / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": True,
                "video": str(preview),
            })
            (run / "pipeline_home.json").write_text(
                json.dumps({"mode": "run"}, ensure_ascii=False),
                encoding="utf-16",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/write_delivery_gate_report.py",
                    "--run",
                    str(run),
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertTrue(summary["pass"])


if __name__ == "__main__":
    unittest.main()
