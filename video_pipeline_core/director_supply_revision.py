"""Director-side contract revision from objective material supply limits."""
from __future__ import annotations

import copy
import json
from pathlib import Path


def _load_json(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def _write_json(path, payload):
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def revise_contract_to_supply(contract, supply_review):
    revised = copy.deepcopy(contract)
    supply_by_segment = {
        item.get("segment"): item
        for item in (supply_review or {}).get("segments") or []
    }
    changes = []
    for index, segment in enumerate(revised.get("segments") or []):
        sid = segment.get("segment", index + 1)
        supply = supply_by_segment.get(sid)
        if not supply or supply.get("action") != "shorten_or_merge":
            continue
        requested = float(segment.get("requested_duration_sec") or segment.get("duration_sec") or 0)
        maximum = float(supply.get("max_honest_duration_sec") or 0)
        if maximum <= 0 or requested <= maximum:
            continue
        segment["requested_duration_sec"] = maximum
        segment["director_revision"] = {
            "reason": "script_overreach",
            "source": "supply_review",
            "previous_requested_duration_sec": requested,
            "max_honest_duration_sec": maximum,
            "action": "shortened_to_supply",
        }
        changes.append({
            "segment": sid,
            "from_requested_duration_sec": requested,
            "to_requested_duration_sec": maximum,
            "reason": "script_overreach",
        })
    return revised, {
        "artifact_role": "director_supply_revision",
        "version": 1,
        "ok": True,
        "updated_segments": [item["segment"] for item in changes],
        "changes": changes,
        "ready_for_spec_review": True,
    }


def revise_contract_file(contract_path, supply_review_path, out_contract_path, out_report_path):
    revised, report = revise_contract_to_supply(
        _load_json(contract_path),
        _load_json(supply_review_path),
    )
    _write_json(out_contract_path, revised)
    _write_json(out_report_path, report)
    return {
        "ok": True,
        "updated_segments": report["updated_segments"],
        "out_contract": str(Path(out_contract_path)),
        "out_report": str(Path(out_report_path)),
    }
