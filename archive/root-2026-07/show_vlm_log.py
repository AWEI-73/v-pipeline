#!/usr/bin/env python3
import json, sys
proj = sys.argv[1] if len(sys.argv) > 1 else "nightmarket"
p = json.load(open(f"{proj}/picks.json"))
print(f"mode: {p.get('_mode')}, vlm_model: {p.get('_vlm_model')}\n")
print(f"{'seg':<4} {'pick':<5} {'rejected':<12} vlm_verdicts (top3 by text score)")
print("-" * 80)
for n in sorted(p["picks"], key=int):
    log = p["log"][n]
    v = log.get("vlm_verdicts", {})
    rej = log.get("rejected_by_vlm", [])
    rej_str = ",".join(f"c{r}" for r in rej) if rej else "-"
    v_str = ", ".join(f"c{k}={vv}" for k, vv in v.items() if k != "_fallback")
    print(f"{n:<4} c{p['picks'][n]:<4} {rej_str:<12} {v_str}")
