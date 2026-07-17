# Decision: Progressive editorial ambiguity loop

Date: 2026-07-17
Status: accepted for bounded implementation
Scope: Hermes Stage 0–2 story discovery and Stage 3 handoff

## SPEC

Requirement:

Prevent a fuzzy whole-video request from becoming a thin list of segment names
that a downstream worker must reinterpret. Preserve the user's intent while
removing ambiguity one level at a time, and carry decisions, reasons, evidence,
authority, remaining unknowns, and downstream interpretation bounds into Stage
3.

Why:

The Canon 67 reconstruction proved that a plausible whole-film thesis and
segment labels are not enough. Stage 3 received new A01–A11 segments but only
old Material Map need identifiers, then guessed mappings and changed accepted
segment meanings. That was not a retrieval-tool failure; Stage 2 had omitted
segment composition grammar and an evidence-need map.

Direction:

- Keep the existing Stage owners and add a thin Stage 0–2 method overlay.
- Use `propose → compare → verdict → expand → evidence check → compact`.
- Require story decision, segment story grammar, and evidence needs before
  Stage 3.
- Use deterministic validation only for completeness and binding. Human/agent
  reasoning creates the content; the validator does not judge taste.
- Default high-impact ambiguous choices to paper-edit A/B comparison, but allow
  a reasoned single-option waiver when two credible options do not exist.

Non-goals:

- No new Stage, orchestrator, selector, renderer, Material Map schema, BUILD
  schema, creative-quality score, approval gate, or delivery authority.
- No Canon 67-specific segment grammar in the generic contract.
- No claim that a complete evidence-need map proves the material exists.

## DO

Files / modules:

- `skills/editorial-ambiguity-loop.md`: the reasoning workflow and ownership
  boundary.
- `video_pipeline_core/editorial_ambiguity.py`: deterministic package validator.
- `tools/editorial_ambiguity.py`: thin CLI adapter.
- `tests/test_editorial_ambiguity.py`: valid and fail-closed contract cases.
- Existing Stage 0–2 skills, route docs, runbook, boundary matrix, and handoff:
  link to the new completion rule without duplicating the schema.

Contract:

1. `story_decision_packet.json` records hypotheses, accepted causal arc,
   decision authority, retired directions, material-deferred intent, and open
   questions.
2. `segment_story_contract.json` records each segment's factual claim, causal
   change, entry/exit state, picture roles, source-family boundary, forbidden
   substitutions, minimum unique windows, duration policy, transitions, title
   role, fallback rule, review question, and decision record.
3. `evidence_need_map.json` maps every required picture role to a factual,
   observable evidence need.
4. Cross-artifact path/hash refs and project ids bind the package.

Stage 2 is complete only when:

- high-impact unknowns are resolved or explicitly deferred;
- accepted decisions carry evidence and allowed downstream interpretation;
- each segment has a complete composition grammar;
- every required picture role has one evidence need;
- material deferral is owner-confirmed rather than inferred from retrieval
  failure;
- `tools/editorial_ambiguity.py validate` exits 0.

Compatibility:

The artifact package is additive. Existing `video_intent.json`, story-soul
blueprints, canonical `segment_contract.json`, Material Map, immutable global
editorial state, Editing Loop, and Stage 0–10 cursor remain authoritative in
their current domains. The Stage 2 package is an upstream reasoning and handoff
contract, not a competing BUILD contract.

## VERIFY

Automated checks:

- Valid three-artifact package returns `ready_for_stage3=true`.
- Open route-changing/structural unknown fails.
- Cosmetic A/B duplicates fail the distinct-causal-promise check.
- Missing evidence need for a required picture role fails.
- Cross-artifact hash drift fails.
- Unconfirmed material deferral fails.
- CLI writes a machine-readable report and uses exit status.
- Skill index, skill/tool ownership, pipeline boundaries, UTF-8, and diff
  hygiene remain green.

Forward checks:

- Fresh agents with no expected answer read only the Skill and raw fuzzy briefs
  for different video families.
- They must produce bounded artifacts without inventing facts, route ownership,
  rendering, or delivery claims.
- The Integrator validates artifacts mechanically and reviews whether the Skill
  elicited useful hypotheses, composition grammar, evidence needs, and honest
  unknowns.

Regression risks:

- Requiring A/B everywhere would create fake options and double cost; retain the
  single-option waiver.
- Too many required prose fields could become ceremonial. Forward tests must
  prove each field changes downstream interpretation or exposes a gap.
- Validator PASS may be mistaken for story quality. The report carries an
  explicit claim boundary.
- A new artifact can become stale. Path/hash binding and immutable run roots are
  required; accepted revisions must update the current handoff pointer.

### Cold-start forward-test result

Three fresh agents received only this Skill, the shared boundary, and one raw
fuzzy brief each. They wrote only isolated `.tmp` packages for a picture-driven
training recap, a speech-driven craft interview, and a mixed community event.

The first attempt exposed one documentation defect: agents understood the
reasoning loop but invented near-synonym enum values and treated relative refs
as repo-root paths. The validator failed closed. The Skill was corrected to
publish canonical vocabulary and artifact-relative path rules; no validator
relaxation was made.

Final independent read-back:

- picture-driven: 2 distinct hypotheses, 6 causal beats, 6 segments, 24 needs;
- speech-driven: reasoned single-option waiver, 4 beats, 4 segments, 14 needs;
- mixed event: 2 distinct hypotheses, 5 beats, 5 segments, 13 needs;
- all three exited 0 with `ready_for_stage3=true`, all needs remained `needed`,
  and no case selected source windows, rendered, approved, or claimed delivery.

Manual semantic review found the alternatives materially different, the single
waiver credible, and factual boundaries honest. This proves the Skill can elicit
and bind three upstream package shapes under controlled synthetic briefs. It
does not certify story quality on real material or prove Stage 3 transfer; the
capability therefore remains `experimental`.

## Decision Notes

Accepted because:

This closes the actual gap found in the long-form reconstruction without adding
another engine. LLM reasoning stays responsible for ambiguity reduction; code
only prevents incomplete or drifted decisions from silently entering Stage 3.

Search tags:

decision-log, editorial-ambiguity, stage0-stage2, story-decision,
segment-grammar, evidence-need-map, compact-to-next-level, longform
