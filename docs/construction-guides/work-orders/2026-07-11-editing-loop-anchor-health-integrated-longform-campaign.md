# Editing Loop Anchor, Health, Integrated Closure, And Long-Form Bridge Work Order

Status: **READY — WAVE A UNATTENDED, THEN OWNER GATE**

## 1. Goal And Source

Continue the accepted Editing Loop direction without adding another
orchestrator:

```text
truth anchors converge
→ Codebase Memory MCP read-only health audit
→ corrected owner packet v2
→ owner verdict
→ 22-second L0–L5 same-candidate closure
→ integrator acceptance
→ 66-second structural long-form bridge
```

Product basis:

- `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
- `skills/editing-loop-director.md`
- `docs/decisions/2026-07-10-evidence-carrying-editing-loop.md`
- `docs/pilots/2026-07-11-editing-loop-l0-clean-blind-first-of-kind-evidence.md`
- `docs/construction-guides/work-orders/2026-07-11-editing-loop-l0-l5-integrated-closure.md`

This is a multi-wave campaign. It is intentionally allowed to run unattended
until a declared stop state, but owner silence never authorizes a later wave.

## 2. Bounded Outcome

The largest result authorized by this work order is:

1. a verified anchor map and current read order;
2. a Codebase Memory MCP health snapshot with no automatic refactor;
3. an owner-review packet v2 that carries the bounded clean-blind L0 result;
4. after explicit owner verdicts, one 22-second integrated internal-review
   candidate with approved subtitles and fresh L5 evidence;
5. after explicit integrator acceptance, one approximately 66-second
   structural bridge formed from the frozen 44-second opening and accepted
   22-second interview candidate.

The bridge measures cross-segment context, verification and render cost. It is
not a creative long-film PASS. The complete 9.4-minute candidate requires a
separate work order after the bridge is accepted.

## 3. Fixed Product Decisions

1. `RUNBOOK.md` remains the single operator entry. `docs/INDEX.md` remains the
   document map. Product Spec is LOOP truth; Skill is execution doctrine;
   durable pilot summaries are accepted evidence; `.tmp` campaign files are
   current state, not permanent truth.
2. Evidence travels by stable ID plus repo/run-relative path, time/frame/cell/
   check anchor and producer. Do not create a new context envelope, journal,
   registry or state machine.
3. Codebase Memory MCP is a read-only architecture/navigation aid. It cannot
   override route contracts, tests, delivery gates or product decisions.
4. The historical answer-leaked L0 shadow remains `UNKNOWN`. The separate
   clean-blind retest is bounded `L0_CLEAN_BLIND_CERTIFIED`; this does not
   approve the selected picture.
5. Existing factories execute the edit. The Skill directs them. Do not extend
   Home, `runtime_orchestrator`, route runners or `mv_cut.py` for this campaign.
6. Picture taste, audio taste, transcript truth, music rights, creative
   approval and delivery remain owner-only.
7. No production-code or test change is authorized. A real factory gap becomes
   a recorded gap and stop state for a separate TDD work order.
8. `human_creative_approval=false` and `final_delivery_claimed=false` remain
   false throughout.

## 4. Required Read Order

Read completely before writing:

1. `AGENTS.md`
2. this work order — the sole campaign construction basis
3. `RUNBOOK.md`
4. `docs/INDEX.md`
5. `HANDOFF_CURRENT.md`
6. `docs/codebase-memory-mcp-handoff.md`
7. `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
8. `skills/pipeline-boundary.md`
9. `skills/editing-loop-director.md`
10. the evidence-carrying decision and L0/L1/L2/L5 durable summaries named by
    the Product Spec and Skill
11. `.tmp/editing_loop_certification_campaign/campaign_status.md`
12. the existing L0–L5 integrated-closure work order and worker report
13. the existing owner packet under `integrated_closure/owner_gate/`

