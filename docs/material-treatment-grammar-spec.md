# Material Treatment Grammar Spec

Updated: 2026-06-08

Status: draft for implementation

Relationship: this spec **snaps on top of** `docs/editing-intent-sequence-grammar-spec.md`.
That spec owns the *structural* linkage — why a shot exists, when to cut, when to
hold, and the SPEC→BUILD→VERIFY ownership. This spec owns the *material* linkage:
given a segment's content shape, decide **which treatment** materializes each shot
slot, **how many** materials it needs, and **how the four material lanes (video /
photo / subtitle / music) co-vary**. Neither spec introduces a new render backend.

## Why this exists

Today material selection is coarse and uncoupled. The system knows a segment "uses
a photo" but not *why* or *how*: it falls back to one rule — `1 photo = 1 still` —
so photos either hold too long or "just keep jumping" with no motivation. Clip
selection is bolted to subtitles and nothing else. The result is a correct-but-dead
edit.

```text
Current:   pick material that matches the query  +  attach a subtitle
Target:    content shape -> treatment -> material count -> paired lanes -> a told segment
```

A soulful narration plus a structured spec should be enough to present a segment
that tells a story. The missing piece is the grammar that turns "what this segment
is about" into "how its materials are arranged."

## Core principle

```text
Content shape decides the treatment.
The treatment decides how many materials and how they are paired.
Coverage checks the derived quantity, not just presence.
```

A calm emotional beat is one held photo. An enumeration ("the kinds of vegetables")
is a beat-locked photo stack with one label per item. A fast story bridge is a
2–4 shot quick-cut that compresses time. These are different *treatments* of the
same media type, chosen by content — not one default.

## The missing dimension: `content_pattern`

`editing-intent-sequence-grammar-spec.md` already gives a segment a `segment_role`
(opening/development/...) and `sequence_grammar.required_functions`
(establish/action/detail/result). Those answer "where in the story" and "which
beats." They do **not** answer "what *shape* is the content," which is what selects
photo-stack vs single-hold.

Add `content_pattern` to the segment's `editing_intent` (Node 3):

```json
{
  "editing_intent": {
    "segment_role": "development",
    "content_pattern": "enumeration",
    "continuity_priority": "low",
    "visual_variety_priority": "high"
  }
}
```

Allowed `content_pattern` values and their default treatment:

| content_pattern | meaning | default treatment | default lanes |
|---|---|---|---|
| `emotional` | a feeling / memory / payoff moment | `single_hold` (slow_push) | photo or 1 clip · music swell or 留白 · narrative card |
| `establishing` | set a place / mood | `single_hold` or `video_primary` | wide clip/photo · music defines tone · optional card |
| `enumeration` | a list/catalog ("types of X", menu) | `photo_stack_beat` | N stills on the beat · **per-item label captions** · fast music · no narration |
| `process` | ordered steps (a how-to / a flow) | `stepped_sequence` (video, photo fallback) | ordered clips/stepped stills · optional narration · steady music |
| `bridge` | compress time / connect two beats | `quick_cut_bridge` | 2–4 stills/clips fast · no/low text · beat-driven |
| `action` | a continuous motion/event | `video_primary` | clip preferred · diegetic optional · light text |
| `testimony` / `proof` / `identity` | a person/claim/evidence | `real_material_only` (no stock/generated) | real clip/photo · keep original audio · name-super |

`testimony/proof/identity` inherits the honesty guard from `stock_first` and the
roadmap: it must never be satisfied by stock or generated material.

## Treatment catalog

Each treatment is a concrete, provider-neutral arrangement that BUILD can execute
with primitives that already exist (per-slot still, kenburns, collage, beat→slot
assignment, ffmpeg concat). A treatment expands ONE sequence-grammar function into
one or more concrete shot slots.

```text
single_hold      one media, one slot, long hold, motion = slow_push|pan|none
photo_stack_beat N stills, each bound to one beat slot, optional per-item label
stepped_sequence ordered slots (video preferred), photo fallback as stepped stills
quick_cut_bridge 2–4 short slots, beat- or whip-driven, time-compression
video_primary    one or few video windows, cut on action_completed
collage          2–N stills composited in one frame (group/簇), one slot
```

A treatment is attached per shot slot at Node 9 (see below), so a single segment
can mix treatments (e.g. an establishing hold, then an enumeration stack).

## Quantity is derived, never guessed

The number of materials a segment needs is a function of treatment + beat grid +
duration, not an author guess:

```text
single_hold        n_required = 1
video_primary      n_required = 1..few (by max_single_source_sec)
quick_cut_bridge   n_required = ceil(segment_sec / bridge_shot_sec)         (2..4 typical)
stepped_sequence   n_required = number of steps in the process
photo_stack_beat   n_required = number of enumerated items, clamped to the
                   beats available in the segment window (beat grid from Node 5)
collage            n_required = items to composite (one slot)
```

