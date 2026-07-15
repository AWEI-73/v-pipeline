# Editorial Layer —Consolidated Overview

Updated: 2026-06-08. **Read this first** for the editorial ("soul") layer. It ties
together three deep-dive specs and records what is wired. The detailed specs remain
the source of truth for field shapes:

- `docs/narrative-blueprint-spec.md` —WHY (narrative spine), Claude
- `docs/editing-intent-sequence-grammar-spec.md` —HOW-structure, Codex
- `docs/material-treatment-grammar-spec.md` —HOW-material, Claude
- Decision log: `docs/archive/decisions/2026-06-08-editorial-soul-layer-and-treatment-grammar.md`

## 1. The problem it solves

The converged SPEC→render→verify pipeline produced *correct but lifeless* videos:
material selection was coarse and uncoupled from content (one rule: `1 photo = 1
still`), and nothing held the film together as one story. The editorial layer adds,
at the front of the pipeline, two missing things:

```
a narrative spine   —every shot serves one thesis (not a bag of clips)
content-driven craft —what a segment IS decides how its material is treated
                       (an enumeration becomes a labeled beat photo-stack,
                        an emotional beat stays a single slow hold)
```

Goal: turn "clip selection + subtitle" into "a told story segment".

## 2. Three-tier model

Each tier compiles the one above into something more executable. All three respect
the roadmap non-goals (no new render backend, no forced cuts, honesty guard intact,
no provider/file choices in SPEC).

| Tier | Question | Primary artifacts | Spec | Status |
|---|---|---|---|---|
| **WHY** narrative blueprint | What is this film saying? | `blueprint.md` + `blueprint.json` (thesis + ordered `beats[]`); `segment.core.blueprint_ref` | narrative-blueprint-spec | wired (gate + compile CLI) |
| **HOW-structure** editing intent | Why each cut / hold? | `editorial_design.json`; `editing_intent` / `sequence_grammar` / `pacing` / `still_image_policy`; `build_profile.editing_policy`; `shot_slots`; `visual_fatigue_audit.json`; `editorial_qa.json` | editing-intent-sequence-grammar-spec (Codex) | wired |
| **HOW-material** treatment grammar | How is each shot's material realized? | `content_pattern` —`treatment` —`n_required` —lane plan; `treatment_audit.json` | material-treatment-grammar-spec | wired + real photo-stack renderer |

## 3. Node flow (where each tier plugs in)

```
Node 0A  editorial_design.json        (Pre-SPEC, Codex direction: whole-film editorial design)
Node 0   blueprint.md -> blueprint.json + brief.json
Node 3   segment_contract.json        (+ editing_intent/content_pattern/sequence_grammar/
                                         material_treatment/pacing + core.blueprint_ref)
Node 2   material_coverage             (n_required is the count check; today via Node 11 audit)
Node 8   build_profile.json           (+ editing_policy compiled from editorial_design)
Node 9   assembly_plan.json           (resolve treatment + n_required + lane_plan; expand shot_slots)
Node 10  timeline_build.json          (concrete clips; per-still labels; beat_grid)
Node 11  editor_review + audits:
           blueprint_coverage.json     (two-way beat gate; dropped_beat BLOCKS)
           treatment_audit.json        (treatment_fit / label_pairing / beat_lock)
           visual_fatigue_audit.json   (single-source / still / density / repetition / pacing)
Node 13  render                        (ffmpeg canonical; photo_stack_beat -> N labeled stills on beat)
Node 12  verify_result.json + editorial_qa.json  (cross-artifact: does the film still say the thesis?)
Node 14  revision                      (route the smallest fix)
```

## 4. The three tiers, in one screen

### WHY —narrative blueprint (`blueprint.py`)

`blueprint.md` (prose: thesis / big story arc / emotional arc / anti-goals) is
indexed by `blueprint.json` (`thesis` + ordered `beats[]` with stable ids). Each
`segment.core.blueprint_ref` cites the beat(s) it serves. A **two-way trace gate**
(`beat_coverage`): every ref must resolve to a real beat (`invalid_ref`), and every
beat must be realized by at least one segment (`dropped_beat`, **blocking**). The runtime runs
the gate *before render* (inert when there is no `blueprint.json`), so a film that
lost a promised story beat cannot complete. `blueprint_compile.compile_blueprint_md`
turns the prose into the index; CLI `video_tools.py blueprint-compile` /
`blueprint-coverage`.

### HOW-structure —editing intent & sequence grammar (Codex)