Use `superpowers:executing-plans`. Do not spawn subagents: the anchors, packet
and carried candidate share state and must have one owner.

## 5. Environment And Owner Zones

- Repo: `C:\Users\user\Desktop\video_pipeline`
- Python: `C:\Users\user\miniconda3\python.exe`
- Shell: PowerShell
- Existing campaign root:
  `.tmp/editing_loop_certification_campaign/`
- New campaign root:
  `.tmp/editing_loop_anchor_health_longform_campaign/`

### Editable in Wave A

- `RUNBOOK.md` — only a compact Editing Loop continuation/router entry
- `docs/INDEX.md` — only the corresponding current-document-map entry
- `HANDOFF_CURRENT.md` — only a compact current Editing Loop continuation block
- `docs/generated/codebase-health-latest.md`
- `.tmp/editing_loop_anchor_health_longform_campaign/**`
- `.tmp/editing_loop_certification_campaign/campaign_status.md` — prepend or
  update only the current top status section
- `.tmp/editing_loop_certification_campaign/integrated_closure/owner_gate_v2/**`

### Additionally editable after a valid owner verdict

Only the paths authorized by Sections 12–17 of
`2026-07-11-editing-loop-l0-l5-integrated-closure.md`, including the fresh
`candidate_l4`/L5 Owner Zone and its bounded durable evidence summary.

### Additionally editable after integrator acceptance of the 22-second closure

- `.tmp/editing_loop_anchor_health_longform_campaign/longform_bridge_66s/**`

### Forbidden zone

