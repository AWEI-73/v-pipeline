# M6e — Real-case acceptance (67th graduation footage)

Date: 2026-06-15. Type: real-data acceptance run (not unit tests). Risk under
test has shifted from "code-contract correctness" to "does the real material +
workflow actually work and is it usable".

Material: `C:\Users\user\Downloads\微電影素材\_整理後` — the real 67th graduation
footage (88 videos, 211 photos, the two finished films, and
`_腳本素材對照表.md` = the human script×material cross-reference: **49 script
items, 22% ✅ covered / 22% ⚠️ suspect / 55% ❌ missing**). This partial-supply
reality is exactly the case the M6 lifecycle was built for.

Reproduce: `python tools/m6e_acceptance.py` builds the fixture (real video
sources, real ffprobe durations, agent-reviewed `satisfies` edges per the
cross-reference table) into `.tmp/m6e/` (gitignored; references the footage by
absolute path — set `M6E_FOOTAGE` to relocate). The four entry runs below were
then driven through the shipped CLIs.

## Results — all four entry behaviors validated on real footage

| Entry | Command | Stage / outcome | Render |
|---|---|---|---|
| **A. existing-material** (raw maps, no needs) | `material-map-lifecycle --maps-dir maps_raw` | `await_requirements_discussion`, `can_build=false` | none (correct) |
| **B. script-first, insufficient** (full 6-need set vs covered-3 material) | `material-map-lifecycle --needs needs_full --material-db …` | `await_material`; `shooting_brief.json` (6 reqs); delta `covered:3 missing:3`, blocks 2 must_have (晨操, 繩結) | none |
| **B (BUILD attempt)** | `contract-run contract_full_norev …` | stage `material_delta`, `ready_for_build=false`, `next_action=await_material` | **no final.mp4** (blocked before render) ✓ |
| **C. covered** (3 ✅ segments) | `material-map-lifecycle …` then `contract-run contract_covered …` | `build_ready` → handoff(original contract) | **final.mp4 8.47s, verify 98.5 PASS** ✓ |
| **D. revision** (drop+waive the 2 missing must_have) | `material-map-lifecycle … --decisions` then `contract-run contract_full …` | `build_ready`(revised 3-seg); run_contract re-ran M6c, re-derived waivers, built revised | **final.mp4** ✓ |

Key confirmations:
- **Only-material entry stops at requirements discussion** (no render, no invented
  needs). ✓
- **Script-first with insufficient material produces a shooting brief and blocks
  BUILD** — `run_contract` returned `stage=material_delta` and never created
  `final.mp4`. The two un-shot must_haves (晨操, 繩結) are the explicit blockers. ✓
- **Covered / revised → real ffmpeg render via the handoff** — both `out_C` and
  `out_D` produced a playable `final.mp4` from the real `.MOV` sources via MR1
  map-ranked retrieval; `verify_result` scored 98.5/PASS. The contact sheet
  (`.tmp/m6e/contact_C.jpg`) shows unmistakably real 67th footage (assembled
  students, night-court activity, the "感謝老師…" card). ✓
- The handoff did **not** bypass the runtime gate: `contract-run` re-ran the fresh
  M6b/M6c gate each time (block in B, pass in C, re-applied revision in D). ✓

## Finding (real usability risk surfaced) — material_map path resolution mismatch

The first render attempt produced `render_mv_audio: no segments rendered` (silent
GAP). Root cause: a `material_db` with a **relative** `material_map` path is
resolved differently by two loaders:

- the M6b gate / M6d lifecycle resolve it **relative to the material_db dir**
  (the MR1/M6c hardening) → gate sees the maps, passes;
- the legacy BUILD path `mv_cut._load_material_maps` resolves it **relative to the
  process cwd** → loads **zero** maps → every segment falls to GAP → "no segments".

So a project can pass the gate yet render nothing. Workaround used here: absolute
`material_map` paths in `materials_db.json`. **Recommended bounded follow-up
(M6e.1):** make `mv_cut._load_material_maps` resolve `material_map` relative to
the material_db directory (consistent with the gate), so relative paths are
portable end-to-end. (Not changed in this acceptance run — flagged for a separate
bounded commit.)

## Still pending (cannot be done by the agent)

1. **Human viewing.** Watch `.tmp/m6e/out_C/final.mp4` and `.tmp/m6e/out_D/final.mp4`
   end to end and compare against the reference film
   `…/67期結訓影片-終.mp4`. Confirm: material ↔ script ↔ final are consistent;
   the dropped/waived segments (晨操, 繩結) are acceptably absent; pacing/audio feel
   right. (Checklist below.)
2. **Full-scale ingest.** This run hand-built per-asset maps for a covered subset
   (the agent's review against `_腳本素材對照表.md`). A real project still needs the
   curator/caption ingest over all 304 files to produce per-asset maps + satisfies
   edges at scale; `.heic` photos (107) were not exercised (ffmpeg HEIC decode is
   environment-dependent) — prefer mp4/mov/jpg or transcode HEIC first.

### Human-viewing checklist
- [ ] `out_C/final.mp4` plays; the three covered segments (主任期勉 / 慶生會 / 感謝導師)
      show the intended real clips, in order.
- [ ] `out_D/final.mp4` is the revised cut — 晨操 / 繩結 absent, the rest intact.
- [ ] No segment shows material that does not match its need (no silent wrong-clip).
- [ ] Audio (7感性收尾 reference track) sits under the footage acceptably.
- [ ] Compared to `67期結訓影片-終.mp4`, the covered sections are faithful.

## Verdict

The M6 lifecycle's three entry points behave correctly on **real 67th material**:
material-only converges on discussion, script-first shortfalls block BUILD with a
shooting brief, and covered/revised projects render for real through the handoff
without bypassing the gate. The remaining risk is genuinely human (viewing
sign-off) and operational (full ingest + the relative-path loader fix), not a
code-contract gap. **M6e automated acceptance: PASS. Human sign-off + M6e.1
loader fix: open.**