The Codex direction adds a **Pre-SPEC editorial design intake** (`editorial_design.json`,
Node 0A): whole-film decisions on narration/subtitle/music/effects/still-image
language and an energy curve —settled *before* segment contracts so agents do not
default generic MV rules onto calm story content. From there, per segment:
`editing_intent` (mode, continuity/variety priority, effects intensity),
`sequence_grammar` (required visual functions: establish/action/detail/result),
`pacing` (preferred/max shot seconds, still-hold limits, when a long hold or a
visual change is required), `still_image_policy`, `transition_philosophy`.
`build_profile.editing_policy` turns intent into operational thresholds by mode.
Node 9 expands `sequence_grammar` into `shot_slots`. Node 11
`visual_fatigue_audit` catches dead edits (one-source-per-segment, photos held too
long, too few shots for the mode, source repetition, pacing mismatch). Node 12
`editorial_qa` is the cross-artifact reviewer: does brief —contract —assembly —timeline —verify line up, and does the finished film cohere to the thesis and arc.

### HOW-material —material treatment grammar (`material_treatment.py`)

A segment's `editing_intent.content_pattern` (emotional / establishing / enumeration
/ process / bridge / action / testimony) resolves a `treatment` (single_hold /
photo_stack_beat / quick_cut_bridge / stepped_sequence / video_primary / collage /
real_material_only), which **derives `n_required`** (count from treatment × beat grid
× items) and **co-varies the four lanes** (photo/video, subtitle, music) together —e.g. enumeration —N stills on the beat + per-item label captions + fast music.
`treatment_audit` (Node 11) checks the render honored the treatment (collapsed stack,
wrong count, missing labels, off-beat). The renderer really does it: an enumeration
segment fetches one Pexels photo per item and renders N beat-fast labeled stills.

## 5. Cross-cutting invariants (the review checklist)

- **Opt-in / inert-when-absent.** Every editorial feature is gated on an explicit
  declaration (`content_pattern`, `editing_policy`, `blueprint.json`, …). A run that
  does not opt in is byte-for-byte unaffected. This is why the canonical fixtures
  stay green.
- **Honesty guard.** `content_pattern` testimony/proof/identity and any
  `must_include` segment must never be satisfied by stock/generated material
  (`stock_first._can_use_stock`, the treatment honesty guard).
- **Soft in expression, hard in traceability.** Prose (blueprint.md) carries the
  soul; a structured index + the two-way gate make it executable, never a floating
  essay that hides un-executed intent.
- **SPEC stays provider/backend neutral.** Tool/provider/file choices live in BUILD
  (`build_profile`), never in `segment_contract.json` or the editorial artifacts.
- **ffmpeg is canonical.** No new render backend; CapCut/Remotion/Blender stay
  optional. No forced rapid cuts.

## 6. Implementation status

```
module                      role                                 wired   tests
blueprint.py                WHY gate (beat_coverage)             yes     test_blueprint
blueprint_compile.py        blueprint.md -> blueprint.json       yes     test_blueprint_compile
material_treatment.py       content_pattern -> treatment         yes     test_material_treatment
treatment_audit.py          Node 11 treatment fit                yes     test_treatment_audit
visual_fatigue.py           Node 11 dead-edit guard              yes     test_visual_fatigue
editorial_design.py         Node 0A / editing_policy source      yes     test_editorial_design
shot_slots.py               Node 9 slot expansion                yes     test_shot_slots
editorial_qa.py             Node 12 cross-artifact reviewer      yes     test_editorial_qa
mv_cut (stack renderer)     photo_stack_beat -> N labeled stills yes     test_stack_renderer
```

Audit wiring pattern (for any future audit): produce JSON in
`edit_artifacts.write_edit_artifacts` (gated/inert) —load + surface in
`dashboard_state` (`audit_data`, `NODE_AUDIT_MAP`, `AUDIT_PRIMARY_NODE`) —route in
`runtime_orchestrator._AUDIT_NODE` —list in the Node's `node_registry` outputs.

## 7. Run & verify

```powershell
# unit suite (set UTF-8 first on Windows)
$env:PYTHONUTF8=1; python -m unittest discover -s tests   # 453 OK

# real E2E fixtures (need ffmpeg + PEXELS_API_KEY in .env + yt-dlp + Ollama)
#   examples/genre_tests/stock_story_e2e   -> verify 92.5 PASS, blueprint gate live
#   examples/genre_tests/treatment_demo    -> enumeration -> 3 beat-fast labeled stills, audits PASS
python video_tools.py project-init "<name>"; python video_tools.py project-new-run --label x
# copy segment_contract.json/brief.json/material_categories.json/blueprint.json into <project>/input/
python runtime.py run --project <slug>
```

## 8. Where to read more

- Field shapes & node-by-node Build/Verify: the three specs in §intro.
- Why each decision: `docs/archive/decisions/2026-06-08-editorial-soul-layer-and-treatment-grammar.md`.
- Resume/handoff anchor: original task list is local history only; this overview
  is the conceptual map.
- Prose→edit translation: `docs/imagery-to-edit-lexicon-spec.md` (the deterministic
  imagery→enum table) + `skills/blueprint-interview.md` (elicitation) +
  `video_pipeline_core/blueprint_to_contract.py` (the compiler).
