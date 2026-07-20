# Canon 67 150-Second Hero Cut Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task in one
> continuous director session. Do not dispatch subagents; creative continuity
> is part of the experiment.

**Goal:** Produce one review-only 150-second Hero Cut from the same 42 Canon 67
assets as the frozen factory baseline, with bounded public-reference research,
licensed online music evidence, traceable creative decisions, and a blind owner
comparison.

**Architecture:** The immutable factory candidate remains the control. One
director agent works only in an ignored `.tmp` sandbox, first freezing reference
and music evidence, then performing at most three render/review loops. The run
ends with an owner packet; no successful decision enters production until a
separate post-verdict distillation project.

**Tech Stack:** Existing Hermes CLI/tools, FFmpeg/ffprobe, installed Remotion
runtime when needed, browser/web access for bounded research, JSON/Markdown
evidence, SHA-256 manifests.

## Global Constraints

- Baseline video SHA-256:
  `cd4be611fe9f36916475c89ba3c5efb1dc3f73076f7cb6567093c54f8f451619`.
- Baseline picture-plan SHA-256:
  `8a4dadf40dd13b74ea0f39724e61fd15eb2e7fbe304aa94467177ae839dc2c0d`.
- Use all and only the same 42 distinct visual asset IDs; do not mutate source
  files or the baseline run.
- Final duration: `150.0 +/- 0.5` seconds.
- One director, no subagents, no production-code/test/Skill/registry edits.
- One-off code is allowed only below
  `.tmp/canon67_150s_hero_cut/director_sandbox/`.
- At most five public video references, three downloaded music candidates, two
  tracks used in the cut, and three complete creative renders.
- Online music requires official-source and license evidence. The candidate
  remains `delivery_allowed=false` and review-only.
- Preserve every failed attempt and deviation. Do not fabricate PASS evidence.
- `human_creative_approval=false` and `final_delivery_claimed=false` until the
  owner returns a verdict.

## File Structure

Create only beneath `.tmp/canon67_150s_hero_cut/` during execution:

- `control/input_freeze.json` — immutable baseline, plan, source and git facts.
- `research/reference_brief.json` / `.md` — five-reference maximum.
- `research/music_candidates/**` — official downloads and license snapshots.
- `research/music_license_manifest.json` — rights evidence and selection.
- `director/baseline_diagnosis.md` — creative weaknesses of the control.
- `director/director_treatment.json` / `.md` — story, energy, audio and visual
  thesis.
- `director/hero_edit_decision_plan.json` — layered picture/audio/text/effects
  timeline.
- `director/creative_decision_trace.json` — evidence-carrying decisions.
- `director_sandbox/**` — one-off render code/configuration only.
- `versions/v1/**`, `versions/v2/**`, `versions/v3/**` — immutable version
  renders, plans, findings, perception evidence and hashes.
- `review/candidate_X.mp4`, `review/candidate_Y.mp4` — blind owner candidates.
- `review/comparison_seal.json` — X/Y mapping; do not expose in review index.
- `review/owner_review_index.md` — review order without identity leakage.
- `review/owner_verdict_template.json` — unset verdict.
- `final/hero_cut.mp4` — chosen director version, not delivery.
- `final/hero_cut_manifest.json` — lineage and exact hashes.
- `final/agent_attestation.json` — actual reads, inspections, tools and limits.
- `final/worker_report.md` — commands, results, deviations and final state.

---

### Task 1: Freeze The Control And Establish A Clean Sandbox

**Files:**
- Read:
  `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/final.mp4`
- Read:
  `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/inputs/combined_rough_cut_plan.json`
- Create: `.tmp/canon67_150s_hero_cut/control/input_freeze.json`

**Interfaces:**
- Consumes: frozen baseline candidate and accepted plan.
- Produces: verified 42-ID allowlist and immutable control hashes used by every
  later task.

- [ ] **Step 1: Record pre-run state and exact hashes**

Run:

