import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.material_first_landing_case import run_material_first_landing_case
from video_pipeline_core.asset_paths import is_absolute_path_string
from video_pipeline_core.platform_tools import resolve_ffmpeg


def _jpg(path: Path, color: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (80, 45), color=color).save(path, "JPEG")


def _mp4(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            resolve_ffmpeg(),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=80x48:rate=24:duration=2",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)


def _write_verdict(path: Path, *, asset_count: int = 3) -> None:
    roles = ["opening", "training", "closing"]
    assets = []
    for index in range(asset_count):
        asset_id = f"real_{index + 1:04d}"
        if index < 3:
            role = roles[index]
            assets.append({
                "asset_id": asset_id,
                "coarse_status": "keep",
                "visual_role": [role],
                "quality": "good",
                "usable_ranges": [{"start": 0.0, "end": 4.0}],
                "visual_evidence": [f"{role} evidence"],
            })
        else:
            assets.append({
                "asset_id": asset_id,
                "coarse_status": "reject",
                "visual_role": [],
                "quality": "bad",
                "why_not_selected": "bounded fixture extra",
            })
    path.write_text(json.dumps({
        "artifact_role": "material_wall_review_verdict",
        "version": 1,
        "reviewer": "test:review-promotion",
        "assets": assets,
    }), encoding="utf-8")


def _source_fixture(root: Path) -> tuple[Path, Path, Path]:
    source = root / "external_source"
    _jpg(source / "opening" / "opening.jpg", "red")
    _jpg(source / "training" / "training.jpg", "green")
    _jpg(source / "closing" / "closing.jpg", "blue")
    _jpg(source / "extra" / "unused.jpg", "yellow")
    (source / "extra" / "corrupt.mp4").write_bytes(b"not a real mp4")
    verdict = root / "material_wall_review_verdict.json"
    _write_verdict(verdict, asset_count=4)
    run_dir = root / "run"
    result = run_material_first_landing_case(
        run_dir,
        source_dir=source,
        wall_verdict=verdict,
        max_assets=4,
    )
    if not result["ok"]:
        raise AssertionError(result)
    return source, verdict, run_dir


class MaterialFirstReviewPromotionTest(unittest.TestCase):
    def test_review_packet_lists_run_relative_assets_without_external_paths(self):
        from video_pipeline_core.material_first_review_promotion import build_material_first_review_packet

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, _verdict, run_dir = _source_fixture(root)

            packet = build_material_first_review_packet(run_dir)

            packet_path = run_dir / "material_review_packet.json"
            self.assertTrue(packet_path.exists())
            self.assertEqual(packet["artifact_role"], "material_review_packet")
            self.assertEqual(packet["next_action"], "await_material_wall_review")
            self.assertEqual(len(packet["accepted_candidate_assets"]), 3)
            for asset in packet["accepted_candidate_assets"]:
                self.assertTrue(asset["asset_ref"].startswith("assets/materials/"))
                self.assertFalse(is_absolute_path_string(asset["asset_ref"]))
                self.assertIn("source_path_hash", asset["original_source"])
                self.assertIn("basename", asset["original_source"])
                self.assertTrue(asset["role_hints"])
            self.assertTrue(packet["rejected_corrupt_or_skipped"])
            self.assertIn("material_wall_review_verdict", packet["verdict_instructions"]["write_artifact"])
            self.assertNotIn(str(source), json.dumps(packet, ensure_ascii=False))

    def test_accept_review_verdict_writes_promotion_report(self):
        from video_pipeline_core.material_first_review_promotion import (
            accept_material_first_review_verdict,
            build_material_first_review_packet,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _source, verdict, run_dir = _source_fixture(root)
            build_material_first_review_packet(run_dir)

            result = accept_material_first_review_verdict(run_dir, verdict)

            self.assertTrue(result["ok"], result)
            report_path = run_dir / "material_first_review_verdict_acceptance.json"
            self.assertTrue(report_path.exists())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["artifact_role"], "material_first_review_verdict_acceptance")
            self.assertEqual(report["accepted_asset_count"], 3)
            self.assertEqual(report["rejected_asset_count"], 1)
            self.assertEqual(report["decision_source"], "human_or_agent_review")
            accepted_verdict = json.loads((run_dir / "material_wall_review_verdict.json").read_text(encoding="utf-8"))
            self.assertEqual(accepted_verdict["reviewer"], "test:review-promotion")

    def test_accept_review_verdict_fails_closed_when_packet_asset_is_missing(self):
        from video_pipeline_core.material_first_review_promotion import (
            accept_material_first_review_verdict,
            build_material_first_review_packet,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _source, verdict, run_dir = _source_fixture(root)
            build_material_first_review_packet(run_dir)
            payload = json.loads(verdict.read_text(encoding="utf-8"))
            payload["assets"] = [asset for asset in payload["assets"] if asset["asset_id"] != "real_0002"]
            bad_verdict = root / "bad_verdict.json"
            bad_verdict.write_text(json.dumps(payload), encoding="utf-8")

            result = accept_material_first_review_verdict(run_dir, bad_verdict)

            self.assertFalse(result["ok"], result)
            self.assertEqual(result["next_action"], "blocked")
            self.assertEqual(result["blocking"][0]["rule"], "missing_review_decision")

    def test_render_promotion_gate_writes_ready_report_and_handoff(self):
        from video_pipeline_core.material_first_review_promotion import (
            accept_material_first_review_verdict,
            build_material_first_render_promotion,
            build_material_first_review_packet,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _source, verdict, run_dir = _source_fixture(root)
            build_material_first_review_packet(run_dir)
            accept_material_first_review_verdict(run_dir, verdict)

            report = build_material_first_render_promotion(run_dir)

            self.assertTrue(report["ok"], report)
            self.assertEqual(report["next_action"], "ready_for_render")
            self.assertFalse(report["final_delivery_claimed"])
            self.assertTrue((run_dir / "render_readiness_report.json").exists())
            self.assertTrue((run_dir / "render_handoff.json").exists())
            handoff = json.loads((run_dir / "render_handoff.json").read_text(encoding="utf-8"))
            self.assertEqual(handoff["artifact_role"], "render_handoff")
            self.assertEqual(handoff["next_action"], "ready_for_render")
            self.assertFalse(handoff["final_delivery_claimed"])
            self.assertEqual(len(handoff["timeline_refs"]), 3)
            self.assertTrue(all(ref["source_path"].startswith("assets/materials/") for ref in handoff["timeline_refs"]))

    def test_render_promotion_warns_for_non_render_critical_absolute_paths(self):
        from video_pipeline_core.material_first_review_promotion import (
            accept_material_first_review_verdict,
            build_material_first_render_promotion,
            build_material_first_review_packet,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _source, verdict, run_dir = _source_fixture(root)
            build_material_first_review_packet(run_dir)
            accept_material_first_review_verdict(run_dir, verdict)
            source_candidates = json.loads((run_dir / "materials_db.source_candidates.json").read_text(encoding="utf-8"))
            source_candidates["provenance_debug"] = {
                "original_absolute_source": str(root / "external_source" / "opening" / "opening.jpg"),
            }
            (run_dir / "materials_db.source_candidates.json").write_text(
                json.dumps(source_candidates),
                encoding="utf-8",
            )
            packet = json.loads((run_dir / "material_review_packet.json").read_text(encoding="utf-8"))
            packet["review_evidence_debug"] = str(root / "external_source" / "training" / "training.jpg")
            (run_dir / "material_review_packet.json").write_text(json.dumps(packet), encoding="utf-8")

            report = build_material_first_render_promotion(run_dir)

            self.assertTrue(report["ok"], report)
            self.assertTrue((run_dir / "render_handoff.json").exists())
            self.assertFalse((run_dir / "final.mp4").exists())
            warning_summary = report.get("asset_path_warning_summary") or {}
            self.assertGreaterEqual(warning_summary.get("finding_count", 0), 2)
            self.assertGreaterEqual(len(report.get("warnings") or []), 1)

    def test_render_promotion_blocks_external_absolute_timeline_source_path(self):
        from video_pipeline_core.material_first_review_promotion import (
            accept_material_first_review_verdict,
            build_material_first_render_promotion,
            build_material_first_review_packet,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _source, verdict, run_dir = _source_fixture(root)
            build_material_first_review_packet(run_dir)
            accept_material_first_review_verdict(run_dir, verdict)
            timeline = json.loads((run_dir / "timeline_build.json").read_text(encoding="utf-8"))
            timeline["clips"][0]["source_path"] = str(root / "external_source" / "opening" / "opening.jpg")
            (run_dir / "timeline_build.json").write_text(json.dumps(timeline), encoding="utf-8")

            report = build_material_first_render_promotion(run_dir)

            self.assertFalse(report["ok"], report)
            rules = {item["rule"] for item in report["blocking"]}
            self.assertIn("non_asset_store_ref", rules)
            self.assertFalse((run_dir / "render_handoff.json").exists())

    def test_render_promotion_blocks_external_absolute_rough_cut_source_path(self):
        from video_pipeline_core.material_first_review_promotion import (
            accept_material_first_review_verdict,
            build_material_first_render_promotion,
            build_material_first_review_packet,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _source, verdict, run_dir = _source_fixture(root)
            build_material_first_review_packet(run_dir)
            accept_material_first_review_verdict(run_dir, verdict)
            rough_cut = json.loads((run_dir / "rough_cut_plan.json").read_text(encoding="utf-8"))
            rough_cut["clips"][0]["source_path"] = str(root / "external_source" / "opening" / "opening.jpg")
            (run_dir / "rough_cut_plan.json").write_text(json.dumps(rough_cut), encoding="utf-8")

            report = build_material_first_render_promotion(run_dir)

            self.assertFalse(report["ok"], report)
            rules = {item["rule"] for item in report["blocking"]}
            self.assertIn("non_asset_store_ref", rules)
            self.assertFalse((run_dir / "render_handoff.json").exists())

    def test_render_promotion_gate_blocks_when_asset_store_file_is_missing(self):
        from video_pipeline_core.material_first_review_promotion import (
            accept_material_first_review_verdict,
            build_material_first_render_promotion,
            build_material_first_review_packet,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _source, verdict, run_dir = _source_fixture(root)
            build_material_first_review_packet(run_dir)
            accept_material_first_review_verdict(run_dir, verdict)
            (run_dir / "assets" / "materials" / "real_0002.jpg").unlink()

            report = build_material_first_render_promotion(run_dir)

            self.assertFalse(report["ok"], report)
            self.assertEqual(report["next_action"], "blocked")
            self.assertFalse((run_dir / "render_handoff.json").exists())
            self.assertEqual(report["blocking"][0]["rule"], "missing_asset_store_file")

    def test_render_handoff_execution_writes_final_mp4_from_run_local_refs(self):
        from video_pipeline_core.material_first_render import render_material_first_handoff
        from video_pipeline_core.material_first_review_promotion import (
            accept_material_first_review_verdict,
            build_material_first_render_promotion,
            build_material_first_review_packet,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, verdict, run_dir = _source_fixture(root)
            build_material_first_review_packet(run_dir)
            accept_material_first_review_verdict(run_dir, verdict)
            build_material_first_render_promotion(run_dir)

            result = render_material_first_handoff(run_dir)

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["next_action"], "ready_for_delivery_gate")
            self.assertEqual(result["final_mp4_ref"], "final.mp4")
            self.assertTrue((run_dir / "final.mp4").is_file())
            self.assertTrue((run_dir / "material_first_final_artifact_acceptance.json").is_file())
            self.assertGreaterEqual(result["ffprobe"]["video_stream_count"], 1)
            self.assertFalse(result["final_delivery_claimed"])
            self.assertNotIn(str(source), json.dumps(result, ensure_ascii=False))

    def test_render_handoff_execution_supports_run_local_video_refs_with_timing(self):
        from video_pipeline_core.material_first_render import render_material_first_handoff

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            video = run_dir / "assets" / "materials" / "real_0001.mp4"
            _mp4(video)
            (run_dir / "render_handoff.json").write_text(json.dumps({
                "ok": True,
                "artifact_role": "render_handoff",
                "final_delivery_claimed": False,
                "timeline_refs": [{
                    "segment": 1,
                    "asset_id": "real_0001",
                    "source_path": "assets/materials/real_0001.mp4",
                    "start_sec": 0.5,
                    "duration_sec": 0.75,
                }],
            }), encoding="utf-8")

            result = render_material_first_handoff(run_dir)

            self.assertTrue(result["ok"], result)
            self.assertTrue((run_dir / "final.mp4").is_file())
            video_streams = [
                stream for stream in result["ffprobe"]["streams"]
                if stream.get("codec_type") == "video"
            ]
            self.assertGreaterEqual(len(video_streams), 1)
            duration = float(video_streams[0]["duration"])
            self.assertGreaterEqual(duration, 0.5)
            self.assertLessEqual(duration, 1.2)


if __name__ == "__main__":
    unittest.main()
