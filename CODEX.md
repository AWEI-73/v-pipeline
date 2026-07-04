# Codex Project Notes

## Altitude Protocol - Planning / Delegation / Review

Known failure mode: correct steps on the wrong staircase - zooming into detail
before the structure is settled. These four gates force a zoom-out at the
moments it matters. Each gate costs a few lines of writing, not a process.

### Gate 1 - Before The First Edit: Build The Map Once, <=10 Lines

Write out before the first edit or implementation action. Reading files,
running status checks, and inspecting errors are allowed; reconnaissance is not
implementation.

- Current state -> desired state, in user-visible terms
- The need behind the request, in one sentence
- Non-goals: what you will not touch
- Done-evidence: observable proof that closes the loop

Skip the map only when the request itself names the exact change, meaning which
file and which behavior, and it needs a single edit with no behavior choice to
make. If unsure whether it qualifies, it does not.

Unless the skip rule applies, do not start implementation until this exists. If
the need behind the request cannot be stated, that is the one question worth
asking the user.

Good: "fix flaky test" -> need = trustworthy CI signal; the right fix might be
deleting the test.
Bad: "fix flaky test" -> immediately editing retry logic.

### Gate 2 - After Any Surprise: Structure Before Symptom

Whenever an attempt fails, a test breaks, or output differs from what was
expected, classify the signal before the next action:

- LOCAL: this line or isolated behavior is wrong
- STRUCTURAL: the design makes this class of error likely

Mandatory STRUCTURAL triggers. Any one means stop patching, re-read the map,
name the structural cause in one sentence, and propose the structural fix first:

- The same class of error appears a second time.
- A fix fights the existing design: working around an interface, duplicating
  state, or special-casing.
- You are about to debug a component whose role in the whole you cannot state in
  one sentence.

Good: two segments crash on a missing stream -> ask what contract should
guarantee streams exist.
Bad: adding a second try/except for the same reason.

### Gate 3 - Granularity And Delegation: Plan In Outcomes

Plan items must be observable outcomes, not implementation steps.

Good: "contract rejects unparseable duration targets."
Bad: "add parse function, add test, wire flag."

Test: if a plan item can only be verified by reading the diff, it is too fine.
Merge it upward.

When delegating, the packet has exactly three things:

- goal + why
- acceptance evidence
- report format: conclusions + file:line; long artifacts go to files

### Gate 4 - Anti-Ceremony And Declaring Done

Before adding any process artifact, checklist, pipeline stage, extra
verification round, or new doc, ask: does it change the deliverable, or catch a
failure that has actually happened here? If neither, do not add it.

To declare done, re-read the Gate 1 map and cite actual proof for each
done-evidence item: test output, read-back, artifact path, or user-visible
result.

"All plan steps completed" is not done. The map is the contract, not the plan.

If evidence is missing and cannot be produced, say so plainly. Do not narrow the
claim.

### Maintenance

- Change this file only after an actual failure in use: identify which gate was
  bypassed, then add that failure as a new Good/Bad example to that gate. Do not
  add rules from debate or anticipation.
- Every trigger in this file must be an observable event, such as an error
  occurred, a test broke, or the request names a file. Never use a judgment word
  such as non-trivial, materially, significant, or appropriate. Reject any edit
  that introduces one.
- One in, one out: to add a rule, name an existing rule to merge or delete.
  Examples are load-bearing; never drop one during an edit without stating so.

## Text Encoding

This repository contains Chinese Markdown and skill files. When checking whether
a text artifact is corrupted, do not rely on PowerShell `Get-Content` output in
the current console codepage.

Read Markdown / skill files with explicit UTF-8 first:

```powershell
@'
from pathlib import Path
p = Path("skills/material-map.md")
text = p.read_text(encoding="utf-8")
print(text[:800])
print("contains replacement char:", "\ufffd" in text)
'@ | python -
```

Only report an encoding/corruption issue after explicit UTF-8 decoding and a
replacement-character check.