```powershell
git status --short
Get-FileHash -Algorithm SHA256 -LiteralPath '.tmp\canon67_150s_picture_first_longform\l1_picture_candidate\final.mp4'
Get-FileHash -Algorithm SHA256 -LiteralPath '.tmp\canon67_150s_picture_first_longform\l1_picture_candidate\inputs\combined_rough_cut_plan.json'
```

Expected: hashes match the Global Constraints. Otherwise stop as
`BASELINE_DRIFT`.

- [ ] **Step 2: Read the plan and prove the source set**

Extract the 42 distinct asset IDs, source paths, source hashes, clip IDs,
source types, current windows and durations. Hash every referenced source and
require `42/42` matches. Do not infer missing hashes.

- [ ] **Step 3: Create the run tree and input freeze**

Write `input_freeze.json` with baseline/video/plan hashes, the complete 42-ID
allowlist, source read-back results, current HEAD, pre-run status, timestamp,
and these flags:

```json
{
  "human_creative_approval": false,
  "final_delivery_claimed": false,
  "delivery_allowed": false
}
```

- [ ] **Step 4: Validate UTF-8 and JSON**

Use explicit UTF-8 decoding. Require no replacement character, no suspicious
`????` Chinese corruption, valid JSON, and 42 distinct asset IDs.

---

### Task 2: Freeze Bounded Reference Research

**Files:**
- Create: `.tmp/canon67_150s_hero_cut/research/reference_brief.json`
- Create: `.tmp/canon67_150s_hero_cut/research/reference_brief.md`

**Interfaces:**
- Consumes: Canon 67 story categories and the baseline diagnosis target.
- Produces: maximum five technique references; no downloaded reference media.

- [ ] **Step 1: Search public references**

Find up to five graduation, training, corporate-recap, documentary-montage, or
emotionally structured event films. Actually inspect the relevant passages in
the browser; search-result snippets alone are not evidence.

- [ ] **Step 2: Record transferable observations**

For each reference, record URL, title, inspection date, timecodes, observed
technique, intended Canon 67 application, and initial adoption state. Do not
copy protected footage, audio, graphics, fonts, dialogue, or lyrics.

- [ ] **Step 3: Freeze the brief**

Write both JSON and human-readable Markdown. After their SHA-256 values are
recorded in `input_freeze.json`, do not conduct further open-ended reference
search.

---

### Task 3: Select Music With Durable License Evidence

**Files:**
- Create: `.tmp/canon67_150s_hero_cut/research/music_candidates/**`
- Create:
  `.tmp/canon67_150s_hero_cut/research/music_license_manifest.json`

**Interfaces:**
- Consumes: director energy intent and official library pages.
- Produces: no more than three auditioned tracks, no more than two selected
  tracks, exact files/hashes and review-only rights evidence.

- [ ] **Step 1: Search only permitted official sources**

Use Pixabay Music, YouTube Audio Library, or Mixkit Music. Do not use arbitrary
YouTube uploads, stream rips, reposts, mirrors, commercial songs, or an
unverified `no copyright` claim.

- [ ] **Step 2: Inspect and shortlist at most three tracks**

Prefer instrumental tracks whose duration and energy structure can support a
150-second three-act film. Record title, artist, URL, library, duration, mood,
instrumentation, vocal presence, anticipated edit role, and rejection reason
for unselected candidates.

- [ ] **Step 3: Download from the official page and capture rights evidence**

For each downloaded track, preserve the original file, SHA-256, official track
page, download timestamp, applicable license URL, local terms snapshot or
screenshot, attribution text, Content ID/certificate information, platform
scope, commercial-use statement, and restrictions.

- [ ] **Step 4: Write the fail-closed license decision**

The manifest must contain:

```json
{
  "artifact_role": "hero_cut_music_license_manifest",
  "delivery_allowed": false,
  "review_only": true,
  "selected_track_count": 1,
  "selected_tracks": [],
  "rejected_tracks": [],
  "blind_spots": []
}
```

