# Prose→Contract Lexicon + Blueprint Compiler (2026-06-08)

## Context

The three-tier soul layer (blueprint / editing-intent / material-treatment) was
spec'd and the engine consumers existed (`material_treatment.resolve_treatment`,
`shot_slots.expand_shot_slots`), but a real run still produced a captioned
slideshow. Comparing a generated `graduation-demo` contract against the human gold
`66期養成班-高訓結訓影片全OK.mp4` (~368 shots / 804s / ~27.5 cuts/min) showed why:

- The blueprint→contract step emitted **1 beat = 1 segment = 1 material_hint** and
  dropped the density fields (`content_pattern` / `sequence_grammar` / `pacing`), so
  every segment rendered as one clip (~11 shots total vs the reference's 368).
- The blueprint itself was a **dry bullet outline** ("[B3|develop] 基本技能…
  {feeling: active}") — a table of contents with no imagery, pace, or audio intent.
  User's reframe (decisive): the blueprint must be **narrative, evocative, fuzzy
  PROSE**; pacing/「頻率」must be *elicited from the vision*, not filled as numbers.

The missing piece was the **prose→executable translation neuron**, plus the
elicitation front-end. Nothing deterministic connected soulful prose to the
existing enums.

## Decision

Build the translation layer + elicitation, keep judgment with the agent and make
the mechanical half deterministic. (Roadmap non-goals respected: no new render
backend, no forced cuts, honesty guard intact, no provider choices in SPEC.)

### 1. Imagery→edit lexicon (the translation neuron)
`docs/imagery-to-edit-lexicon-spec.md` — a deterministic table mapping prose signals
to the **existing** engine enums: 情緒型態→`content_pattern`, 結構→`required_functions`,
密度語感→`pace`+`preferred_shot_sec`, 聲音→`audio.role`/`original_audio_policy`,
靜照/文字→treatment/text_layer, plus 轉場語意 and an explicit **effects scope
boundary** (split-screen / kinetic title / particles / PiP = `effects_required`,
NOT auto). Numbers anchored to the reference film + mode presets. Honesty guard 🔒.

### 2. Elicitation skill
`skills/blueprint-interview.md` — the "靈魂引導": each question is engineered to
extract one lexicon dimension; a **追問階梯** pushes vague answers ("就拍訓練啊") to
concrete imagery+pace+audio; a **sufficiency gate** loops until every beat has
情緒型態/節奏/原音/感官意象/thesis-hook before writing `blueprint.md` + `blueprint.json`.
Adds `weight` (篇幅) and `chapter_music` elicitation.

### 3. Director Node-3 translation
`skills/director.md` gained a "blueprint prose → segment_contract" section that
forbids 1-beat-1-clip and wires `core.blueprint_ref`.

### 4. Compiler (the mechanical half, deterministic)
`video_pipeline_core/blueprint_to_contract.py` `compile_contract(blueprint,
decisions)` + CLI `video_tools.py blueprint-to-contract`. The agent writes a compact
per-beat `decisions.json` (content_pattern + key imagery/pace/audio/must_include);
the compiler fills defaults (functions/pace/treatment), places `editing_grammar.role`
at **segment level** (nesting it in `core` silently drops weight — the bug this
removes), wires `blueprint_ref` + `timeline_source` + per-facet `reason`, applies the
honesty trace, and validates (`spec_contract.validate_segment_contract` + two-way
`beat_coverage`, exit≠0 on failure).

### 5. Three-tier pace model
Pace is `fast | calm | hold` (was binary). **calm** maps to a cutting pace
(`visual_style.pace=fast`) with a slow `[4,8]` band, so calm sections still cut
~7s instead of rendering as 30s static holds; `hold` is reserved for genuine
speech/freeze. content_pattern defaults: action/enumeration/process/bridge→fast,
establishing/emotional/identity→calm, testimony/proof→hold.

### 6. Density-aware shot slots
`edit_artifacts.build_assembly_plan`: shot_slots previously capped at
`len(required_functions)`, so a fast 77s chapter got ~6 shots (~12s each). Now a
fast/montage segment with `pacing.preferred_shot_sec` expands to
`max(treatment_n, len(funcs), ceil(time_budget / preferred_shot_sec_upper))`
(lexicon §3). B5 peak: 6 → ~20 shots @3.9s.

### 7. Runtime wiring
`runtime_orchestrator._copy_initial_artifacts` bootstrap step "C2": when
`input/decisions.json` is present, auto-compile the dense contract via the compiler
(before the thin block-D fallback; if it writes the contract, block D skips). Also
excluded `decisions.json`/`material_categories.json` from the "single json in input/
= contract" heuristic. Inert when no decisions.json.

### 8. Bug fix
`blueprint_compile.py` thesis sentence-split no longer truncates on a digit-period
(e.g. the thesis "人生的 0.66%…" was being cut to "人生的 0.").

## Verification

- Full suite **464 OK** (was 363 at the start of the soul-layer work). New tests:
  `tests/test_blueprint_to_contract.py` (7), `tests/test_runtime_decisions_bootstrap.py` (2).
- Gold fixture `examples/blueprint_gold_66/` (blueprint.md + decisions.json →
  compiler → contract) driven deterministically: old graduation-demo = 11 shots/11
  seg (0 expand); gold = ~94 shots, fast~4s/calm~7s/hold-few; `beat_coverage` pass
  11/11; honesty guard forces `real_material_only` on all testimony/proof/identity.
- Whole-film cut-rate (~8.5/min vs reference 27.5) is now an **authoring** dial (how
  many beats are fast vs hold, weight allocation) living in `decisions.json`'s pace
  column, not an engine limit — confirming the user's thesis that the blueprint drives it.

## Consequences

- End-to-end chain is runnable: blueprint-interview (elicit) → decisions.json
  (agent judgment) → blueprint-to-contract (compile, runtime-auto) → engine
  (treatment/shot_slots, density-aware) → audits.
- Still needed: a full `final.mp4` render needs the real 66期 material pool (not in
  this env). The elicitation→decisions.json authoring remains an agent judgment step
  by design.
- Docs consolidated: superseded handoffs/design notes moved to `archive/` (see
  `archive/README.md`); live map at `docs/INDEX.md`.
