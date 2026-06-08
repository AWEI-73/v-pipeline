# Narrative Blueprint Spec

Updated: 2026-06-08

Status: draft for implementation

Relationship: this is the **top layer (WHY)** of a three-tier front-of-pipeline
stack. It sits above both:

```text
WHY       narrative-blueprint-spec.md     prose: what the film says and why it moves
HOW-struct editing-intent-sequence-grammar-spec.md   structure: why each cut/hold exists
HOW-matl  material-treatment-grammar-spec.md          material: content -> treatment -> count -> lanes
```

The blueprint is the **single source of the film's soul, in human language**,
written before any structured artifact. The two HOW specs are *compiled down* from
it. This spec defines the blueprint's format, how it compiles into
`editorial_design.json` / `brief.json` / `segment_contract.json`, and the two-way
trace gate that keeps the prose executable instead of decorative.

## Why this exists

The pipeline jumps to structured JSON at the very first step. Structured specs are
good at per-segment executable intent but they *decompose* the story, and
decomposition loses the throughline. Nothing currently holds the whole film as one
coherent argument — the thing a director writes first: "this film is about X; it
opens quiet, builds to the craft, turns on the single perfect moment, lands on a
small complete morning."

The roadmap already named this as the #1 upstream risk: *"真正的上游風險是『沒有敘事
脊椎、影片流於形式』"* — and called for `narrative.thesis / arc / big_story /
mode_plan`, with `segments[].core.story_purpose` laddering back to the arc. The
blueprint **is** that narrative spine, expressed as prose at the very top.

```text
Without a blueprint: precise structure with no center -> a beautiful empty shell.
With a blueprint:    one thesis every shot serves -> a told story.
```

## Core principle

```text
Soft in expression, hard in traceability.
The prose carries the soul; an anchor index makes it referenceable;
a two-way gate guarantees every beat is realized and every shot ladders back.
```

The blueprint must never become a free-floating essay that hides un-executed
intent (roadmap C0: the runtime must not silently drop creative decisions). It is a
*compiled source*, not a parallel truth.

## Artifacts

Two files, mirroring the repo's existing "prose + structured index" pattern
(e.g. `material_map.md` + `materials_db.json`):

### `blueprint.md` — the prose (the soul)

Human- or agent-written natural language. Sections:

```text
# Thesis        one sentence: what this film is ultimately saying
# Audience       who it is for and what they should feel by the end
# Big Story       a few paragraphs: the whole story/argument as 起承轉合
                  (setup -> develop -> turn -> resolve), in prose, with the
                  emotional arc made explicit
# Stakes/Why      why this matters; the feeling it must leave
# Anti-goals      what this film must NOT become (tone, cliché, dishonesty)
```

This file is what a human reads to feel the film. It is not parsed for execution
directly — it is indexed by `blueprint.json`.

### `blueprint.json` — the thin structured index (the handle)

Extracted from `blueprint.md` (by the agent that writes it). This is what
downstream structure cites, so prose stays free but becomes addressable and
gate-able:

```json
{
  "artifact_role": "narrative_blueprint",
  "version": 1,
  "thesis": "A quiet morning, done with care, is a small complete thing.",
  "intended_feeling": "warm, calm, quietly proud",
  "mode_hint": "warm_documentary",
  "beats": [
    { "id": "B1", "role": "setup",   "summary": "the city and a cafe wake up", "intended_feeling": "still, anticipatory", "prose_ref": "Big Story ¶1" },
    { "id": "B2", "role": "develop", "summary": "the craft: grind, tamp, pour",  "intended_feeling": "focused, building",   "prose_ref": "Big Story ¶2" },
    { "id": "B3", "role": "turn",    "summary": "the single perfect pour",       "intended_feeling": "peak, held breath",   "prose_ref": "Big Story ¶3" },
    { "id": "B4", "role": "resolve", "summary": "one finished cup in warm light", "intended_feeling": "complete, warm rest", "prose_ref": "Big Story ¶4" }
  ],
  "anti_goals": ["no corporate ad gloss", "no fake claims about a specific shop"]
}
```

Rules:
- `beats[].id` are stable anchors. Structure cites them; the gate counts them.
- The blueprint contains NO provider/file/backend choices and NO per-shot timing.
  It is about meaning, not mechanics.
- `mode_hint` and `intended_feeling` are hints to the HOW layers, not bindings.

## The two-way trace gate

This is what makes the prose executable without forcing it into rigid fields.

```text
Forward (every shot ladders back):
  each segment.core.blueprint_ref must name a real beats[].id
  -> a segment that serves no beat is flagged (orphan_segment)

Backward (every beat is realized):
  each beats[].id must be referenced by >= 1 segment
  -> an unrealized beat is BLOCKING (dropped_beat) before completion

Thesis alignment (the whole reads as one thing):
  Node 12 editorial_qa checks the final film coheres to thesis + arc order
  -> beats out of order, or a film that contradicts the thesis, fails
