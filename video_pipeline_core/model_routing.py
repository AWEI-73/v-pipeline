"""Model route artifact for the agent-driven video workflow.

Visual judgment roles default to agent/cloud review. Local VLM backends are
allowed only when a caller explicitly opts in, because the local model is not a
reliable final judge for material understanding or VERIFY.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


DEFAULT_MODEL_ROUTES: dict[str, dict[str, Any]] = {
    "video_understanding": {
        "provider": "agent",
        "model": "codex_or_hermes",
        "reason": "Material visual understanding uses agent review by default; local VLM is opt-in only.",
    },
    "verify_vlm": {
        "provider": "agent",
        "model": "codex_or_hermes",
        "reason": "Render/content verification uses agent review by default, not local VLM.",
    },
    "content_qa": {
        "provider": "agent",
        "model": "codex_or_hermes",
        "reason": "Content QA is routed to agent review by default; local VLM is only an explicit fallback.",
    },
    "asr": {
        "provider": "local",
        "model": "small",
        "env": "MV_ASR_MODEL",
        "reason": "Speech recognition remains a local mechanical tool.",
    },
    "agent_planning": {
        "provider": "agent",
        "model": "codex_or_hermes",
        "reason": "SPEC and route planning need agent reasoning.",
    },
}


def default_model_routes() -> dict[str, Any]:
    return {
        "artifact_role": "model_route_contract",
        "model_routes_version": 2,
        "routes": copy.deepcopy(DEFAULT_MODEL_ROUTES),
    }


def _validate_routes(payload: dict[str, Any]) -> dict[str, Any]:
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


def load_model_routes(path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
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


def resolve_model(routes: dict[str, Any] | None, role: str, default: Any = None) -> Any:
    route = (routes or {}).get("routes", {}).get(role)
    if not route:
        return default
    return route.get("model", default)


def write_model_routes(path: str | Path, routes: dict[str, Any] | None = None) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _validate_routes(routes or default_model_routes())
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return str(path)