Worked example — "today's beans come from three origins" (enumeration), segment
window has 8 beats: `content_pattern=enumeration` → `photo_stack_beat` →
`n_required = 3 items` → 3 stills on 3 beats (or 6 if 2 photos/item), each with an
origin label. Node 2 coverage then asks "do we have ≥3 origin photos?" instead of
"is there any photo?" — so a thin pool is correctly flagged `weak`, not passed.

## Lane co-variation (the four-way pairing)

The treatment drives all four material lanes together. This is the part that is
currently uncoupled.

| treatment | video/photo lane | subtitle lane | music lane |
|---|---|---|---|
| `single_hold` (emotional) | 1 still slow_push / 1 clip | full-screen **narrative card** | swell or **留白 (drop a beat)** |
| `photo_stack_beat` (enumeration) | N stills on beat | **per-item `label`** (one name per still) | fast, on-beat, no duck |
| `quick_cut_bridge` | 2–4 fast stills/clips | none or single short label | beat-driven, energetic |
| `stepped_sequence` (process) | ordered clips/stepped stills | optional step `label`/narration | steady, low |
| `video_primary` (action) | clip | light label, no full card | steady; duck if diegetic |
| `real_material_only` (testimony) | real clip/photo, original audio | **name_super** + ASR subtitle (real speech) | duck under speech |

Rule: a segment's `subtitle_strategy` / `text_layer_strategy` / `music_strategy`
choices from `editorial_design.json` are **defaults**; the per-segment treatment may
override them within the editorial policy. A treatment that needs per-item labels
(enumeration) must not be silently rendered with one narration line.

## Node changes (deltas on top of editing-intent-sequence-grammar-spec.md)

### Node 3: Contract

Build:
- Add `editing_intent.content_pattern` (enum above).
- Optional explicit override `material_treatment` per segment when the director
  wants to force a treatment; otherwise BUILD resolves it.

```json
{
  "segment": 4,
  "editing_intent": { "content_pattern": "enumeration", "visual_variety_priority": "high" },
  "material_treatment": {
    "treatment": "photo_stack_beat",
    "items": ["origin: Ethiopia", "origin: Colombia", "origin: Guatemala"],
    "label_per_item": true,
    "reason": "列舉產地,照片堆疊對拍,每張帶產地名"
  }
}
```

Verify:
- `content_pattern` must be present or defaulted from `segment_role`
  (opening/closing → `establishing`/`emotional`; montage → `bridge`/`enumeration`
  only when items are declared).
- `material_treatment` must not name a provider, file, or backend.

### Node 2: Material Coverage

Build:
- Compute `n_required` per segment from the resolved treatment + beat grid.
- Report coverage against `n_required`, extending the spec's `function_coverage`:

```json
{
  "segment": 4,
  "treatment": "photo_stack_beat",
  "n_required": 3,
  "n_available": 1,
  "coverage": "weak",
  "variety": { "unique_sources": 1, "stock_similarity_risk": "high" },
  "next_action": "await_material | request_generated_asset | revise:director"
}
```

Verify:
- An enumeration/stack/sequence segment with `n_available < n_required` is `weak`
  or `missing` even if one clip exists.
- A `single_hold` segment is satisfied by 1 strong candidate.

### Node 8: Build Profile

Build:
- Add treatment thresholds to `editing_policy`:

```json
{
  "editing_policy": {
    "treatment_defaults_by_pattern": {
      "emotional": "single_hold",
      "enumeration": "photo_stack_beat",
      "process": "stepped_sequence",
      "bridge": "quick_cut_bridge"
    },
    "stack_shot_sec_by_mode": { "rhythmic_mv": [0.4, 0.9], "warm_documentary": [0.8, 1.6] },
    "max_stack_items": 12,
    "bridge_shot_sec": [0.4, 1.0]
  }
}
```

Verify:
- Treatment defaults load when the contract omits `material_treatment`.
- Stack/bridge shot lengths obey the active mode (rhythmic_mv faster than
  warm_documentary). No treatment may imply Remotion/Blender.

### Node 9: Assembly (where treatment becomes shot slots)

Build:
- Resolve treatment (explicit `material_treatment` > pattern default), then expand
  the sequence-grammar function into concrete `shot_slots`, carrying treatment and
  per-item label/lane decisions onto each slot:

