"""BUILD recoverable blocks + VERIFY fix_class taxonomy (material/spec/human).

A per-segment BUILD failure must surface in state as a `blocked` segment with a
fix_class and route via next_action — never crash the film. A whole-film
precompose gate failure routes to review instead of a stacktrace.
"""
import json
import tempfile
import unittest
from pathlib import Path

import video_pipeline as vp
from video_pipeline_core import vt_core


class FixTaxonomyAlignmentTest(unittest.TestCase):
    """錯誤分類單一真相:vt_core 與 video_pipeline 的 fix_class→target 必須一致
    (收斂時 video_pipeline 應改 import vt_core;此測鎖住對齊,divergence 會紅)。"""

    def test_fix_target_tables_match(self):
        self.assertEqual(vt_core.FIX_TARGET, vp._FIX_TARGET)

    def test_toolerror_fix_class_routes(self):
        e = vt_core.ToolError("no material", fix_class="material")
        self.assertEqual(e.fix_class, "material")
        self.assertEqual(e.fix_target, "curator")
        self.assertIsInstance(e, RuntimeError)        # 向後相容:仍是 RuntimeError
        self.assertIsNone(vt_core.ToolError("plain").fix_class)   # 不帶分類也可

    def test_gap_sentinel(self):
        self.assertEqual(vt_core.GAP, "GAP")


def _state(tmp, script, qa, **kw):
    outdir = Path(tmp)
    (outdir / "content_qa.json").write_text(
        json.dumps({"segments": [{"segment": s["segment"], "score": 88.0} for s in script]}),
        encoding="utf-8")
    final = outdir / "final.mp4"
    final.write_bytes(b"fake")
    return vp.build_state(script=script, outdir=str(outdir), style="mv", bgm=None,
                          qa=qa, unfixable=kw.get("unfixable", {}), attempt=0,
                          final=str(final), build_blocks=kw.get("build_blocks"),
                          gate_review=kw.get("gate_review"))


class FixClassMapTest(unittest.TestCase):
    def test_map(self):
        self.assertEqual(vp._FIX_TARGET["material"], "curator")
        self.assertEqual(vp._FIX_TARGET["spec"], "director")
        self.assertIsNone(vp._FIX_TARGET["human"])


class BuildBlockStateTest(unittest.TestCase):
    def test_material_build_block_routes_to_await_material(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = [{"segment": 1, "title": "a", "source": "local"},
                      {"segment": 2, "title": "b", "source": "stock"}]
            st = _state(tmp, script, {"pass": True, "score": 90},
                        build_blocks={1: {"reason": "source=local 素材未到位", "fix_class": "material"}})
            seg1 = st["segments"][0]
            self.assertEqual(seg1["status"], "blocked")
            self.assertEqual(seg1["fix_class"], "material")
            self.assertEqual(seg1["fix_target"], "curator")
            self.assertEqual(seg1["block_reason"], "source=local 素材未到位")
            self.assertEqual(st["next_action"], "await_material")
            self.assertEqual(st["blocking"][0]["segment"], 1)

    def test_spec_block_routes_to_revise_director(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = [{"segment": 1, "title": "a", "source": "stock"}]
            st = _state(tmp, script, {"pass": True, "score": 90},
                        build_blocks={1: {"reason": "layout wrong", "fix_class": "spec"}})
            self.assertEqual(st["segments"][0]["fix_class"], "spec")
            self.assertEqual(st["segments"][0]["fix_target"], "director")
            self.assertEqual(st["next_action"], "revise:director(seg=[1])")

    def test_gate_review_routes_to_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = [{"segment": 1, "title": "a", "source": "stock"}]
            st = _state(tmp, script, {"pass": False, "score": 0},
                        gate_review="precompose gate failed (2 issues)")
            self.assertEqual(st["next_action"], "review")
            self.assertEqual(st["gate_review"], "precompose gate failed (2 issues)")

    def test_clean_pass_unaffected(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = [{"segment": 1, "title": "a", "source": "stock"}]
            st = _state(tmp, script, {"pass": True, "score": 90})
            self.assertEqual(st["segments"][0]["status"], "done")
            self.assertIsNone(st["segments"][0]["fix_class"])
            self.assertIsNone(st["next_action"])


class RecoverableBuildErrorTest(unittest.TestCase):
    def test_carries_segment_reason_class(self):
        e = vp.RecoverableBuildError(3, "no candidates", "material")
        self.assertEqual(e.segment, 3)
        self.assertEqual(e.fix_class, "material")
        self.assertEqual(str(e), "no candidates")


if __name__ == "__main__":
    unittest.main()
