# Material Phase M0 Enforcement Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give existing capability, GAP, and VERIFY signals binding decision power before adding new editing machinery.

**Architecture:** Add a deterministic generated capability manifest, consume it in the pre-BUILD SPEC review, and centralize delivery blocking over existing audit artifacts. Keep creative preferences soft while making semantic honesty and failed audits hard gates.

**Tech Stack:** Python standard library, existing `video_tools.py` CLI, `unittest`, existing artifact contracts.

---

## Chunk 1: Capability And SPEC Authority

### Task 1: Generated Capability Manifest

**Files:**
- Create: `video_pipeline_core/capability_manifest.py`
- Create: `tests/test_capability_manifest.py`
- Modify: `video_tools.py`

- [ ] Write failing tests for deterministic manifest contents and JSON writer.
- [ ] Run tests and verify failure because the module does not exist.
- [ ] Implement manifest generation from existing constants.
- [ ] Add `video_tools.py capability-manifest --out ...`.
- [ ] Run focused tests and CLI smoke.

### Task 2: B5 Out-Of-Capability Gate And Tier Metadata

**Files:**
- Modify: `video_pipeline_core/spec_review.py`
- Modify: `tests/test_spec_review.py`
- Modify: `skills/spec-contract.md`

- [ ] Write failing tests for unsupported requirements blocking BUILD.
- [ ] Write failing tests asserting rule tier metadata and target length as tier 3.
- [ ] Run tests and verify expected failures.
- [ ] Implement capability requirement extraction and tier metadata.
- [ ] Run focused tests.

## Chunk 2: Delivery Authority And Census

### Task 3: Hard Delivery Gate

**Files:**
- Create: `video_pipeline_core/delivery_gate.py`
- Create: `tests/test_delivery_gate.py`
- Modify: `video_pipeline_core/dashboard_state.py`
- Modify: `tests/test_dashboard_state.py`

- [ ] Write failing tests proving failed b-roll/editorial/visual audits block completion.
- [ ] Write failing test proving unresolved GAP blocks completion.
- [ ] Run tests and verify expected failures.
- [ ] Implement deterministic delivery gate over existing artifacts.
- [ ] Wire dashboard completion routing through the gate.
- [ ] Run focused tests.

### Task 4: SPEC Field Census

**Files:**
- Create: `docs/decisions/2026-06-13-spec-field-census.md`

- [ ] Record keep/merge/downgrade/remove decisions.
- [ ] Identify each field's consumer, verifier, and violation action.

### Task 5: Verification

- [ ] Run all M0 focused tests.
- [ ] Run full `python -m unittest discover -s tests -v`.
- [ ] Update M0 roadmap status only after verification.
