# Reference-Aligned Pipeline Gap Analysis Report

Date: 2026-07-08

## Scope

This report answers whether the current video pipeline can produce a new reference-aligned graduation-film script package, and what gaps must be respected before asking a worker to write a different script.

Evidence used:

- Reference teardown output: `.tmp/reference_film_teardown_product_standard_20260708-161322`
- Shot-level proof output: `.tmp/shot_level_material_proof_completion_20260708-080727`
- Effect factory handoff output: `.tmp/effect_factory_integration_completion_20260708-154117`

This is a planning and script-readiness review only. It does not approve final delivery, music rights, human transcript, or story/material mapping.

## Verdict

The pipeline can support a reference-aligned no-render script package now.

It can probably support a constrained `music_subtitle_only` render rehearsal after human review accepts the known limitations.

It cannot honestly claim a reference-quality full production route yet, because the current evidence still has gaps in shot duration capacity, supervisor transcript, certification/check proof, effect integration, and music/legal review.

## Gap Table

| Capability | Current Evidence | Status | What This Means |
| --- | --- | --- | --- |
| Reference film basis | `67期結訓影片-終.mp4` selected; duplicate secondary confirmed; ffprobe duration 564.455s | PASS | There is a real benchmark to imitate structurally, not just a vague taste target. |
| Reference teardown | 4 sampled 60s windows, 240 frames, opener/middle/speech/ending contact sheets | PARTIAL | Good enough for script standard and structure; not enough for exact audio/music/edit-density teardown. |
| Product standard | `reference_product_standard.json` exists | PASS WITH CAVEATS | Usable as the benchmark language for opener, MV, title/subtitle, and closer expectations. |
| Story/soul layer | Prior soul-first package defines thesis and story arc | PARTIAL | It gives direction, but the next script must be rewritten as a fresh story, not reuse the old V-runs. |
| Shot-level material proof | 35 candidates, 27 raw usable, 6 compiled-reference-only, 2 human-review-needed | PARTIAL | There is enough to write a grounded script, but not enough to claim all beats are production-safe. |
| Duration capacity | opening 19s, training MV 131s, supervisor 9s, teacher/class 30s, closing 25.5s; total about 214.5s | PARTIAL / SHORT | Below the 240-300s five-minute target unless the script adds more accepted shots or uses deliberate bridge/effect pacing. |
| Training MV modules | 21 candidate shots, 18 raw usable | PASS FOR SCRIPT | Strongest section. The next script should lean on this as the core visual engine. |
| Supervisor source speech | 3 candidates, 0 raw usable, 1 compiled reference, 2 human-review-needed | BLOCKED | Do not build the new script around source speech unless it remains a review-required placeholder. |
| Certification/check proof | `thin_blocked_for_primary_proof` | BLOCKED / SHORTEN | The script should either shorten this beat or treat it as a standards/check bridge, not as a raw-footage claim. |
| Teacher/class intro | 4 raw usable candidates | PARTIAL | Usable, but the script should request readability/person-identification review before final. |
| Opener/closer effects | Effect contract and 4 contact-sheet proofs exist; status `ready_for_human_review` | PARTIAL | Good enough to specify designed opener/closer; not yet proof of final animated overlay quality. |
| Title/subtitle behavior | Effect line has enter/hold/exit rules and no persistent side rail | PARTIAL | New script should specify title moments and disappearance timing per section. |
| Music route | `music_subtitle_only` recommended; legal/music review not approved | PARTIAL | Script can assume music-driven MV, but cannot claim final music rights. |
| VoxCPM narration | Known lead-in provider artifact; optional route blocked for delivery narration | OPTIONAL / BLOCKED | Do not require narration for the new script. Use subtitles and music as primary; narration may be optional test only. |
| Render entry | `may_start_future_five_minute_rehearsal=true` for `music_subtitle_only` with limitations | CONDITIONAL | A render rehearsal can start only if the script explicitly accepts certification shortening and excludes unresolved source-speech claims. |

## What Is Actually Missing

1. A different script that uses the reference as a quality benchmark, not as a scene-by-scene copy.
2. A stronger material-to-story negotiation layer: each major beat must say whether it is raw proof, support, bridge, effect/title, or blocked.
3. A five-minute strategy that admits current capacity is short. Either expand accepted shots or write a safe 210-230s cut plus a 240-300s extension plan.
4. A designed opener and closer that are story functions, not decorative cards.
5. MV section logic that can vary with the story. The order is not fixed; the order must explain why the viewer moves from one training module to the next.
6. Title/subtitle pockets: chapter labels must appear, hold briefly, and leave; they must not become a permanent side rail.
7. A no-narration default. For this route, music + subtitles + source visuals are the primary delivery mechanism.
8. A supervisor/source-speech decision. Until transcript review is complete, the new script should not depend on intelligible supervisor speech.
9. A certification/check decision. Until raw proof exists, the new script should compress or bridge this beat.
10. A human review packet that lets the user approve story/material choices before render.

## Recommended Next Worker Task

Ask a worker to write a new reference-aligned script package, not to render.

The worker should use this report as construction basis and produce a different story that can flow from opening, into training MV, into people/context, and into a designed closing. The script must be detailed enough to compare against the reference standard and explicit enough to expose missing proof.

The output should include both:

- A current-capacity cut that can plausibly fit around 210-230 seconds.
- A reference-target extension plan for 240-300 seconds, naming what extra proof or pacing is needed.

The worker must not write `story_human_review_decision.json`, must not render, and must not claim music/legal approval.
