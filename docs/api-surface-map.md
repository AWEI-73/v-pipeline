# API Surface Map & Boundary Contract

This document defines the API layer architecture, routing policies, and security boundaries for the Hermes Video Pipeline's HTTP services.

---

## 1. Role of the API Layer

The Dashboard and Workbench servers (`tools/dashboard_server.py` and `tools/workbench_server.py`) serve as **visual interfaces** and **draft editors** for operators and agents. 

> [!IMPORTANT]
> The API layer is **NEVER** the owner of the Canonical Truth. It operates strictly under **draft-only** or **request-only** write boundaries to prevent out-of-order state corruption.

---

## 2. Endpoint Categories (Modes)

API endpoints are classified into strict operational modes:

| Mode | Description | Example Endpoint | Allowed Writes |
|---|---|---|---|
| `read_only` | Safe endpoints that return system info, views, or logs without side effects. | `GET /api/artifacts` | None |
| `draft_write` | Permitted to write to local draft files in the run directory. Writes are isolated from main-line build assets. | `POST /api/workbench/patch` | `timeline_patch.json`, `patched_draft_timeline.json` |
| `derived_cache_write` | Permitted to write derived preview cache files only. These files are rebuildable and never canonical truth. | `GET /api/workbench/thumbnails` | `workbench_thumbs/` |
| `request_only` | Requests a promotion/merge of drafts into the canonical truth. Writes only a promotion request file. | `POST /api/control/promote` | `workbench_promotion_request.json` |
| `canonical_write` | Restricted mode allowed to write directly to canonical files (`timeline.json`, `final.mp4`). **Disabled by default for API endpoints.** | None | N/A |
| `system` | Handles framework operations, SPA rendering, and static file delivery. | `GET /dashboard` | None |

---

## 3. Forbidden Writes

To protect mainline pipeline execution, the API layer is strictly forbidden from writing or mutating the following files directly:
*   `final.mp4` (Must only be produced by `contract-run` or verified compilation)
*   `segment_contract.json` (Main-line segment parameters)
*   `project_material_map.json` (Canonical material tracking)
*   `timeline.json` (Canonical timeline track)

Any workbench or control endpoint wishing to request updates to these files must submit a draft patch or write a request envelope.

---

## 4. Response Shape Contract

To help calling agents distinguish between business-level blocks and system exceptions, the API returns two distinct JSON response structures:

### A. Business/Pipeline Result (`pipeline_result`)
Returned for successful operations or valid pipeline-level blocks, such as a human revision request or a vocal conflict with required narration:
```json
{
  "ok": false,
  "status": "blocked",
  "branch": "soundtrack-arranger",
  "next_action": "agent_decide_repair",
  "blocking": [
    {
      "code": "VOCAL_CONFLICT_WITH_NARRATION",
      "message": "Selected music contains vocals but narration is required."
    }
  ]
}
```

### B. System/API Problem Detail (`problem_detail`)
Returned for system failures, malformed requests, missing parameters, or server crashes. Adheres to **RFC 7807** Problem Detail structure:
```json
{
  "type": "https://hermes.local/problems/missing-artifact",
  "title": "Missing Artifact",
  "status": 400,
  "detail": "effect_contract.json was not found.",
  "instance": "/api/control/effect-review"
}
```