`selected_track_count` may be `1` or `2` and must equal the selected list.
Stop if no candidate has readable official license evidence.

- [ ] **Step 5: Probe selected audio**

Use the existing soundtrack probe to record duration, streams, loudness, vocal
analysis, beat candidates and energy. Preserve raw probe output; do not label a
track instrumental from filename alone.

---

### Task 4: Write The Director Treatment And Layered Edit Plan

**Files:**
- Create: `.tmp/canon67_150s_hero_cut/director/baseline_diagnosis.md`
- Create: `.tmp/canon67_150s_hero_cut/director/director_treatment.json`
- Create: `.tmp/canon67_150s_hero_cut/director/director_treatment.md`
- Create:
  `.tmp/canon67_150s_hero_cut/director/hero_edit_decision_plan.json`
- Create:
  `.tmp/canon67_150s_hero_cut/director/creative_decision_trace.json`

**Interfaces:**
- Consumes: control freeze, actual baseline, source evidence, reference brief,
  music probes and license manifest.
- Produces: a complete 150-second four-layer plan and initial decision lineage.

- [ ] **Step 1: Inspect the baseline and source evidence**

Read the full baseline perception wall and timing artifacts. Inspect full
resolution source evidence for every proposed window change. Record what the
baseline does well and the three to seven highest-leverage creative weaknesses.

- [ ] **Step 2: Write one coherent director thesis**

Define story arc, audience feeling, opening hook, section transitions, energy
peaks/valley, ending landing, shot-duration strategy, repetition controls,
source-audio policy, music structure, text restraint and effect restraint.

- [ ] **Step 3: Build the exact layered plan**

The plan must contain picture, audio, text and effects layers with exact
timeline ranges. Picture entries must carry source path/hash, asset ID, clip ID,
source in/out, timeline in/out, crop, speed, transition and still treatment.
Require all and only the frozen 42 distinct asset IDs and `150.0 +/- 0.5`
seconds.

- [ ] **Step 4: Seed the decision trace**

Every nontrivial deviation from baseline receives a stable ID, coordinate,
before/after state, story purpose, expected audience effect, parameter values,
evidence refs, origin and provisional distillation class.

- [ ] **Step 5: Pre-render validation**

Fail before rendering on missing source/hash, a 43rd asset, an omitted frozen
asset, overlap/gap beyond the chosen transition model, invalid music evidence,
or an untraceable decision.

---

### Task 5: Render And Review Hero v1

**Files:**
- Create: `.tmp/canon67_150s_hero_cut/director_sandbox/**`
- Create: `.tmp/canon67_150s_hero_cut/versions/v1/**`

**Interfaces:**
- Consumes: validated layered edit plan and selected licensed music.
- Produces: first complete Hero candidate, objective QA, perception evidence and
  stable-ID findings.

- [ ] **Step 1: Choose the least custom execution surface**

Use registered tools and Workbench where they express the plan. Use FFmpeg or
the installed Remotion runtime for unsupported decisions. Any custom script,
composition or config must stay in `director_sandbox/**` and record its command
and dependency provenance.

- [ ] **Step 2: Render Hero v1 once**

Render H.264/AAC, 1280x720, 30 fps, `150.0 +/- 0.5` seconds. Preserve the exact
plan used, command log, output hash and stream probe.

- [ ] **Step 3: Run objective media checks**

Require decode success, video/audio streams, no fatal black range, no audio
clipping, correct duration, 42-ID lineage, text-plan equality, and selected
music hash equality. Objective failure blocks creative review.

- [ ] **Step 4: Generate perception evidence**

Run full-film perception sampling and produce a wall, timing report, shot-length
statistics, repetition/family report, audio-energy plot or data, and sampled
opening/transition/peak/ending evidence.

- [ ] **Step 5: Perform director self-review**

Actually inspect the rendered evidence. Write `findings_v1.json`, separating
objective defects from taste findings. Each finding needs coordinate, evidence,
severity, proposed change, affected layers and expected benefit.