- `AGENTS.md`
- `skills/**`, including `skills/INDEX.md`
- `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
- `docs/decisions/**`
- `docs/branch-contract-registry.*`
- `docs/interface-contracts/**`
- `video_pipeline_core/**`
- `tools/**`
- `tests/**`
- `video_tools.py`, `video_pipeline.py`, `runtime.py`
- all historical candidate/media/evidence files outside the approved new
  Owner Zones
- raw Downloads material and reference films

Do not stage, commit, push, upload, install dependencies, modify configuration,
or clean/reset the existing dirty tree. Record pre/post status and preserve
every unrelated dirty path.

## 6. Wave A0 — Freeze Baseline And Resolve Anchors

1. Record HEAD, branch, `git status --short`, and hashes of all tracked dirty
   files before writes.
2. Revalidate the frozen hashes in Section 5 of the existing integrated-closure
   work order and the five clean-blind artifact hashes in the L0 durable
   evidence summary. A drift is a stop condition.
3. Build
   `.tmp/editing_loop_anchor_health_longform_campaign/anchor_map.json` with
   these roles:

```text
operator_entry      → RUNBOOK.md
document_map        → docs/INDEX.md
resume_anchor       → HANDOFF_CURRENT.md
loop_product_truth  → Editing Loop Product Spec
loop_doctrine       → editing-loop-director Skill
durable_evidence    → L0/L1/L2/L5 summaries
current_state       → campaign_status.md
owner_gate          → owner packet v2
```

4. Each row must contain `role`, repo-relative `path`, existence, SHA-256,
   and links to the next anchor. Validate every link.
5. Add only the minimal router/map/resume entries needed to make this chain
   discoverable. Do not copy Product Spec content into the entry files.
6. Write `anchor_audit.md` separating current truth, historical evidence and
   ephemeral state. Literal old history may remain; no current entry may point
   to an obsolete packet as the latest owner gate.

## 7. Wave A1 — Codebase Memory MCP Health Audit

Use the already configured project
`C-Users-user-Desktop-video_pipeline`. Do not install or reconfigure the MCP.

Required read-only calls:

1. `index_status`
2. `detect_changes` with `since=HEAD~10`, `depth=2`
3. `get_architecture` for overview, clusters and entry points
4. `query_graph` for:
   - Functions/Methods with `cognitive >= 20`;
   - Functions/Methods with the highest outgoing `CALLS` count;
   - Files with the highest `change_count`;
   - available hot-path indicators such as `transitive_loop_depth` and
     `linear_scan_in_loop`.
5. `search_graph` for `contract adapter`, `pipeline home`,
   `runtime orchestrator`, `rough cut`, `audio mix`, `subtitle review`, and
   `long form segment`.

Write:

- `.tmp/editing_loop_anchor_health_longform_campaign/health/codebase_memory_health.json`
- `docs/generated/codebase-health-latest.md`

Every finding must contain:

```text
classification: objective | interpretation
evidence: MCP call/query plus returned symbol/path/metric
severity: green | yellow | red
action: observe | separate-work-order-proposal | stop-current-wave
trigger: the observable event required before construction
```

Health findings do not authorize refactoring. If MCP is unavailable, record
`UNKNOWN_MCP_UNAVAILABLE`, do not install it, and continue Wave A2.

## 8. Wave A2 — Owner Packet V2

Preserve `integrated_closure/owner_gate/**` unchanged. Create v2 under
`integrated_closure/owner_gate_v2/`:

- `integrated_owner_review_index_v2.md`
- `integrated_owner_verdict_template_v2.json`
- `integrated_owner_packet_manifest_v2.json`
- `packet_validation_report.json`

Required corrections:

1. L0 historical shadow remains `UNKNOWN (historical)`.
2. L0 procedure is `CERTIFIED_BOUNDED` from the separate clean-blind evidence.
3. `l0_selects` remains owner `unknown`; procedural certification is not taste.
4. L1 picture, L2 no-op, L3 internal-preview audio and all seven L4 cue fields
   remain explicit owner verdicts.
5. The packet must link the valid 22-second picture, internal-preview audio,
   exact source-speech audio, transcript review table, clean-blind artifacts,
   current frozen hashes and all limitations.
6. Keep `preview_only=true`, `delivery_allowed=false`, both approval flags
   false, and every non-delegated decision explicit.
7. Validate UTF-8, JSON, every path, every declared hash, all seven cue IDs and
   all false flags.

The template must accept only:

```jsonc
{
  "l0_selects": "approve | revise | unknown",
  "l1_picture": "approve | revise | unknown",
  "l2_effects": "no_change_approved | revise | unknown",
  "l3_audio": "approve_internal_preview | revise | unknown",
  "l4_transcript_cues": [
    {"cue_id": "cue_001", "approved_text": "", "verdict": "approved_text | revise | unknown"}
  ]
}
```

Include all seven cue IDs. Do not prefill approved text.

## 9. Wave A Acceptance And Stop

Run:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_skill_index tests.test_skill_tool_contracts tests.test_pipeline_skill_boundaries tests.test_interactive_skill_flow_docs -v
git diff --check
```

Expected exits: `0`. Also run an explicit UTF-8/JSON/path/hash read-back for
the anchor map, health artifacts and packet v2.

Write:

- `.tmp/editing_loop_anchor_health_longform_campaign/wave_a_worker_report.md`
- `.tmp/editing_loop_anchor_health_longform_campaign/campaign_status.md`

Then stop exactly at:

`WAITING_OWNER_ANCHOR_HEALTH_AND_INTEGRATED_VERDICTS`

No owner response means no Wave B. Do not wait, poll or infer approval.

## 10. Resume Contract — Owner Verdict

Wave B may begin only when the owner supplies a verbatim verdict matching the
v2 template. Preserve the message in a new owner-verdict artifact and hash it.

- Any blank/unknown cue or field keeps its LOOP `UNKNOWN` and stops.
- Any `revise` writes one evidence-backed target finding and stops at
  `WAITING_OWNER_TARGETED_LOOP_REVISION`.
- Do not fill transcript text from ASR or agent suggestions.

## 11. Wave B — 22-Second Same-Candidate Integrated Closure

After a valid owner verdict, execute Sections 12–17 of
`2026-07-11-editing-loop-l0-l5-integrated-closure.md` as the subordinate
factory procedure, with these overrides:

1. Do not rerun L0 blind selection. Carry
   `L0_CLEAN_BLIND_CERTIFIED` plus the separate owner selects verdict.
2. Use only packet v2 and its owner-verdict hash.
3. Keep production code/tests forbidden. A factory gap stops the affected
   stream as specified by the subordinate work order.
4. Run the subordinate full suite once, last, only if Phases 3–5 and durable
   evidence complete. Do not run it during Wave A.
5. The worker may report ready for integrator review; only the integrator may
   certify L3/L4 or the integrated closure.

Required stop:

`WAITING_INTEGRATOR_L0_L5_INTEGRATED_CLOSURE_REVIEW`

No Wave C before a separate integrator verdict explicitly accepts the
22-second closure and its input/output hashes.

## 12. Wave C — 66-Second Structural Long-Form Bridge

This wave is conditional on integrator acceptance, not merely worker PASS.

Inputs:

- frozen 44-second Canon 67 `candidate_l2`;
- accepted 22-second integrated candidate from Wave B.

1. Freeze both hashes and construct `bridge_manifest.json` with stable segment
   IDs `opening_000_044` and `interview_044_066`, source hashes, durations,
   evidence refs, audio/rights limitations and carried LOOP decisions.
2. Use only the public concat capability:

```powershell
C:\Users\user\miniconda3\python.exe video_tools.py concat <opening-final.mp4> <interview-final.mp4> --out <bridge>\run\final.mp4
```

3. Measure wall-clock render time. Do not build segment rerender, dirty matrix,
   transition engine or long-form orchestrator.
4. Verify input hashes remain unchanged; output is approximately 66 seconds,
   contains one video and one audio stream, preserves the expected segment
   boundary, and has no blocking black-frame/stream error.
5. Run fresh rendered QA, final-product verify and perception-field review on
   the bridge. Inspect the 42–46 second boundary densely.
6. Write a finding packet separating technical continuity, story discontinuity,
   audio/right limitations and owner taste. A hard cut is acceptable evidence;
   it is not automatically a creative PASS.
7. Propose—but do not write—the minimum long-form Skill doctrine learned from
   this bridge: stable segment IDs, per-segment LOOPs, carried evidence, global
   L5 and the measured rerender trigger.

Stop exactly at:

`WAITING_INTEGRATOR_66S_LONGFORM_BRIDGE_REVIEW`

The complete 9.4-minute film, long-form Skill maturity update and segment
rerender decision remain out of scope.

## 13. Stop-Loss

- One LOCAL repair attempt per artifact/command failure class.
- A second occurrence of the same class is STRUCTURAL; stop that wave at its
  last green state.
- Stop immediately on frozen-hash drift, owner-zone conflict, invalid UTF-8,
  missing owner truth, reference-footage selection, licensing/delivery
  ambiguity, required production-code/test change, or an acceptance command
  failure that cannot be repaired inside the Owner Zone.
- Never lower a threshold, alter historical evidence, handcraft a private
  renderer/mixer, copy an old PASS, infer owner text, or use success exit alone
  as product evidence.
- A blocked later wave does not erase an earlier PASS. Continue only independent
  read-only/reporting work that cannot contaminate the blocked artifact.

## 14. Required Report

At every stop state, report:

- exact state and completed wave;
- PASS/FAIL/UNKNOWN by anchor, health check and LOOP;
- HEAD, exact pre/post dirty tree and protected hashes;
- MCP calls/queries, returned project/index counts and health findings;
- packet/candidate/bridge paths and SHA-256 values;
- every command, exit code and focused/full-suite status;
- owner/integrator verdicts verbatim when present;
- deviations, repairs, skipped work, factory gaps, blind spots and next legal
  resume condition;
- `human_creative_approval=false`;
- `final_delivery_claimed=false`.

No commit, push, upload, delivery or general long-form certification is
authorized.
