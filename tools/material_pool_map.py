"""Checkout or commit the canonical versioned material-pool map."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from video_pipeline_core.material_pool_store import checkout_pool_map, commit_campaign_map


def _write_receipt(path: str | None, payload: dict) -> None:
    if not path:
        return
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    checkout = sub.add_parser("checkout")
    checkout.add_argument("--pool-root", required=True)
    checkout.add_argument("--pool-id", required=True)
    checkout.add_argument("--campaign-id", required=True)
    checkout.add_argument("--out", required=True)
    checkout.add_argument("--receipt")

    commit = sub.add_parser("commit")
    commit.add_argument("--pool-root", required=True)
    commit.add_argument("--pool-id", required=True)
    commit.add_argument("--campaign-id", required=True)
    commit.add_argument("--campaign-map", required=True)
    commit.add_argument("--expected-base-sha256", required=True)
    commit.add_argument("--receipt")

    args = parser.parse_args(argv)
    if args.command == "checkout":
        result = checkout_pool_map(
            pool_root=args.pool_root,
            pool_id=args.pool_id,
            campaign_id=args.campaign_id,
            out_path=args.out,
        )
    else:
        result = commit_campaign_map(
            pool_root=args.pool_root,
            pool_id=args.pool_id,
            campaign_id=args.campaign_id,
            campaign_map_path=args.campaign_map,
            expected_base_sha256=args.expected_base_sha256,
        )
    _write_receipt(args.receipt, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
