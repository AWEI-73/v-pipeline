---
name: editorial-reviewer
description: Use for the single V Pipeline Editorial Reviewer surface when persisted eye/ear/heart evidence needs an evidence-bound finding or bounded proposal across existing rubric lenses. Do not use it to repair, render, approve creative quality, or claim delivery.
---

# V Pipeline Editorial Reviewer

This is the one human/agent entry for editorial review. The runtime identity is
`editorial_reviewer`; existing `reviewer_role` values are rubric lenses and
legacy artifact vocabulary, not separate reviewer agents.

The reviewer stance is:

> Understand the intended outcome, inspect evidence, surface consequential
> differences, explain why they matter, and propose the smallest existing
> route that could resolve them. Preserve strengths. Do not manufacture faults.

Hermes V Pipeline is the legacy product alias only; new review artifacts use
`V Pipeline`.

<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "editorial-reviewer",
  "stage_owner": "verify_delivery_gate",
  "triggers": [
    "a candidate or review packet needs one bounded eye/ear/heart editorial review",
    "a persisted evidence packet can be reused or a bounded delta must be inspected",
    "an owner needs an evidence-bound finding and existing-route proposal"
  ],
  "canonical_tools": [
    {
      "tool": "video_tools.py reviewer-policy --validate-review",
      "command": "video_tools.py reviewer-policy --validate-review REVIEW.json --receipt-out editorial_review_receipt.json",
      "when": "validate an editorial_review v2 artifact or an additive editorial_review block before routing it",
      "inputs": [
        "structured editorial review",
        "timeline evidence manifest",
        "registered rubric lenses and capability IDs"
      ],
      "outputs": [
        "validation result with errors or a valid findings/proposals artifact",
        "hash-bound editorial_review_receipt.json when receipt-out is supplied"
      ],
      "stop_if": [
        "subject, evidence hash, evidence coordinate, rubric lens, route, or capability ID is unresolved",
        "the artifact claims creative approval, delivery, repair, or canonical mutation"
      ],
      "capability_id": "cap.editorial-reviewer.structured-review-validation.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": ["L5"],
      "maturity": "bounded",
      "certified_scope": "schema, evidence, route, and authority validation only"
    }
  ],
  "supporting_tools": [
    {
      "tool": "tools/timeline_review_packet.py",
      "when": "reuse the existing uniform timeline packet and its eye/ear evidence tracks",
      "inputs": [
        "candidate or reference film",
        "optional decision context JSON with locked_truth and declared finishing_contract/audio_policy",
        "optional soundtrack probe",
        "optional SRT with explicit text authority"
      ],
      "outputs": [
        "timeline_review_packet.json",
        "editorial_evidence_manifest.json",
        "reviewer_write_contract.json",
        "editorial_review.template.json",
        "wall_index.json",
        "timeline walls"
      ],
      "stop_if": [
        "the output root is not fresh",
        "subject type, soundtrack contract, subtitle authority, or wall coverage is invalid",
        "decision context subject binding is missing or does not match the reviewed subject SHA-256"
      ]
    }
  ],
  "forbidden_tools": [
    "Do not create a new Stage, orchestrator, route runner, LLM runtime, cache service, or repair worker",
    "Do not modify canonical state, render, apply a proposal, approve creative quality, or claim delivery",
    "Do not treat legacy reviewer roles as multiple agent dispatches",
    "Do not manufacture findings when strengths or evidence gaps are the truthful result"
  ],
  "capability_namespace": "cap.editorial-reviewer.*",
  "capability_lookup_owner": "verify"
}
<!-- TOOL_CONTRACT_END -->

## Review contract

Start from persisted evidence. A `timeline_review_packet.json` and its
`editorial_evidence_manifest.json` are the preferred whole-story surface. If a
decision context is exact-subject bound, read `locked_truth` before proposing fixes in
`full_context` mode. In `cold_start` mode, first record audience-visible
observations without using the locks, then classify each finding against them
before final output. A fresh review records the exact manifest items reused and
regenerated; unknown or mismatched subject/hash state fails closed.

Timeline wall inspection uses one fresh/disposable reviewer context. That
context returns only the immutable review artifact to the parent/orchestrator;
the parent validates and routes findings but does not rewrite them. This is one
reviewer identity, not a multi-reviewer consensus system.

The output is `editorial_review` version 2, or an additive `editorial_review`
block on a legacy `artifact_review` version 1. It records:

- `reviewer_identity=editorial_reviewer` and one or more existing
  `rubric_lenses`;
- `full_context` or `cold_start` mode, subject binding, inspection scope,
  strengths, findings, and evidence gaps;
- `human_creative_approval=false` and `final_delivery_claimed=false`;
- `chapter_candidates[]` when present, with bounded windows, opening/ending
  descriptions, information gain, and evidence references;
- findings with observation, interpretation, consequence, bounded coordinates,
  manifest evidence refs, falsification or explicit `human_taste_only`, a
  `requires_reopen` boolean, and exactly one primary proposal plus at most one
  fallback. A lock conflict remains visible and sets `requires_reopen=true`.

`proposed_fix` is normally an existing route/capability with rerun gates. If no
existing route is honest, use `route=no_existing_route`,
`capability_id=null`, a non-empty `no_route_reason`, and the owner/integrator
verdict requirement; do not invent an implementation or fake rerun gate.

The packet's `audio_probe_artifact_fingerprint` is the hash of the soundtrack
probe JSON only. It is not an elementary-stream fingerprint. When no real
picture/audio stream fingerprint exists, the packet keeps it explicitly
`unbound` and reuse fails closed.

Empty `findings` is valid. A clean review should preserve strengths and state
limitations instead of maximizing finding count. Structural candidates remain
advisory until an owner verdict; taste findings never become a machine
PASS/FAIL and are capped at three.

## Stage placement

This is a route-driven surface, not a mandatory stop at every Stage:

| Stage | Editorial Reviewer use |
|---|---|
| 0–2 | Major story choice or requested A/B comparison. |
| 3 | Targeted Material Map audit; never full-pool reinspection by default. |
| 4–5 | Paper-edit and story-structure review before expensive render. |
| 6 | Candidate review only after build evidence exists. |
| 7–8 | Primary eye/ear/heart timeline review plus deterministic Verify. |
| 9 | Incremental review of the changed layer/window only. |
| 10 | Process and artifact-integrity review; never creative self-approval. |

Existing Verify tools remain owned by `skills/verify.md`. A finding routes to an
existing Stage return route/capability and always sets
`requires_owner_or_integrator_verdict=true`; the reviewer never executes that
route.

After the reviewer has finished writing its JSON, the parent/orchestrator runs
the public validator with `--receipt-out`. The receipt hashes the exact review
bytes that were validated and rechecks declared packet/subject hashes when
those files are available. A chat message claiming a hash is not evidence; the
receipt is the authoritative handoff for routing.
