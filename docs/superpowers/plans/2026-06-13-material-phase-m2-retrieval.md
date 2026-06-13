# Material Phase M2 Retrieval Plan

## Goal

Select relevant scene windows from material maps, preserve useful source speech,
and block edits that reuse the same visual information without justification.

## Tasks

1. Rank scenes by textual relevance, requested function, pace, and optional
   external ranker score.
2. Plan matched segment windows from ranked scenes instead of file order.
3. Plan `source_speech` sound bites from mapped speech runs.
4. Add a new-visual-information audit and make its failures block delivery.
5. Verify synthetic behavior, the previous graduation-film run, and full tests.

## Acceptance

- Off-topic scenes with no positive evidence are excluded.
- `source_speech` selects a speech run with transcript evidence and keeps audio.
- Repeated scene identity or excessive repeated visual hold fails delivery.
