# Pipeline Branch Interface Dictionary

This folder contains the machine-readable route interface contracts between the
Hermes main video pipeline and its side branches.

## What These Interfaces Are

These are **not** HTTP endpoints. They are pipeline-facing data and command
interfaces:

- Main route request -> side branch work.
- Side branch handoff -> main BUILD / review route.
- Verify delivery repair -> owning side branch.
- Workbench/Brownfield draft review -> route-back patch handoff.

The current MVP dictionary covers 16 interfaces across these major side
branches:

- `material-map`
- `soundtrack-arranger`
- `subtitle-voiceover`
- `effect-factory`
- `workbench-brownfield`

## File Index

- `pipeline-api-dictionary.json`:
  Master registry for branch interfaces, triggers, required inputs, expected
  outputs, success/failure next actions, and protected files each interface must
  not write.
- `pipeline-product-artifact-dictionary.json`:
  Product-facing artifact registry that maps fuzzy user intent to functional
  editing, audio, effect, subtitle/voiceover, build, and verify parameters.
- `pipeline-product-artifacts.md`:
  Human-readable explanation of the product artifact layer.

## Audit Command

Run:

```powershell
python video_tools.py interface-audit
```

JSON output:

```powershell
python video_tools.py interface-audit --out .tmp/interface_audit.json
```

Product artifact dictionary audit:

```powershell
python tools/product_artifact_dictionary_audit.py --json
```

The audit checks:

1. Every interface uses valid branch IDs from `docs/branch-contract-registry.json`.
2. Each major side branch has request, handoff, and repair coverage.
3. Branch request/handoff/repair interfaces forbid direct `final.mp4` writes.
4. Returning branch handoffs forbid protected canonical writes where applicable.
5. Each interface has a trigger, request tool, non-empty inputs, required fields,
   outputs, and explicit success/failure next actions.
6. Success/failure next actions are declared route action IDs, not artifact filenames.
7. Branch handoff routes declare at least one output that can be registered in
   `artifact_manifest.json.handoffs`.
8. Referenced tools exist under `tools/` or as `video_tools.py` commands.

## Handoff Manifest Contract

Side branches should register accepted or blocked handoff artifacts in the run
folder's `artifact_manifest.json` using:

```json
{
  "handoffs": {
    "audio_director_handoff": {
      "path": "audio_director_handoff.json",
      "artifact_class": "handoff",
      "owner_branch": "soundtrack-arranger",
      "status": "accepted",
      "updated_by": "tools/soundtrack_flow_acceptance.py",
      "interface_id": "soundtrack_arranger.to.audio_director.handoff",
      "next_action": "audio_director_mix_or_build"
    }
  }
}
```

Keep the existing flat manifest keys for compatibility. The shared helper is
`video_pipeline_core.artifact_manifest.register_handoff`.

---

## Audit vs Discovery

*   **`video_tools.py interface-audit` (Hard Gate)**:
    Verifies that the canonical `pipeline-api-dictionary.json` is structurally valid, self-consistent, and secure (e.g., enforces `final.mp4` forbidden writes and valid branch names). Any failure here is treated as a hard validation failure.
*   **`pipeline_interface_discovery.py` (Soft Discovery)**:
    Heuristically scans skills and python files to discover new candidate interfaces, missing mappings, or stale declarations. It outputs suggestions/draft report to help agents/humans maintain the dictionary. It does not enforce hard gates or modify the dictionary directly.

Run discovery:
```powershell
python tools/pipeline_interface_discovery.py --json
```
