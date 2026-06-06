"""model_routing.py — model route artifact for agent-driven video workflow.

This module makes model choices explicit without forcing every runtime caller to
switch providers at once. The artifact is intentionally small: each role names
the provider/model and the reason it exists in the workflow.
"""
import copy
import json
from pathlib import Path


DEFAULT_MODEL_ROUTES = {
    "video_understanding": {
        "provider": "ollama",
        "model": "qwen3-vl:4b-instruct",
        "base_url_env": "OLLAMA_URL",
        "reason": "素材/畫面理解與低成本視覺判讀",
    },
    "verify_vlm": {
        "provider": "ollama",
        "model": "qwen3-vl:4b-instruct",
        "base_url_env": "OLLAMA_URL",
        "reason": "節點 VERIFY 小模型視覺審查",
    },
    "content_qa": {
        "provider": "ollama",
        "model": "qwen3-vl:4b-instruct",
        "base_url_env": "OLLAMA_URL",
        "reason": "內容 QA 與素材適性初篩",
    },
    "asr": {
        "provider": "local",
        "model": "small",
        "env": "MV_ASR_MODEL",
        "reason": "語音轉文字與字幕初稿",
    },
    "agent_planning": {
        "provider": "agent",
        "model": "codex_or_hermes",
        "reason": "互動式 SPEC、節點決策與契約修正",
    },
}


def default_model_routes():
    return {
        "artifact_role": "model_route_contract",
        "model_routes_version": 1,
        "routes": copy.deepcopy(DEFAULT_MODEL_ROUTES),
    }


def _validate_routes(payload):
    routes = payload.get("routes")
    if not isinstance(routes, dict):
        raise ValueError("model_routes requires object field: routes")
    for role, route in routes.items():
        if not isinstance(route, dict):
            raise ValueError(f"model route {role!r} must be an object")
        if not route.get("model"):
            raise ValueError(f"model route {role!r} requires model")
        if not route.get("provider"):
            raise ValueError(f"model route {role!r} requires provider")
    return payload


def load_model_routes(path=None, overrides=None):
    payload = default_model_routes()
    if path:
        with Path(path).open(encoding="utf-8") as f:
            incoming = json.load(f)
        incoming_routes = incoming.get("routes")
        if incoming_routes is None:
            raise ValueError("model_routes override requires routes")
        _validate_routes({"routes": incoming_routes})
        for role, route in incoming_routes.items():
            payload["routes"][role] = {**payload["routes"].get(role, {}), **route}
    if overrides:
        _validate_routes({"routes": overrides})
        for role, route in overrides.items():
            payload["routes"][role] = {**payload["routes"].get(role, {}), **route}
    return _validate_routes(payload)


def resolve_model(routes, role, default=None):
    route = (routes or {}).get("routes", {}).get(role)
    if not route:
        return default
    return route.get("model", default)


def write_model_routes(path, routes=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _validate_routes(routes or default_model_routes())
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return str(path)