```

`dropped_beat` is blocking because a missing beat means the film literally does not
tell the story it promised — the exact "hollow form" failure the roadmap warns of.

## Node changes

### Node 0-pre: Blueprint Intake (video-workflow)

Review:
`video-workflow` today does light brainstorming and jumps to `brief.json`. It
should instead first remove ambiguity and produce the blueprint — the model's job
is "vague request -> structured SPEC," and the blueprint is the first structured
output of that judgment (prose + anchor index).

Build:
- From a vague user request, the clarifier asks targeted questions, then writes
  `blueprint.md` + `blueprint.json`.
- If the request is ambiguous on thesis/feeling/audience, ASK before writing —
  do not invent a thesis silently.
- Index both in `artifact_manifest.json`.

```text
vague request -> video-workflow clarify -> blueprint.md + blueprint.json
             -> editorial_design.json (Node 0A) -> brief.json (Node 0) -> contract (Node 3)
```

Verify:
- A blueprint with no thesis or no beats is incomplete -> ask / block.
- Anti-goals present so later layers can be checked against them.

### Node 0A / Node 0: editorial_design.json + brief.json

Review:
The editorial-intent spec's `editorial_design.json` and `brief.json` should be
*compiled from* the blueprint, not authored independently.

Build:
- `brief.json.editorial_intent.mode` defaults from `blueprint.json.mode_hint`.
- `editorial_design.energy_curve` should follow the blueprint beats' feelings.
- Carry `blueprint_version`/hash so drift is detectable.

Verify:
- editorial_design energy curve length/order is consistent with blueprint beats.
- If the blueprint changes, downstream artifacts are marked stale.

### Node 3: Contract

Build:
- Every segment carries `core.blueprint_ref` (one or more beat ids it serves) and
  keeps its existing `story_purpose`:

```json
{
  "segment": 3,
  "core": {
    "story_purpose": "用快剪手部特寫堆疊手藝的密度",
    "blueprint_ref": ["B2"]
  }
}
```

Verify:
- `blueprint_ref` resolves to real beat ids (else orphan_segment).
- Contract validation stays provider/backend neutral.

### Node 2 / Node 9 / Node 10

- No new ownership; they inherit `blueprint_ref` as trace on shot_slots and
  timeline clips so Node 11/12 can show "this clip serves beat B2."

### Node 11: Editor Review

Build:
- Add `beat_coverage` to the deterministic review: which beats are realized, which
  segments are orphans.

Verify:
- `dropped_beat` (a beat with zero realizing segments) is a blocking finding.
- `orphan_segment` (serves no beat) is at least a warn (often means scope creep).

### Node 12: Verify (editorial_qa)

Build — extend the cross-artifact `editorial_qa.json` reviewer (owned by the
editing-intent spec) with blueprint dimensions:

```text
thesis_alignment   : does the finished film cohere to blueprint.thesis?
arc_order          : do realized beats appear in blueprint beat order?
beat_completeness   : every beat realized (mirrors Node 11 beat_coverage)
anti_goal_respect   : film does not drift into any blueprint.anti_goals item
```

Rules (inherited): the main reviewer reports mismatches only; it does not mutate
artifacts or invent new requirements. Findings carry a `route` for Node 14.

### Node 14: Revision

- A `dropped_beat` routes to the smallest fix: add/repurpose a segment for that
  beat (target Node 3/9), not a full restart.

## Worked example (the coffee film)

```text
blueprint.thesis: "A quiet morning, done with care, is a small complete thing."
beats: B1 setup / B2 craft / B3 the pour / B4 finished cup

segment_contract:
  seg1.blueprint_ref=[B1]  seg2.blueprint_ref=[B1]
  seg3.blueprint_ref=[B2]  seg4.blueprint_ref=[B3]
  seg5.blueprint_ref=[B2]  seg6.blueprint_ref=[B4]

Node 11 beat_coverage: B1,B2,B3,B4 all realized -> ok
Node 12 editorial_qa: arc order B1->B2->B3->B4 holds; thesis alignment pass
If seg4 (the pour, B3) were dropped -> dropped_beat=B3 -> BLOCK (the film lost its turn)
```

## How the three layers compose

```text
blueprint.json.thesis + beats        (WHY: the soul, one center)
  -> editorial_design + editing_intent (HOW-struct: cut/hold reasons, pacing, sequence_grammar)
    -> content_pattern -> treatment    (HOW-matl: how materials realize each beat)
      -> shot_slots -> timeline -> render
        -> editorial_qa checks the render still says the thesis
```

Each layer narrows the one above into something executable, and Node 12 closes the
loop by checking the finished film against the top.

## Implementation order

1. `video-workflow` writes `blueprint.md` + `blueprint.json` from a clarified
   request (interactive ambiguity removal first).
2. Add `core.blueprint_ref` to the contract schema + validation (resolves to beat ids).
3. Compile `editorial_design`/`brief` defaults from `blueprint.json` (mode, energy curve).
4. Node 11 `beat_coverage` (dropped_beat blocking, orphan_segment warn).
5. Node 12 `editorial_qa` blueprint dimensions (thesis_alignment, arc_order, anti_goal_respect).
6. One E2E fixture: removing the turn beat's segment must produce `dropped_beat` and block.

## Non-goals

- The blueprint is not a shot list, not timing, not provider/file/template choices.
- Do not force a fixed beat count or a fixed arc shape; `起承轉合` is a default, not a law.
- Do not let the prose run un-compiled — no anchor index, no acceptance.
- Do not let blueprint dimensions become an opaque model opinion; Node 12 evidence
  must be traceable to artifacts, mechanical-first, optional VLM later.