```json
{
  "segment": 4,
  "treatment": "photo_stack_beat",
  "shot_slots": [
    { "slot": "4.1", "function": "detail", "treatment": "photo_stack_beat",
      "media": "photo", "target_duration_sec": 0.7, "label": "Ethiopia",
      "beat_index": 12, "candidate_requirements": { "min_candidates": 1 } },
    { "slot": "4.2", "function": "detail", "treatment": "photo_stack_beat",
      "media": "photo", "target_duration_sec": 0.7, "label": "Colombia", "beat_index": 13 },
    { "slot": "4.3", "function": "detail", "treatment": "photo_stack_beat",
      "media": "photo", "target_duration_sec": 0.7, "label": "Guatemala", "beat_index": 14 }
  ],
  "execution_plan": {
    "subtitles": { "mode": "per_item_label" },
    "music": { "duck_music": false }
  }
}
```

Verify:
- Number of generated slots for a stack/sequence equals `n_required` (clamped to
  available beats); a 1-slot expansion of an enumeration segment is a failure.
- Each stack slot binds to a distinct beat from Node 5's grid.
- `execution_plan` lane decisions match the treatment's lane row above.

### Node 10: Timeline

Build:
- Bind each treatment slot to a concrete window; for `photo_stack_beat`/
  `stepped_sequence` write one clip per still with its `label`, `still_treatment`,
  `beat_index`, and `cut_reason: "beat" | "next_item"`.

Verify:
- Timeline preserves `treatment`, `label`, `beat_index`, `still_treatment` trace.
- Stack stills land on the beat grid (cut times ≈ beat times within tolerance).

### Node 11: Editor Review

Build — add treatment-fit checks to the visual-fatigue audit:

```text
treatment_fit:
  enumeration segment rendered as a single hold        -> fail (collapsed stack)
  stack item count != intended items (lost/duplicated) -> fail
  bridge segment held as one long shot                 -> fail (no compression)
  single_hold emotional shot chopped into a montage    -> warn (fought the intent)
label_pairing:
  per-item-label treatment missing labels on stills    -> fail
beat_lock:
  stack/bridge cut times not aligned to beat grid      -> warn
```

Routing:
```text
treatment collapse / wrong count -> editor (Node 9)
missing labels                    -> writer / subtitle
material count short              -> curator / await_material (from Node 2 n_required)
```

### Node 12: Verify

- Surface treatment-fit and label-pairing findings into `editorial_qa.json`
  (the cross-artifact reviewer from the sequence-grammar spec). The reviewer checks
  that the rendered arrangement matches the declared content_pattern + treatment,
  e.g. an enumeration segment actually reads as a labeled stack, not a random jump.

## Worked examples (the user's cases)

```text
早晨咖啡(溫和):
  content_pattern=emotional -> single_hold -> n_required=1
  1 張 slow_push 長 hold + 全螢幕敘事卡 + 音樂留白一拍。  (現在就對)

介紹蔬菜/水果種類(列舉):
  content_pattern=enumeration -> photo_stack_beat -> n_required=#items
  每種一張、對拍、每張帶品名 label、快音樂不 duck。
  Node 2 缺張數 -> weak -> 補料/生成,不再「一直跳」。

故事快橋段(壓縮時間):
  content_pattern=bridge -> quick_cut_bridge -> n_required=ceil(sec/shot)
  2–4 張快切把過程濃縮,低/無文字,beat 帶。

沖煮流程(步驟):
  content_pattern=process -> stepped_sequence
  影片優先;缺片用分步 stepped stills,可帶 step label,音樂穩定。
```

## Mode interaction

Treatment shot lengths and whether a `single_hold` is allowed depend on the
editorial `mode` from the sequence-grammar spec:

```text
warm_documentary : longer holds OK; stacks slower (0.8–1.6s); emotional single_hold preferred
rhythmic_mv      : discourage single_hold for non-emotional; stacks fast (0.4–0.9s)
story_documentary: stepped_sequence/process favored; motivated bridges
training_recap   : mixed; enumeration for equipment/skills, single_hold for ceremony
```

## Implementation order

1. Add `editing_intent.content_pattern` schema + default-from-`segment_role`.
2. Add treatment resolver (explicit override > pattern default) + `editing_policy`
   treatment thresholds in `build_profile`.
3. Derive `n_required` and extend Node 2 coverage to check it.
4. Expand Node 9 shot slots per treatment (stack/sequence/bridge), carrying labels
   and beat indices.
5. Bind per-still slots + labels in Node 10 timeline; align to Node 5 beat grid.
6. Add treatment-fit + label-pairing checks to Node 11; surface in `editorial_qa`.
7. Two E2E fixtures: an enumeration segment that must render as a labeled stack;
   an emotional segment that must stay a single hold.

## Non-goals

- Do not introduce a new render backend; treatments use existing primitives.
- Do not force stacks/cuts on emotional or establishing content.
- Do not let `enumeration`/`bridge` apply to `testimony/proof/identity` — the
  honesty guard still forbids stock/generated substitution there.
- Do not put provider/file/template choices in SPEC; they belong in BUILD.
