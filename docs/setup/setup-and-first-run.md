# Setup and First Run

Windows is the primary local path for this repository.

## Prerequisites

Install:

- Miniconda for Windows.
- ffmpeg and ffprobe on `PATH`.
- Node.js on `PATH`.

Check the installed tools:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" --version
ffmpeg -version
node --version
```

Observed on this machine:

```text
Python 3.10.16
ffmpeg version 4.3.1 Copyright (c) 2000-2020 the FFmpeg developers
v22.16.0
```

## Python Dependencies

Install pinned Python dependencies into the miniconda environment:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" -m pip install -r requirements.txt
```

Observed on this machine: all pinned top-level packages were already satisfied,
including `edge-tts==7.2.7`, `faster-whisper==1.2.1`, `librosa==0.11.0`,
`numpy==2.2.6`, `opencv-python==4.12.0.88`, `Pillow==10.4.0`,
`playwright==1.60.0`, `python-dotenv==1.1.1`, `scenedetect==0.7`, and
`yt-dlp==2026.3.17`.

Node-side dependencies are documented by the dashboard/workbench scripts and
are not pinned in `requirements.txt`.

## Environment

Create `.env` from `.env.example` and fill local values. Do not commit `.env`.

`PEXELS_API_KEY` is the required stock-search key for strict preflight on this
machine. A clean clone will fail `tools/preflight.py --strict` until this key is
present. Use a real Pexels API key for strict local verification:

```powershell
Copy-Item .env.example .env
notepad .env
```

At minimum, set:

```text
PEXELS_API_KEY=<your pexels api key>
```

Other keys in `.env.example` are optional capabilities or local path overrides.

## Verification

Run:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" tools/preflight.py --strict
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py e2e-smoke --case stock_story
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py e2e-smoke --case single_long_highlight
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py registry-audit
& "$env:USERPROFILE\miniconda3\python.exe" -m unittest discover -s tests
```

Observed `preflight --strict` tail on this machine:

```text
status: ok
python: ok (3.10.16, required >=3.10)
ffmpeg: ok - ffmpeg version 4.3.1 Copyright (c) 2000-2020 the FFmpeg developers
node: ok - v22.16.0
yt-dlp: ok - 2026.03.17
python modules: ok
required env keys: present
```

Observed e2e smoke results:

```text
stock_story: ok=true, final_next_action=complete_review_final, dry_build_ok=true
single_long_highlight: ok=true, final_next_action=material-quick-inventory
```

Observed registry audit:

```text
Registry Audit: OK (7 branches, 14 stages)
```

Current construction note: during Stream S2, the full suite executed but failed
because `tools/preflight.py` is intentionally new while the existing
skill/tool ownership audit only accepts tools registered in frozen `skills/**`.
The S2 report in
`docs/construction-guides/2026-07-03-endgame-three-stream-spec.md` records the
exact blocker.

Run a strict asset path audit against a fresh smoke output:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py e2e-smoke --case stock_story --out-dir .tmp\setup_stock_story
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py asset-path-audit --strict .tmp\setup_stock_story
```

Expected strict audit result:

```text
Asset Path Audit (STRICT): 0 absolute path finding(s); 0 strict finding(s)
```

For the browser first-run check, start the dashboard server against a disposable
artifact root:

```powershell
New-Item -ItemType Directory -Force .tmp\dashboard_empty
& "$env:USERPROFILE\miniconda3\python.exe" tools\dashboard_server.py --artifact-root .tmp\dashboard_empty --port 8765
```

Open:

```text
http://127.0.0.1:8765/
http://127.0.0.1:8765/workbench
```

Both pages should load without browser console errors. A fresh disposable
artifact root may still show the built-in Workbench sample project rather than
a blank empty state; record that as first-run UX, not as a setup failure.

## First Run

For an agent-driven video request, point the coding agent at:

```text
docs/START_HERE_VIDEO_PIPELINE.md
```

Then ask for a video. The agent should enter through
`skills/video-pipeline.md`, inspect or create the current run state, and follow
`runtime.py` / `state.json.next_action`.
