# Canon 67 — 540 秒剪輯邏輯盲測 A/B

## Goal

由兩個彼此隔離的 agent，使用同一批 Canon 67 原始素材證據，各自提出一套可執行但不渲染的 540 秒紙上剪輯。測試 Hermes 結構化導演流程與自由導演流程，哪一種能產生較清楚、較少無意義重複、較符合素材真實性的故事。

## Shared frozen inputs

- Raw source root: `C:/Users/user/Downloads/微電影素材/_整理後`
- Neutral wall: `.tmp/canon67_540s_route_acceptance/stage3/source_scan_v2/verify/material_wall/`
- Evidence contact sheet: `.tmp/canon67_540s_route_acceptance/stage3/l0_semantic_review_v1/material_understanding_contact_sheet.jpg`
- Evidence matrix: `.tmp/canon67_540s_route_acceptance/stage3/l0_semantic_review_v1/material_understanding_matrix.json`

The matrix may be used for source paths, keyframes, durations, and objective observations. Existing story labels are not ground truth.

## Blind boundary

Both variants must not read:

- the other variant's output directory;
- `stage1/story_soul_blueprint.json`;
- `stage2/` or `stage4/` story artifacts;
- `stage5/` picture plans, ranking reports, storyboard previews, or effects;
- prior SOL/Fable creative verdicts other than the owner feedback embedded in the dispatch prompt.

No production code, tests, Skills, registry, Runbook, source media, or git state may be modified. No render, audio processing, effect design, web search, upload, commit, or push.

## Variant A — Hermes material-first director

Output root: `.tmp/canon67_editing_logic_ab/variant_a/`

Use a structured material-first method: immerse, cluster by real event, identify action phases, assign each event cluster to at most one chapter by default, then derive the story. Reuse across chapters requires an explicit callback/contrast reason.

## Variant B — free director

Output root: `.tmp/canon67_editing_logic_ab/variant_b/`

Ignore existing pipeline story doctrine. Act as an experienced documentary/editorial director. Immerse in the same evidence, decide independently what the footage is actually about, and design the strongest honest 540-second film. Existing Hermes categories are optional and must not constrain the concept.

## Required outputs per variant

1. `editing_logic.json`
2. `editing_logic.md`
3. `evidence_ledger.json`

`editing_logic.json` must include:

- one-sentence thesis and intended final feeling;
- total duration exactly 540 seconds;
- ordered chapters with start/end/duration;
- per chapter: unique narrative job, event clusters, progression grammar, candidate asset IDs/source paths, approximate source windows when known, new information contributed, and why the chapter cannot be merged with another;
- event-cluster allocation table with default cross-chapter exclusivity;
- every intentional reuse with semantic reason;
- rejected material families and reasons;
- scarcity/gap report;
- proposed human checkpoint questions, maximum five;
- no effect implementation, no music selection, no render command.

## Acceptance

- Duration sums to exactly 540 seconds.
- Every chapter has a distinct narrative job and introduces new information.
- Every selected event cluster has evidence references.
- No unexplained event-cluster reuse across chapters.
- The logic remains executable by a later worker without inventing a new story.
- Chinese artifacts decode as UTF-8 without U+FFFD or suspicious `????`.
- Final worker chat summary is at most 20 lines; detailed evidence stays in files.

## Stop state

Each worker stops at `WAITING_INTEGRATOR_CANON67_EDITING_LOGIC_AB_REVIEW`. Creative approval and delivery flags remain false.
