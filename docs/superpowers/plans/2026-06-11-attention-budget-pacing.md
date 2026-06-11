# Attention Budget Pacing Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:test-driven-development to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Audit shot duration according to the channel currently carrying the story.

**Architecture:** Add a pure segment-level attention-budget resolver. `visual_fatigue` consumes the resolver to distinguish narration-led holds, untreated stills, photo stacks, and music-led edits without changing renderer allocation yet.

**Tech Stack:** Python standard library, unittest

---

## Chunk 1: Attention Budget Resolver

- [ ] Write failing tests for narration-led holds, untreated stills, photo stacks, and high-energy music.
- [ ] Implement `video_pipeline_core/attention_budget.py`.
- [ ] Run focused tests.

## Chunk 2: Visual Fatigue Integration

- [ ] Write failing audit tests proving narration-led holds pass and untreated music-led stills over two seconds fail.
- [ ] Add `attention_budget_fit` findings to `visual_fatigue`.
- [ ] Run focused tests and full suite.