---

### Task 6: Perform At Most Two Evidence-Driven Revisions

**Files:**
- Create when justified: `.tmp/canon67_150s_hero_cut/versions/v2/**`
- Create when justified: `.tmp/canon67_150s_hero_cut/versions/v3/**`

**Interfaces:**
- Consumes: the prior immutable version and its findings.
- Produces: a final director-selected version with semantic diffs and no more
  than three total creative renders.

- [ ] **Step 1: Decide whether v2 is justified**

If v1 has no material finding, retain it. Otherwise freeze `revision_plan_v2`
listing stable IDs, affected layers and expected benefit before rendering.

- [ ] **Step 2: Render and verify v2 once**

Preserve v1. Produce semantic diff, objective QA, perception evidence and
director findings for v2. Update the creative decision trace rather than
rewriting prior decisions.

- [ ] **Step 3: Decide whether v3 is justified**

Create v3 only for remaining high-impact evidence-backed findings. Do not use a
third render merely because the budget exists.

- [ ] **Step 4: Render and verify v3 once when authorized by findings**

Preserve v1/v2 and repeat the same evidence shape. A fourth creative render is
forbidden without a new owner work order.

- [ ] **Step 5: Select the final Hero version**

Write `director_final_selection.json` comparing version hashes and explaining
the choice. Copy, do not mutate, the selected media to `final/hero_cut.mp4`.

---

### Task 7: Build A Blind Owner Review Packet

**Files:**
- Create: `.tmp/canon67_150s_hero_cut/review/**`
- Create: `.tmp/canon67_150s_hero_cut/final/hero_cut_manifest.json`
- Create: `.tmp/canon67_150s_hero_cut/final/agent_attestation.json`
- Create: `.tmp/canon67_150s_hero_cut/final/worker_report.md`

**Interfaces:**
- Consumes: immutable baseline and selected Hero version.
- Produces: owner-reviewable X/Y candidates, sealed identity mapping, evidence
  index and unset verdict.

- [ ] **Step 1: Freeze baseline and Hero hashes again**

Require the original baseline hash and the chosen Hero hash. Revalidate all 42
source hashes and the selected music hash.

- [ ] **Step 2: Randomize X/Y once and seal the mapping**

Create byte-identical copies named `candidate_X.mp4` and `candidate_Y.mp4`.
Write the mapping and randomization evidence only to `comparison_seal.json`.
The owner review index must not reveal filenames, hashes, or wording that leaks
which candidate is Hero.

- [ ] **Step 3: Create comparison aids**

Produce a full review index plus bounded dynamic comparisons for opening,
first transition, technical climax, emotional transition and ending. Do not
alter the audio of X/Y candidates.

- [ ] **Step 4: Write the unset owner verdict**

Use exactly these verdict choices:

```json
[
  "HERO_PREFERRED",
  "BASELINE_PREFERRED",
  "NO_CLEAR_PREFERENCE",
  "BOUNDED_HERO_REVISION_REQUESTED"
]
```

Keep creative and delivery flags false.

- [ ] **Step 5: Write manifest and attestation**

Record all paths/hashes, reference and music evidence, render versions,
perception artifacts, decision trace, actual inspection methods, commands,
deviations, blind spots, skipped actions, pre/post git state and the claim
boundary.

- [ ] **Step 6: Final validation**

Require valid UTF-8/JSON, no suspicious Chinese corruption, all evidence paths
and hashes readable, objective QA PASS, baseline/source preservation, no files
modified outside the committed planning documents and ignored sandbox, and:

```powershell
git diff --check
```

Do not run the full unit-test suite because production code is unchanged.

- [ ] **Step 7: Stop for the owner**

Final state:

```text
WAITING_OWNER_150S_HERO_CUT_BLIND_VERDICT
```

Do not reveal the X/Y mapping, upload externally, start capability distillation,
or claim creative approval/delivery.
