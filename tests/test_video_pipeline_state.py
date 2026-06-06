import json
import tempfile
import unittest
from pathlib import Path

import video_pipeline


class BuildStateTest(unittest.TestCase):
    def test_all_rejected_top_text_fallback_routes_to_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp)
            (outdir / "content_qa.json").write_text(
                json.dumps(
                    {
                        "segments": [
                            {"segment": 1, "score": 88.0},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (outdir / "picks.json").write_text(
                json.dumps(
                    {
                        "log": {
                            "1": {
                                "vlm_verdicts": {
                                    "1": "no",
                                    "2": "no",
                                    "_fallback": "all_rejected_use_top_text",
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            final = outdir / "final.mp4"
            final.write_bytes(b"fake")

            state = video_pipeline.build_state(
                script=[
                    {
                        "segment": 1,
                        "title": "Fallback",
                        "source": "stock",
                    }
                ],
                outdir=str(outdir),
                style="mv",
                bgm=None,
                qa={"pass": True, "score": 90},
                unfixable={},
                attempt=0,
                final=str(final),
            )

            self.assertEqual(state["segments"][0]["status"], "needs_review")
            self.assertEqual(state["segments"][0]["fix_target"], "curator")
            self.assertEqual(state["segments"][0]["block_reason"], "all stock candidates rejected by VLM; top text-score fallback used")
            self.assertEqual(state["next_action"], "review")

    def test_clean_pass_remains_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp)
            (outdir / "content_qa.json").write_text(
                json.dumps({"segments": [{"segment": 1, "score": 88.0}]}),
                encoding="utf-8",
            )
            final = outdir / "final.mp4"
            final.write_bytes(b"fake")

            state = video_pipeline.build_state(
                script=[{"segment": 1, "title": "Clean", "source": "stock"}],
                outdir=str(outdir),
                style="mv",
                bgm=None,
                qa={"pass": True, "score": 90},
                unfixable={},
                attempt=0,
                final=str(final),
            )

            self.assertEqual(state["segments"][0]["status"], "done")
            self.assertIsNone(state["next_action"])


if __name__ == "__main__":
    unittest.main()
