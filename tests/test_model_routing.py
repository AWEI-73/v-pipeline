import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import model_routing


class ModelRoutingTest(unittest.TestCase):
    def test_defaults_cover_verify_content_qa_and_asr(self):
        routes = model_routing.default_model_routes()
        for role in ("video_understanding", "verify_vlm", "content_qa"):
            self.assertEqual(routes["routes"][role]["provider"], "agent")
        self.assertEqual(
            model_routing.resolve_model(routes, "verify_vlm"),
            "codex_or_hermes",
        )
        self.assertEqual(
            model_routing.resolve_model(routes, "content_qa"),
            "codex_or_hermes",
        )
        self.assertEqual(model_routing.resolve_model(routes, "asr"), "small")

    def test_load_json_override_preserves_unspecified_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "model_routes.json"
            p.write_text(json.dumps({
                "routes": {
                    "verify_vlm": {
                        "provider": "openai",
                        "model": "gpt-5.4-mini",
                        "reason": "cloud review fallback",
                    }
                }
            }), encoding="utf-8")
            routes = model_routing.load_model_routes(p)
        self.assertEqual(model_routing.resolve_model(routes, "verify_vlm"), "gpt-5.4-mini")
        self.assertEqual(model_routing.resolve_model(routes, "content_qa"), "codex_or_hermes")

    def test_invalid_route_requires_model(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad_model_routes.json"
            p.write_text(json.dumps({"routes": {"verify_vlm": {"provider": "ollama"}}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                model_routing.load_model_routes(p)

    def test_write_model_routes_is_traceable_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "model_routes.json"
            result = model_routing.write_model_routes(out)
            payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(result, str(out))
        self.assertEqual(payload["artifact_role"], "model_route_contract")
        self.assertIn("verify_vlm", payload["routes"])


if __name__ == "__main__":
    unittest.main()
