import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.material_first_landing_case import run_material_first_landing_case
from video_pipeline_core.asset_paths import is_absolute_path_string


def _jpg(path: Path, color: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (80, 45), color=color).save(path, "JPEG")


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


if __name__ == "__main__":
    unittest.main()
