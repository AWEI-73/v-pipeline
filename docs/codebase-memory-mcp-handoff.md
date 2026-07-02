# Codebase Memory MCP Handoff

Date: 2026-07-03
Status: optional local code-navigation memory for review, handoff, and new agent sessions

This document explains how to use `codebase-memory-mcp` with this repository.
It is an agent helper, not a pipeline runtime component.

## Purpose

Use `codebase-memory-mcp` when a new agent or reviewer needs low-token answers
to code-structure questions:

- Where is a tool, route, handoff, or gate implemented?
- Which functions or tests mention an artifact such as `audio_build_handoff.json`?
- What code changed since the indexed state?
- Which modules own Soundtrack, Effect Factory, Material Map, Workbench, or
  delivery-gate behavior?

Do not use it as the source of truth for route decisions, artifact ownership, or
delivery gates. Those remain in:

- `RUNBOOK.md`
- `docs/pipeline-decision-tree.md`
- `docs/interface-contracts/README.md`
- `docs/branch-contract-registry.json`
- `docs/video-pipeline-operating-map.md`
- tests and delivery-gate code

## Relationship To Graphify

`codebase-memory-mcp` and Graphify serve different jobs.

| Tool | Best for | Not best for |
|---|---|---|
| `codebase-memory-mcp` | local code graph, functions, classes, call relationships, code search, change impact, handoff lookup | full semantic reading of project documents, product decisions, route rationale |
| Graphify | semantic maps across docs, decisions, images, videos, and architecture explanations | cheap per-commit code navigation |

Recommended operating rule:

- Use `codebase-memory-mcp` for normal new-session code discovery and review.
- Use Graphify only for larger semantic refreshes, route/design understanding,
  or documentation-heavy analysis.

## Local Pilot Result

The first local pilot used the release binary without installing hooks or
changing agent settings.

Binary path used:

```text
C:\Users\user\Desktop\video_pipeline\.tmp\cbm\codebase-memory-mcp.exe
```

Indexed project:

```text
C:\Users\user\Desktop\video_pipeline
```

Project name returned by the MCP server:

```text
C-Users-user-Desktop-video_pipeline
```

Fast index result:

```json
{
  "status": "indexed",
  "nodes": 9219,
  "edges": 28171
}
```

The index excluded large or noisy folders such as `.tmp`, `runs`, `docs`,
`reference repo`, and `archive/experiments`. That makes it useful for code
navigation, but it means it does not replace the current documentation map.

## Safe Usage Policy

Do not run the installer by default.

The upstream installer may modify coding-agent MCP settings, PATH, and hooks.
For this repository, prefer a local binary under `.tmp/cbm/` unless the user
explicitly asks to install it for all agents.

Safe pilot mode:

1. Download or place the binary under `.tmp/cbm/`.
2. Start it as an MCP stdio process.
3. Call `index_repository` for this repo.
4. Query it for code structure.
5. Leave pipeline source files untouched.

## Minimal MCP Call Pattern

The CLI wrapper may be sensitive to Windows argument quoting. MCP stdio is the
most reliable way to use it from an agent.

```python
import json
import subprocess

bin_path = r"C:\Users\user\Desktop\video_pipeline\.tmp\cbm\codebase-memory-mcp.exe"
repo_path = r"C:\Users\user\Desktop\video_pipeline"

proc = subprocess.Popen(
    [bin_path],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    errors="replace",
)

def send(obj):
    proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
    proc.stdin.flush()

send({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "video-pipeline-agent", "version": "0"},
    },
})
print(proc.stdout.readline())

send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

send({
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "index_repository",
        "arguments": {"repo_path": repo_path, "mode": "fast"},
    },
})
print(proc.stdout.readline())
```

## Useful Queries

Always pass the indexed project name:

```text
C-Users-user-Desktop-video_pipeline
```

Examples:

```json
{
  "name": "search_graph",
  "arguments": {
    "project": "C-Users-user-Desktop-video_pipeline",
    "query": "soundtrack arranger audio handoff",
    "limit": 8
  }
}
```

```json
{
  "name": "search_graph",
  "arguments": {
    "project": "C-Users-user-Desktop-video_pipeline",
    "query": "effect factory remotion handoff",
    "limit": 8
  }
}
```

```json
{
  "name": "search_code",
  "arguments": {
    "project": "C-Users-user-Desktop-video_pipeline",
    "pattern": "audio_build_handoff",
    "mode": "literal"
  }
}
```

```json
{
  "name": "detect_changes",
  "arguments": {
    "project": "C-Users-user-Desktop-video_pipeline"
  }
}
```

## Handoff Prompt Snippet

Use this when asking another agent to review code with this helper:

```text
You are reviewing C:\Users\user\Desktop\video_pipeline.

First read RUNBOOK.md and docs/START_HERE_VIDEO_PIPELINE.md.
If codebase-memory-mcp is available, use it only for code discovery:
- index project C:\Users\user\Desktop\video_pipeline if not already indexed
- project name is usually C-Users-user-Desktop-video_pipeline
- use search_graph/search_code/get_architecture/detect_changes to locate code

Do not treat codebase-memory-mcp as route truth.
Route truth remains RUNBOOK.md, docs/pipeline-decision-tree.md,
docs/interface-contracts/README.md, docs/branch-contract-registry.json,
and tests/delivery gates.
```

## Known Limits

- It is strongest on code, not route/design prose.
- Fast index intentionally ignores large or noisy folders.
- Search may return tests before implementation; this is useful for review, but
  the agent still needs to open implementation files before editing.
- It does not verify pipeline correctness. Use existing tests, interface audits,
  delivery gates, and focused E2E runs for correctness.
