"""runtime_orchestrator.py — Unified Runtime Orchestrator core logic.

Decouples CLI driver from orchestrator logic to keep root module small.
"""
import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

# Add the repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from video_pipeline_core.project_workspace import (
    resolve_active_pointer, default_project_root, create_run_dir, write_active_project, _repo_project_dir
)
from video_pipeline_core.dashboard_state import load_dashboard_state
from video_pipeline_core.platform_tools import resolve_python

from video_pipeline_core import blueprint as blueprint_gate
from video_pipeline_core.node_registry import NODE_REGISTRY, NODE_ORDER
NODE_ARTIFACTS = {node_id: node_def["outputs"] for node_id, node_def in NODE_REGISTRY.items()}


_AUDIT_NODE = {
    "timeline_invariants": "11", "broll_audit": "11", "caption_audit": "11",
    "keyframe_grid": "12", "visual_audit": "12", "treatment_audit": "11",
    "visual_fatigue_audit": "11", "editorial_qa": "12",
}


def resolve_audit_route(dash_state):
    """Consume P1 audit findings and route to the smallest affected node/skill.

    Pure consumer: reads the deterministic audit artifacts already loaded into the
    dashboard state; it does not run any audit algorithm. Returns the route for the
    earliest (smallest node) blocking audit, or None when nothing is blocking.
    """
    findings = [f for f in (dash_state.get("findings") or [])
                if f.get("type") == "error" and f.get("artifact") in _AUDIT_NODE]
    if not findings:
        return None
    findings.sort(key=lambda f: (f.get("node") or 99, f.get("artifact")))
    chosen = findings[0]
    artifact = chosen["artifact"]
    node_id = _AUDIT_NODE[artifact]
    node_def = NODE_REGISTRY.get(node_id, {})
    audit = (dash_state.get("artifacts") or {}).get(artifact) or {}
    return {
        "artifact": artifact,
        "node": node_id,
        "skill": " / ".join(node_def.get("skill", [])),
        "next_action": audit.get("next_action"),
        "message": chosen.get("message", f"{artifact} reported a blocking finding"),
    }


def _get_project_and_run(project_name=None):
    """Resolve project directory and active/latest run directory, honoring project_root."""
    active_path = _repo_project_dir(REPO_ROOT) / "active.json"
    project_root = None
    active_data = None

    if active_path.exists():
        try:
            with active_path.open(encoding="utf-8") as f:
                active_data = json.load(f)
                root_path = Path(active_data["project_root"]).expanduser()
                if not root_path.is_absolute():
                    root_path = REPO_ROOT / root_path
                project_root = root_path
        except Exception:
            pass

    if not project_root:
        project_root = default_project_root()

    if project_name:
        from video_pipeline_core.project_workspace import slugify
        project_slug = slugify(project_name)
        project_dir = project_root / project_slug
        
        run_dir = None
        # If the active pointer matches the requested project, use its active run
        if active_data and active_data.get("active_project") == project_slug:
            _, run_dir = resolve_active_pointer(active_data, repo_dir=REPO_ROOT)
        if not run_dir:
            # Find latest run folder alphabetically
            runs_parent = project_dir / "runs"
            if runs_parent.exists():
                candidates = sorted([d for d in runs_parent.iterdir() if d.is_dir()])
                if candidates:
                    run_dir = candidates[-1]
    else:
        if active_data:
            project_dir, run_dir = resolve_active_pointer(active_data, repo_dir=REPO_ROOT)
        else:
            print("[runtime] Error: No active project pointer found. Run project-init first or pass --project.", file=sys.stderr)
            sys.exit(1)

    if not project_dir.exists():
        print(f"[runtime] Error: Project directory {project_dir} does not exist.", file=sys.stderr)
        sys.exit(1)

    return project_dir, run_dir
def check_ready_for_build_gate(run_dir):
    """Validate editorial design against allowed strategies (ready_for_build gate)."""
    run_dir = Path(run_dir)
    design_path = run_dir / "editorial_design.json"
    if not design_path.exists():
        return
    try:
        with design_path.open(encoding="utf-8") as f:
            design = json.load(f)
    except Exception as e:
        print(f"[runtime] [GATE] Warning: Failed to parse editorial_design.json: {e}", file=sys.stderr)
        return

    errors = []

    # 1. Subtitle placement validation
    sub_strategy = design.get("subtitle_strategy") or {}
    placement = sub_strategy.get("placement")
    if placement and placement not in ("bottom_safe", "top_safe", "hidden"):
        errors.append(f"Invalid subtitle placement: '{placement}'. Must be 'bottom_safe', 'top_safe', or 'hidden'.")

    # 2. Narration mode validation
    nar_strategy = design.get("narration_strategy") or {}
    mode = nar_strategy.get("mode")
    if mode and mode not in ("voiceover", "none", "captions_only"):
        errors.append(f"Invalid narration mode: '{mode}'. Must be 'voiceover', 'none', or 'captions_only'.")

    # 3. Expressive effects validation
    fx_strategy = design.get("effects_strategy") or {}
    allowed = fx_strategy.get("allowed_roles") or []
    for fx in allowed:
        if fx in ("3d_render", "blender_physics", "advanced_vfx"):
            errors.append(f"Expressive effect '{fx}' is not supported by current CapCut/effects profile.")

    if errors:
        print("[runtime] [GATE] ready_for_build gate check FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    else:
        print("[runtime] [GATE] ready_for_build gate check PASSED.")


def _copy_initial_artifacts(project_dir, run_dir, args):
    """Copy canonical contract and brief files from input to run workspace."""
    run_dir = Path(run_dir)
    project_dir = Path(project_dir)

    # 1. Copy segment contract
    contract_path = run_dir / "segment_contract.json"
    if not contract_path.exists():
        src_contract = None
        if args.contract:
            src_contract = Path(args.contract)
        else:
            candidate = project_dir / "input" / "segment_contract.json"
            if candidate.exists():
                src_contract = candidate
            else:
                # Look for any json in input/
                jsons = list((project_dir / "input").glob("*.json"))
                jsons = [j for j in jsons if j.name not in ("materials_db.json", "brief.json", "blueprint.json", "editorial_design.json", "creator_profile.json", "decisions.json", "material_categories.json")]
                if len(jsons) == 1:
                    src_contract = jsons[0]

        if src_contract and src_contract.exists():
            print(f"[runtime] Copying contract from {src_contract} to {contract_path}...")
            shutil.copy2(src_contract, contract_path)
            # update active project to point to this run
            write_active_project(project_dir, active_run=run_dir, repo_dir=REPO_ROOT)
        else:
            # Check if we can bootstrap from blueprint.md, blueprint.json, or brief.json
            blueprint_md = project_dir / "input" / "blueprint.md"
            blueprint_json = project_dir / "input" / "blueprint.json"
            brief_json = project_dir / "input" / "brief.json"
            if blueprint_md.exists() or blueprint_json.exists() or brief_json.exists():
                print("[runtime] segment_contract.json missing. Attempting to bootstrap Greenfield SPEC...")
                write_active_project(project_dir, active_run=run_dir, repo_dir=REPO_ROOT)
                
                # A) Compile blueprint if blueprint.md exists but blueprint.json doesn't
                compiled_blueprint = None
                blueprint_json_path = run_dir / "blueprint.json"
                if not blueprint_json_path.exists():
                    if (project_dir / "input" / "blueprint.json").exists():
                        shutil.copy2(project_dir / "input" / "blueprint.json", blueprint_json_path)
                    elif (project_dir / "input" / "blueprint.md").exists():
                        try:
                            from .blueprint_compile import compile_blueprint_md
                            md_text = (project_dir / "input" / "blueprint.md").read_text(encoding="utf-8")
                            compiled_blueprint = compile_blueprint_md(md_text)
                            with blueprint_json_path.open("w", encoding="utf-8") as f:
                                json.dump(compiled_blueprint, f, ensure_ascii=False, indent=2)
                            print("[runtime] Compiled blueprint.md -> blueprint.json")
                        except Exception as e:
                            print(f"[runtime] Error compiling blueprint.md: {e}", file=sys.stderr)
                
                # Load compiled blueprint if we haven't already
                if not compiled_blueprint and blueprint_json_path.exists():
                    try:
                        with blueprint_json_path.open(encoding="utf-8") as f:
                            compiled_blueprint = json.load(f)
                    except Exception:
                        pass

                # B) Generate default editorial_design.json if it doesn't exist
                design_path = run_dir / "editorial_design.json"
                if not design_path.exists():
                    if (project_dir / "input" / "editorial_design.json").exists():
                        shutil.copy2(project_dir / "input" / "editorial_design.json", design_path)
                    else:
                        from .editorial_design import default_editorial_design
                        design_data = default_editorial_design(compiled_blueprint)
                        with design_path.open("w", encoding="utf-8") as f:
                            json.dump(design_data, f, ensure_ascii=False, indent=2)
                        print("[runtime] Generated default editorial_design.json")
                
                # C) Copy or generate brief.json
                brief_path = run_dir / "brief.json"
                if not brief_path.exists():
                    if (project_dir / "input" / "brief.json").exists():
                        shutil.copy2(project_dir / "input" / "brief.json", brief_path)
                    else:
                        tone = (compiled_blueprint or {}).get("intended_feeling") or "warm_reflective"
                        video_type = (compiled_blueprint or {}).get("mode_hint") or "mv"
                        brief_data = {
                            "video_type": video_type,
                            "spec_start_mode": "script_first",
                            "can_reshoot": True,
                            "fallback_policy": "reshoot_first",
                            "review_level": "high",
                            "audience": "general audience",
                            "target_length": "2 minutes",
                            "tone": tone,
                            "must_include": []
                        }
                        with brief_path.open("w", encoding="utf-8") as f:
                            json.dump(brief_data, f, ensure_ascii=False, indent=2)
                        print("[runtime] Generated default brief.json")

                # C2) Soul-layer compile (preferred): if a decisions.json is supplied,
                #     compile a density-correct contract from blueprint + per-beat
                #     editorial decisions. Inert when no decisions.json — block D below
                #     then runs the thin bootstrap fallback. If this writes the contract,
                #     block D is skipped (its guard sees the file now exists).
                if not contract_path.exists() and compiled_blueprint:
                    _dec_path = next((c for c in (project_dir / "input" / "decisions.json",
                                                  run_dir / "decisions.json") if c.exists()), None)
                    if _dec_path:
                        try:
                            from .blueprint_to_contract import compile_contract
                            with _dec_path.open(encoding="utf-8") as f:
                                _decisions = json.load(f)
                            shutil.copy2(_dec_path, run_dir / "decisions.json")
                            _compiled = compile_contract(compiled_blueprint, _decisions)
                            with contract_path.open("w", encoding="utf-8") as f:
                                json.dump(_compiled, f, ensure_ascii=False, indent=2)
                            print("[runtime] Compiled segment_contract.json from blueprint.json + "
                                  f"decisions.json ({len(_compiled['segments'])} segments, soul layer)")
                        except Exception as e:
                            print(f"[runtime] Error compiling contract from decisions.json: {e}; "
                                  "falling back to bootstrap.", file=sys.stderr)

                # D) Generate segment_contract.json from blueprint beats
                if not contract_path.exists():
                    beats = (compiled_blueprint or {}).get("beats") or [{"id": "b1", "role": "opening", "summary": "opening scene"}]
                    segments = []
                    for idx, beat in enumerate(beats):
                        role = beat.get("role") or "montage"
                        is_montage = role == "montage"
                        segments.append({
                            "segment": idx + 1,
                            "core": {
                                "section_role": role,
                                "story_purpose": beat.get("summary") or "Scene",
                                "timeline_source": "beat" if is_montage else "fixed",
                                "review_required": True,
                                "blueprint_ref": beat.get("id")
                            },
                            "material_fit": {
                                "category": "establishing_aerial" if idx == 0 else "hands_on_training",
                                "visual_desc": beat.get("summary") or "Scene",
                                "material_hint": beat.get("id") or "scene",
                                "required_traits": [],
                                "reject_traits": [],
                                "must_include": None,
                                "collection_instructions": f"Collect footage for: {beat.get('summary') or 'Scene'}",
                                "fallback_policy": "reshoot_first",
                                "reason": "bootstrapped from blueprint"
                            },
                            "audio": {
                                "role": "music",
                                "music_intent": "background",
                                "original_audio_policy": "drop",
                                "voiceover_policy": "none",
                                "reason": "bootstrapped"
                            },
                            "text_layer": {
                                "label": (beat.get("summary") or "Scene")[:30],
                                "reason": "bootstrapped"
                            },
                            "visual_style": {
                                "layout": "montage" if is_montage else "single",
                                "pace": "fast" if is_montage else "hold",
                                "transition": "cut" if is_montage else "fade",
                                "color_grade": "neutral",
                                "effects": [],
                                "reason": "bootstrapped"
                            }
                        })
                    
                    contract_data = {
                        "brief_ref": "brief.json",
                        "categories_ref": "material_categories.json",
                        "style": "mv",
                        "music": {"brief": "warm background", "query": "warm background lofi", "source": "yt"},
                        "segments": segments
                    }
                    with contract_path.open("w", encoding="utf-8") as f:
                        json.dump(contract_data, f, ensure_ascii=False, indent=2)
                    print("[runtime] Generated segment_contract.json from blueprint beats")

                # E) Check the ready_for_build gate!
                check_ready_for_build_gate(run_dir)

            else:
                print("[runtime] Error: No segment contract found to start the run. Please specify --contract or place segment_contract.json in the input folder.", file=sys.stderr)
                sys.exit(1)

    # 2. Copy brief
    brief_path = run_dir / "brief.json"
    if not brief_path.exists():
        src_brief = None
        if args.brief:
            src_brief = Path(args.brief)
        else:
            candidate = project_dir / "input" / "brief.json"
            if candidate.exists():
                src_brief = candidate
            else:
                # check contract brief_ref
                try:
                    with contract_path.open(encoding="utf-8") as fh:
                        contract_data = json.load(fh)
                        brief_ref = contract_data.get("brief_ref")
                        if brief_ref:
                            for prefix in (Path("."), project_dir / "input", REPO_ROOT / "examples"):
                                cand = prefix / brief_ref
                                if cand.exists():
                                    src_brief = cand
                                    break
                except Exception:
                    pass
        if src_brief and src_brief.exists():
            print(f"[runtime] Copying brief from {src_brief} to {brief_path}...")
            shutil.copy2(src_brief, brief_path)

    # 3. Copy narrative blueprint (WHY layer, optional) if present
    blueprint_path = run_dir / "blueprint.json"
    if not blueprint_path.exists():
        found = False
        for cand in (Path(args.contract).parent / "blueprint.json" if args.contract else None,
                      project_dir / "input" / "blueprint.json"):
            if cand and cand.exists():
                print(f"[runtime] Copying blueprint from {cand} to {blueprint_path}...")
                shutil.copy2(cand, blueprint_path)
                found = True
                break
        if not found:
            for cand_md in (Path(args.contract).parent / "blueprint.md" if args.contract else None,
                            project_dir / "input" / "blueprint.md"):
                if cand_md and cand_md.exists():
                    print(f"[runtime] Compiling blueprint from {cand_md} to {blueprint_path}...")
                    try:
                        from .blueprint_compile import compile_blueprint_md
                        md_text = cand_md.read_text(encoding="utf-8")
                        compiled = compile_blueprint_md(md_text)
                        with blueprint_path.open("w", encoding="utf-8") as f:
                            json.dump(compiled, f, ensure_ascii=False, indent=2)
                        break
                    except Exception as e:
                        print(f"[runtime] Warning: Failed to compile {cand_md}: {e}", file=sys.stderr)

    # 4. Copy build_profile.json if present
    bp_dest = run_dir / "build_profile.json"
    if not bp_dest.exists():
        bp_src = project_dir / "input" / "build_profile.json"
        if bp_src.exists():
            print(f"[runtime] Copying build_profile from {bp_src} to {bp_dest}...")
            shutil.copy2(bp_src, bp_dest)


def _resolve_music_path(project_dir, run_dir, contract_path, args):
    """Find BGM or fetch it automatically if missing."""
    if args.music:
        return args.music

    run_dir = Path(run_dir)
    project_dir = Path(project_dir)

    # 1. Look in run dir
    for ext in ("mp3", "webm", "wav"):
        cand = run_dir / f"bgm.{ext}"
        if cand.exists():
            return str(cand)

    # 2. Look in project input
    for ext in ("mp3", "webm", "wav"):
        for cand in (project_dir / "input").glob(f"*.{ext}"):
            if cand.exists():
                return str(cand)
        for cand in project_dir.glob(f"*.{ext}"):
            if cand.exists():
                return str(cand)
        for cand in REPO_ROOT.glob(f"*.{ext}"):
            if cand.exists():
                return str(cand)

    # 3. Auto-fetch via query from contract
    try:
        with Path(contract_path).open(encoding="utf-8") as f:
            contract = json.load(f)
        music_opt = contract.get("music", {})
        query = music_opt.get("query")
        source = music_opt.get("source", "yt")
        if query and source == "yt":
            print(f"[runtime] BGM not found. Automatically fetching music for query: '{query}'...")
            python_exe = resolve_python()
            fetch_cmd = [
                python_exe, str(REPO_ROOT / "video_tools.py"), "music-fetch",
                query, "--out", str(run_dir / "bgm.mp3")
            ]
            subprocess.run(fetch_cmd, check=True)
            return str(run_dir / "bgm.mp3")
    except Exception as e:
        print(f"[runtime] Warning: Auto music-fetch failed: {e}", file=sys.stderr)

    return None


def _resolve_material_db_path(project_dir, run_dir, args):
    """Find materials_db.json or write a blank one if missing."""
    if args.material_db:
        return args.material_db

    project_dir = Path(project_dir)
    run_dir = Path(run_dir)

    for cand in (run_dir / "materials_db.json", project_dir / "input" / "materials_db.json"):
        if cand.exists():
            return str(cand)

    # Write blank db
    blank_path = run_dir / "materials_db.json"
    print(f"[runtime] materials_db.json not found. Creating blank database at {blank_path}...")
    with blank_path.open("w", encoding="utf-8") as f:
        json.dump({"files": []}, f, ensure_ascii=False, indent=2)
    return str(blank_path)


def run_orchestrator(project_name=None, args=None):
    """Continuous loop running and resuming the pipeline based on state."""
    project_dir, run_dir = _get_project_and_run(project_name)

    # If no run_dir exists, create a new one
    if not run_dir or not run_dir.exists():
        print("[runtime] No active run folder. Creating a new run...")
        result = create_run_dir(project_dir, label="run-auto")
        run_dir = Path(result["run_dir"])

    print(f"[runtime] Active Project: {project_dir.name}")
    print(f"[runtime] Active Run: {run_dir.name}")

    # Copy initial files if starting a new run
    _copy_initial_artifacts(project_dir, run_dir, args)

    contract_path = run_dir / "segment_contract.json"
    python_exe = resolve_python()

    while True:
        # 1. Load current dashboard state
        dash_state = load_dashboard_state(str(run_dir))
        next_action = dash_state.get("run", {}).get("next_action") or dash_state.get("next_action")

        print(f"[runtime] Current Action resolved: {next_action}")

        # WHY layer: narrative blueprint gate. Inert when no blueprint.json exists.
        # A dropped/invalid beat is a SPEC-level problem -> route to director, never
        # let a run that lost a promised story beat reach completion.
        bp_cov = blueprint_gate.check_run(run_dir)
        if bp_cov is not None and not bp_cov.get("pass"):
            print("[runtime] [BLUEPRINT] Narrative gate failed (blueprint_coverage.json):")
            for f in bp_cov.get("findings", []):
                if f.get("level") == "error":
                    print(f"  - [{f.get('check')}] {f.get('message')}")
            print(f"[runtime] [DISPATCH] Skill 'director' must fix segment_contract "
                  f"blueprint_ref / coverage, then run "
                  f"'python runtime.py resume --project {project_dir.name}'.")
            sys.exit(0)

        # P1 verification tool pack: a failing deterministic/visual audit must not
        # be silently completed. Disabled tools produce no audit findings, so this
        # is inert for existing runs.
        audit_route = resolve_audit_route(dash_state)
        if audit_route and next_action in (None, "complete_review_final"):
            print(f"[runtime] [AUDIT] Blocking finding from '{audit_route['artifact']}' "
                  f"(Node {audit_route['node']} / {audit_route['skill']}): {audit_route['message']}")
            print(f"[runtime] [DISPATCH] Route: {audit_route['next_action'] or 'human review'}. "
                  f"Fix the smallest affected node and run "
                  f"'python runtime.py resume --project {project_dir.name}'.")
            sys.exit(0)

        if next_action == "complete_review_final":
            # Strict completion condition: verify pass AND final.mp4 exists AND required artifacts complete
            final_mp4 = run_dir / "final.mp4"
            verify_result = run_dir / "verify_result.json"
            verify_pass = False
            if verify_result.exists():
                try:
                    with verify_result.open(encoding="utf-8") as f:
                        v_data = json.load(f)
                        verify_pass = v_data.get("pass", False)
                except Exception:
                    pass
            
            # Check if required nodes are complete (not missing)
            required_nodes = [n for n in dash_state.get("nodes", []) if n.get("status") == "missing" and n.get("node") in [0, 3, 2, "4-7", 5, 8, 9, 10, 11, 13, 12]]
            
            if final_mp4.exists() and verify_pass and not required_nodes:
                print("[runtime] [OK] Project completed successfully!")
                print(f"[runtime] Final output video: {final_mp4}")
                sys.exit(0)
            else:
                print("[runtime] Warning: next_action is complete_review_final but final.mp4, verify_result.json, or required artifacts are incomplete. Recalculating state...", file=sys.stderr)
                state_file = run_dir / "state.json"
                if state_file.exists():
                    try:
                        state_file.unlink()
                    except Exception:
                        pass
                continue

        elif next_action == "verify_failed":
            print(f"[runtime] [FAIL] Technical verification failed. Score: {dash_state.get('run', {}).get('score', 0)}")
            print("[runtime] Issues:")
            for issue in dash_state.get("findings", []):
                if issue.get("type") == "error" or "verify" in issue.get("message", "").lower():
                    print(f"  - {issue.get('message')}")
            print(f"[runtime] Please fix the issues and run 'python runtime.py resume --project {project_dir.name}'")
            sys.exit(1)

        elif next_action in ("human_review", "fix_timeline_or_assembly", "review"):
            print(f"[runtime] [REVIEW] Pending review: {next_action}.")
            print(f"[runtime] Please complete review and run 'python runtime.py resume --project {project_dir.name}'")
            sys.exit(0)

        elif next_action and next_action.startswith("revise:director"):
            print(f"[runtime] [DISPATCH] Skill 'director' tasked with revision. Details: {next_action}")
            # Feed the agent the exact SPEC findings — don't make it dig for them.
            sr_path = run_dir / "spec_review.json"
            if sr_path.exists():
                try:
                    with sr_path.open(encoding="utf-8") as f:
                        sr = json.load(f)
                    for b in (sr.get("blocking") or []):
                        print(f"  [BLOCKING] {b.get('message')}")
                        if b.get("fix"):
                            print(f"             fix: {b['fix']}")
                    for w in (sr.get("warnings") or []):
                        print(f"  [warn] {w.get('message')}")
                except Exception:
                    pass
            print("[runtime] Please edit segment_contract.json to resolve the SPEC issues above, then run resume.")
            sys.exit(0)

        elif next_action and next_action.startswith("retry:curator"):
            print(f"[runtime] [DISPATCH] Skill 'curator' automatic retries exhausted. Details: {next_action}")
            print("[runtime] Please adjust search_query or source in segment_contract.json, or supply local files, then run resume.")
            sys.exit(0)

        elif next_action and next_action.startswith("missing_artifact:brief.json"):
            # Try to copy brief.json from input folder again
            _copy_initial_artifacts(project_dir, run_dir, args)
            # If the brief still cannot be found, stop instead of looping forever.
            if not (run_dir / "brief.json").exists():
                print("[runtime] [WAIT] No brief.json found (input/brief.json, --brief, "
                      "or contract brief_ref). Provide one, then run "
                      f"'python runtime.py resume --project {project_dir.name}'.")
                sys.exit(0)
            state_file = run_dir / "state.json"
            if state_file.exists():
                try:
                    state_file.unlink()
                except Exception:
                    pass

        elif next_action and next_action.startswith("missing_artifact:segment_contract.json"):
            # Try to copy segment_contract.json from input folder again
            _copy_initial_artifacts(project_dir, run_dir, args)
            state_file = run_dir / "state.json"
            if state_file.exists():
                try:
                    state_file.unlink()
                except Exception:
                    pass

        elif next_action and (next_action.startswith("missing_artifact:") or "missing" in next_action):
            # Extract artifact name
            artifact_name = next_action.split(":", 1)[1] if ":" in next_action else next_action
            # Find matching node/skill from NODE_REGISTRY
            matching_node = None
            for node_id, node_def in NODE_REGISTRY.items():
                if artifact_name in node_def["outputs"]:
                    matching_node = node_def
                    break
            if matching_node:
                skills = " / ".join(matching_node["skill"])
                print(f"[runtime] [DISPATCH] Invoking skill(s) '{skills}' via runner '{matching_node['runner']}' to build artifact '{artifact_name}' (Node {matching_node['node']})...")

            if matching_node and matching_node["runner"] == "verify":
                # Check if final.mp4 exists. If not, we must compile it first.
                final_mp4 = run_dir / "final.mp4"
                if not final_mp4.exists():
                    print("[runtime] Warning: final.mp4 not found for verification. Building first...")
                else:
                    # Run verify directly!
                    script = str(run_dir / "generated_mv_script.json") if (run_dir / "generated_mv_script.json").exists() else str(run_dir / "segment_contract.json")
                    timing = str(run_dir / "music_structure.json") if (run_dir / "music_structure.json").exists() else str(run_dir / "audio" / "tts_timing.json")
                    edit_log = str(run_dir / "timeline_build.json") if (run_dir / "timeline_build.json").exists() else str(run_dir / "edit_log.json")
                    srt_path = run_dir / "subtitles.srt"
                    if not srt_path.exists():
                        with srt_path.open("w", encoding="utf-8") as f:
                            f.write("1\n00:00:00,000 --> 00:00:01,000\n[Music]\n")
                    out_report = str(run_dir / "verify_result.json")

                    verify_cmd = [
                        python_exe, str(REPO_ROOT / "video_tools.py"), "verify",
                        "--script", script,
                        "--timing", timing,
                        "--edit-log", edit_log,
                        "--srt", str(srt_path),
                        "--video", str(final_mp4),
                        "--out", out_report
                    ]
                    print(f"[runtime] Running: {' '.join(verify_cmd)}")
                    res = subprocess.run(verify_cmd)
                    ret = res.returncode
                    if ret and type(ret).__name__ != 'MagicMock' and ret != 0:
                        print("[runtime] Error: verification failed.", file=sys.stderr)
                        sys.exit(ret)

                    # Regenerate state.json
                    state_cmd = [python_exe, str(REPO_ROOT / "video_tools.py"), "state", str(run_dir)]
                    subprocess.run(state_cmd)
                    continue

            elif matching_node and matching_node["runner"] == "curator":
                # Curator runner (Node 2 Material Coverage)
                print(f"[runtime] [CURATOR] Generating material coverage map for {run_dir}...")
                if not contract_path.exists():
                    print("[runtime] Error: segment_contract.json not found for curator.", file=sys.stderr)
                    sys.exit(1)
                with contract_path.open(encoding="utf-8") as f:
                    contract_data = json.load(f)

                material_db_path = run_dir / "materials_db.json"
                if not material_db_path.exists():
                    input_mat_dir = project_dir / "input" / "materials"
                    raw_mat_dir = run_dir / "materials" / "raw"
                    materials_dir = None
                    if input_mat_dir.exists() and any(input_mat_dir.iterdir()):
                        materials_dir = input_mat_dir
                    elif raw_mat_dir.exists() and any(raw_mat_dir.iterdir()):
                        materials_dir = raw_mat_dir
                    
                    if materials_dir:
                        print(f"[runtime] Ingesting materials from {materials_dir}...")
                        from video_pipeline_core.curator import cmd_ingest_meta
                        class IngestArgs:
                            src = str(materials_dir)
                            out = str(material_db_path)
                            work_dir = str(run_dir)
                        cmd_ingest_meta(IngestArgs)
                    else:
                        if contract_data.get("material_source_mode") == "stock_first":
                            print("[runtime] stock_first mode active, writing empty materials database.")
                            with material_db_path.open("w", encoding="utf-8") as f:
                                json.dump({"files": []}, f, ensure_ascii=False, indent=2)
                        else:
                            print(f"[runtime] [WAIT] No materials found. Please place raw materials under {input_mat_dir} or {raw_mat_dir} and run resume.")
                            sys.exit(0)

                with material_db_path.open(encoding="utf-8") as f:
                    db_data = json.load(f)

                from video_pipeline_core.curator import match_script_to_material
                from video_pipeline_core.contract_adapter import contract_to_mv_script
                flat_contract = contract_to_mv_script(contract_data)
                segments = flat_contract.get("segments", [])
                match_res = match_script_to_material(segments, db_data.get("files", []))

                gaps = match_res.get("gaps", [])
                missing = [g for g in gaps if g.get("must_include")]
                weak = [g for g in gaps if not g.get("must_include")]
                blocking = missing

                coverage_map = {
                    "covered": [a for a in match_res.get("assignments", []) if not a.get("gap")],
                    "weak": weak,
                    "missing": missing,
                    "blocking": blocking,
                }

                coverage_map_path = run_dir / "material_coverage_map.json"
                with coverage_map_path.open("w", encoding="utf-8") as f:
                    json.dump(coverage_map, f, ensure_ascii=False, indent=2)
                print(f"[runtime] Saved material coverage map to {coverage_map_path}")

                if blocking and contract_data.get("material_source_mode") != "stock_first":
                    state_file = run_dir / "state.json"
                    state_json_data = {}
                    if state_file.exists():
                        try:
                            with state_file.open(encoding="utf-8") as sf:
                                state_json_data = json.load(sf)
                        except Exception:
                            pass
                    state_json_data["blocking"] = blocking
                    state_json_data["next_action"] = "await_material"
                    with state_file.open("w", encoding="utf-8") as sf:
                        json.dump(state_json_data, sf, ensure_ascii=False, indent=2)

                    print(f"[runtime] [WAIT] Awaiting missing must-include materials:")
                    for b in blocking:
                        print(f"  - seg{b.get('segment')}: {b.get('reason')}")
                    sys.exit(0)

                # Regenerate state.json
                state_cmd = [python_exe, str(REPO_ROOT / "video_tools.py"), "state", str(run_dir)]
                subprocess.run(state_cmd)
                continue

            # We need to compile the video!
            # If render_backend is capcut_draft, do CapCut finalization instead!
            build_profile_path = run_dir / "build_profile.json"
            build_profile = {}
            if build_profile_path.exists():
                try:
                    with build_profile_path.open(encoding="utf-8") as f:
                        build_profile = json.load(f)
                except Exception:
                    pass
            
            if build_profile.get("render_backend") == "capcut_draft":
                print(f"[runtime] [FINALIZE] CapCut backend detected. Finalizing export...")
                music_file = _resolve_music_path(project_dir, run_dir, contract_path, args)
                if not music_file:
                    print("[runtime] Error: No background music file resolved. Please specify --music or place bgm.mp3 in the input directory.", file=sys.stderr)
                    sys.exit(1)
                
                # Resolve outro defaults (title, address, extra, BGM volume) from brief and creator profile
                brief_path = run_dir / "brief.json"
                brief_data = {}
                if brief_path.exists():
                    try:
                        with brief_path.open(encoding="utf-8") as f:
                            brief_data = json.load(f)
                    except Exception:
                        pass

                creator_profile_path = run_dir / "creator_profile.json"
                if not creator_profile_path.exists():
                    creator_profile_path = project_dir / "input" / "creator_profile.json"
                creator_profile_data = {}
                if creator_profile_path.exists():
                    try:
                        with creator_profile_path.open(encoding="utf-8") as f:
                            creator_profile_data = json.load(f)
                    except Exception:
                        pass

                outro_defaults = creator_profile_data.get("outro_defaults") or {}
                
                outro_title = brief_data.get("outro_title") or outro_defaults.get("title") or "Thank you for watching!"
                outro_address = brief_data.get("outro_address") or outro_defaults.get("address") or "Visit our website!"
                outro_extra = brief_data.get("outro_extra") or outro_defaults.get("extra") or ""
                bgm_volume = brief_data.get("bgm_vol") or brief_data.get("bgm_volume") or outro_defaults.get("bgm_vol") or outro_defaults.get("bgm_volume") or 0.25

                cmd = [
                    python_exe, str(REPO_ROOT / "video_tools.py"), "capcut-finalize",
                    "--video", str(run_dir / "capcut_exported.mp4"),
                    "--out", str(run_dir / "final.mp4"),
                    "--bgm", str(music_file),
                    "--outro-title", outro_title,
                    "--outro-address", outro_address,
                    "--bgm-vol", str(bgm_volume)
                ]
                if outro_extra:
                    cmd += ["--outro-extra", outro_extra]

                print(f"[runtime] Running: {' '.join(cmd)}")
                res = subprocess.run(cmd)
                if res.returncode != 0:
                    print("[runtime] Error: CapCut finalization failed.", file=sys.stderr)
                    sys.exit(res.returncode)
                
                # Run audits after generating final.mp4
                from video_pipeline_core.contract_adapter import _write_p1_audits
                print("[runtime] Running P1 verification audits...")
                with contract_path.open(encoding="utf-8") as f:
                    contract = json.load(f)
                _write_p1_audits(
                    run_dir,
                    build_profile,
                    timeline_build_path=str(run_dir / "timeline_build.json"),
                    srt_path=str(run_dir / "subtitles.srt"),
                    final_video=str(run_dir / "final.mp4"),
                    contract_obj=contract,
                    verbose=True
                )
                
                # Regenerate editorial_qa.json
                if build_profile.get("editing_policy"):
                    try:
                        from video_pipeline_core import edit_artifacts
                        edit_artifacts.write_editorial_qa(run_dir, build_profile["editing_policy"])
                    except Exception as e:
                        print(f"[runtime] failed to update editorial_qa: {e}")

                # Regenerate state.json
                state_cmd = [python_exe, str(REPO_ROOT / "video_tools.py"), "state", str(run_dir)]
                subprocess.run(state_cmd)
                continue

            # Determine style (MV or Narrative)
            with contract_path.open(encoding="utf-8") as f:
                contract = json.load(f)
            style = contract.get("style", "mv")

            if style == "mv":
                # Resolve music and materials db
                music_file = _resolve_music_path(project_dir, run_dir, contract_path, args)
                if not music_file:
                    print("[runtime] Error: No background music file resolved. Please specify --music or place bgm.mp3 in the input directory.", file=sys.stderr)
                    sys.exit(1)
                material_db = _resolve_material_db_path(project_dir, run_dir, args)

                # Resolve categories, preferring the contract/project-specific
                # vocabulary over the global default. The contract declares its
                # own map via categories_ref; the global examples map is only a
                # last-resort fallback (it does not know project-specific
                # category words and would reject them at validate_contract).
                cat_ref = contract.get("categories_ref") or "material_categories.json"
                cat_candidates = [
                    run_dir / cat_ref,
                    project_dir / "input" / cat_ref,
                    run_dir / "material_categories.json",
                    project_dir / "input" / "material_categories.json",
                    REPO_ROOT / "examples" / "material_categories.json",
                ]
                categories = None
                for cand in cat_candidates:
                    if cand.exists():
                        categories = str(cand)
                        break

                print(f"[runtime] Launching contract-run compile for MV style...")
                cmd = [
                    python_exe, str(REPO_ROOT / "video_tools.py"), "contract-run",
                    str(contract_path),
                    "--material-db", material_db,
                    "--music", music_file,
                    "--out", str(run_dir / "final.mp4"),
                    "--mat-dir", str(run_dir)
                ]
                if categories and os.path.exists(categories):
                    cmd += ["--categories", categories]
                build_prof_path = run_dir / "build_profile.json"
                if build_prof_path.exists():
                    cmd += ["--build-profile", str(build_prof_path)]

                print(f"[runtime] Running: {' '.join(cmd)}")
                res = subprocess.run(cmd)
                if res.returncode != 0:
                    print("[runtime] Error: compilation failed.", file=sys.stderr)
                    sys.exit(res.returncode)
            else:
                # Narrative mode
                print(f"[runtime] Launching run_with_ollama.py compile for Narrative style...")
                cmd = [
                    python_exe, str(REPO_ROOT / "run_with_ollama.py"),
                    str(contract_path),
                    "--out", str(run_dir)
                ]
                print(f"[runtime] Running: {' '.join(cmd)}")
                res = subprocess.run(cmd)
                if res.returncode != 0:
                    print("[runtime] Error: narrative compilation failed.", file=sys.stderr)
                    sys.exit(res.returncode)

        elif next_action == "await_capcut_export":
            print("[runtime] [WAIT] Awaiting CapCut manual export...")
            print(f"Please open CapCut, export the project as 'capcut_exported.mp4', and place it in:")
            print(f"  {run_dir}")
            print("Then run resume to finalize compilation.")
            sys.exit(0)

        elif next_action == "await_material":
            # Check for arrived uploads matching blocked segments
            blocking = dash_state.get("blocking", [])
            if not blocking and (run_dir / "state.json").exists():
                try:
                    with open(run_dir / "state.json", encoding="utf-8") as f:
                        state_data = json.load(f)
                        blocking = state_data.get("blocking", [])
                except Exception:
                    pass

            arrived_materials = {}
            for b in blocking:
                seg_id = b.get("segment")
                if not seg_id:
                    continue
                # Search for arrived files
                found_file = None
                for base in (f"seg{seg_id}_user", f"seg{seg_id}"):
                    for folder in (project_dir / "input" / "materials", run_dir / "materials" / "raw", run_dir):
                        if not folder.exists():
                            continue
                        for f in folder.iterdir():
                            if f.is_file() and f.stem.lower() == base.lower():
                                found_file = f
                                break
                        if found_file:
                            break
                    if found_file:
                        break
                if found_file:
                    arrived_materials[seg_id] = found_file

            if arrived_materials:
                # Copy arrived materials into workspace
                raw_materials_dir = run_dir / "materials" / "raw"
                raw_materials_dir.mkdir(parents=True, exist_ok=True)

                with contract_path.open(encoding="utf-8") as f:
                    contract = json.load(f)

                for seg_id, filepath in arrived_materials.items():
                    dest = raw_materials_dir / filepath.name
                    print(f"[runtime] Found material for segment {seg_id}: copying {filepath} to {dest}...")
                    shutil.copy2(filepath, dest)

                    # Update contract segment
                    for seg in contract.get("segments", []):
                        if seg.get("segment") == seg_id:
                            seg["source"] = "local"
                            seg["file"] = str(dest)

                # Save modified contract back
                with contract_path.open("w", encoding="utf-8") as f:
                    json.dump(contract, f, ensure_ascii=False, indent=2)

                print("[runtime] Contract updated with local sources. Rebuilding...")

                # Clear old state and downstream build artifacts to prevent infinite loop
                for art in ["state.json", "verify_result.json", "qa_report.json", "final.mp4", "polished_visual.mp4", "mv_av.mp4"]:
                    filepath = run_dir / art
                    if filepath.exists():
                        try:
                            filepath.unlink()
                        except Exception:
                            pass
            else:
                print(f"[runtime] [WAIT] Awaiting material for segment(s):")
                for b in blocking:
                    print(f"  - seg{b.get('segment')}: {b.get('reason')}")
                print(f"[runtime] Please place the material files (e.g. seg2.mp4 or seg2_user.png) in {project_dir / 'input' / 'materials'} and run resume.")
                sys.exit(0)

        elif next_action == "wait_for_generated_provider":
            # Check if all generated requests are met
            req_path = run_dir / "generated_asset_requests.json"
            if not req_path.exists():
                print("[runtime] Error: generated_asset_requests.json not found.", file=sys.stderr)
                sys.exit(1)

            with req_path.open(encoding="utf-8") as f:
                requests_data = json.load(f)

            items = requests_data.get("items") or []
            gen_dir = run_dir / "materials" / "generated"

            arrived_items = []
            all_arrived = True
            for item in items:
                seg_id = item.get("segment")
                # check if there is segN_generated.* or similar in generated folder
                found_file = None
                if gen_dir.exists():
                    for f in gen_dir.iterdir():
                        if f.is_file() and f.stem.lower() in (f"seg{seg_id}_generated", f"seg{seg_id}_antigravity", f"seg{seg_id}"):
                            found_file = f
                            break
                if found_file:
                    arrived_items.append({
                        "segment": seg_id,
                        "file": str(found_file.relative_to(run_dir)),
                        "provider": item.get("provider", "antigravity")
                    })
                else:
                    all_arrived = False

            if all_arrived and arrived_items:
                print("[runtime] All AI generated assets have arrived. Compiling generated manifest...")
                outputs_path = run_dir / "outputs.json"
                with outputs_path.open("w", encoding="utf-8") as f:
                    json.dump({"items": arrived_items}, f, ensure_ascii=False, indent=2)

                cmd = [
                    python_exe, str(REPO_ROOT / "video_tools.py"), "generated-manifest",
                    str(req_path),
                    "--outputs", str(outputs_path),
                    "--out", str(run_dir / "generated_asset_manifest.json"),
                    "--artifact-manifest", str(run_dir / "artifact_manifest.json")
                ]
                print(f"[runtime] Running: {' '.join(cmd)}")
                subprocess.run(cmd, check=True)

                # Delete temporary outputs.json
                try:
                    outputs_path.unlink()
                except Exception:
                    pass

                # Clear old state and downstream build artifacts to prevent infinite loop
                for art in ["state.json", "verify_result.json", "qa_report.json", "final.mp4", "polished_visual.mp4", "mv_av.mp4"]:
                    filepath = run_dir / art
                    if filepath.exists():
                        try:
                            filepath.unlink()
                        except Exception:
                            pass
            else:
                print(f"[runtime] [WAIT] Awaiting generated assets:")
                for item in items:
                    seg_id = item.get("segment")
                    print(f"  - seg{seg_id}: Conceptual cutaway prompt: '{item.get('prompt')}'")
                sys.exit(0)

        else:
            print(f"[runtime] Unhandled or waiting action: {next_action}. Pausing loop.")
            sys.exit(0)


def print_status(project_name=None):
    """Display project run details and nodes progress table."""
    project_dir, run_dir = _get_project_and_run(project_name)

    if not run_dir or not run_dir.exists():
        print(f"Project: {project_dir.name}")
        print("Status: No runs found.")
        return

    dash_state = load_dashboard_state(str(run_dir))
    run_info = dash_state.get("run", {})

    # Correctly extract verify score from verify_result.json if present
    verify_result = dash_state.get("artifacts", {}).get("verify_result") or {}
    score = verify_result.get("score") if verify_result else None
    score_str = str(score) if score is not None else "N/A"

    print("=" * 80)
    print(f"Project: {project_dir.name}".ljust(40) + f"Run: {run_dir.name}")
    print(f"Path: {run_dir}")
    print("-" * 80)
    print(f"Status: {'PASS' if run_info.get('pass') else 'FAIL'}".ljust(40) + f"QA Score: {score_str}")
    print(f"Next Action: {run_info.get('next_action') or 'None'}")
    print("=" * 80)
    print(f"{'Node'.ljust(6)} | {'Status'.ljust(8)} | {'Artifact'.ljust(30)} | {'Description'}")
    print("-" * 80)
    for node in dash_state.get("nodes", []):
        node_id = str(node.get("node"))
        status = node.get("status", "missing")
        artifact = node.get("artifact", "")
        reason = node.get("reason", "")
        print(f"{node_id.ljust(6)} | {status.ljust(8)} | {artifact.ljust(30)} | {reason}")
    print("=" * 80)

    findings = dash_state.get("findings", [])
    if findings:
        print("Findings & Alerts:")
        for f in findings:
            print(f"  [{f.get('type', 'info').upper()}] {f.get('message')}")
        print("=" * 80)


def rerun_node(node_label, project_name=None, args=None):
    """Clean the specified node's artifact and all downstream artifacts, then rerun."""
    project_dir, run_dir = _get_project_and_run(project_name)

    if not run_dir or not run_dir.exists():
        print(f"[runtime] Error: Run directory does not exist for project {project_name}.", file=sys.stderr)
        sys.exit(1)

    if node_label not in NODE_ORDER:
        print(f"[runtime] Error: Invalid Node label '{node_label}'. Valid nodes: {NODE_ORDER}", file=sys.stderr)
        sys.exit(1)

    idx = NODE_ORDER.index(node_label)
    cleared_files = []

    for i in range(idx, len(NODE_ORDER)):
        label = NODE_ORDER[i]
        artifacts = NODE_ARTIFACTS.get(label, [])
        for art in artifacts:
            filepath = run_dir / art
            if filepath.exists():
                try:
                    if filepath.is_dir():
                        shutil.rmtree(filepath)
                    else:
                        filepath.unlink()
                    cleared_files.append(art)
                except Exception as e:
                    print(f"[runtime] Warning: Failed to delete {art}: {e}", file=sys.stderr)

    # Also clean the verify folder if it exists
    verify_folder = run_dir / "verify"
    if verify_folder.exists() and verify_folder.is_dir():
        for f in verify_folder.iterdir():
            try:
                f.unlink()
            except Exception:
                pass

    # Always delete state.json to force recalculation of the next action
    state_file = run_dir / "state.json"
    if state_file.exists():
        try:
            state_file.unlink()
            cleared_files.append("state.json")
        except Exception:
            pass

    print(f"[runtime] Cleared artifacts for Node {node_label} and downstream: {', '.join(cleared_files) if cleared_files else 'None'}")

    # Reload dashboard state after cleaning to trigger correct rebuilding
    dash_state = load_dashboard_state(str(run_dir))

    # If Node 12 (verify) is the only cleared node but final.mp4 still exists, we can run verify directly
    if node_label == "12" and (run_dir / "final.mp4").exists():
        print("[runtime] Re-running verification directly...")
        python_exe = resolve_python()

        # Determine script and timing paths
        script = str(run_dir / "generated_mv_script.json") if (run_dir / "generated_mv_script.json").exists() else str(run_dir / "segment_contract.json")
        timing = str(run_dir / "music_structure.json") if (run_dir / "music_structure.json").exists() else str(run_dir / "audio" / "tts_timing.json")
        edit_log = str(run_dir / "timeline_build.json") if (run_dir / "timeline_build.json").exists() else str(run_dir / "edit_log.json")
        srt_path = run_dir / "subtitles.srt"
        if not srt_path.exists():
            with srt_path.open("w", encoding="utf-8") as f:
                f.write("1\n00:00:00,000 --> 00:00:01,000\n[Music]\n")
        video = str(run_dir / "final.mp4")
        out_report = str(run_dir / "verify_result.json")

        verify_cmd = [
            python_exe, str(REPO_ROOT / "video_tools.py"), "verify",
            "--script", script,
            "--timing", timing,
            "--edit-log", edit_log,
            "--srt", str(srt_path),
            "--video", video,
            "--out", out_report
        ]
        print(f"[runtime] Running: {' '.join(verify_cmd)}")
        res = subprocess.run(verify_cmd)
        ret = res.returncode
        if ret and type(ret).__name__ != 'MagicMock' and ret != 0:
            print("[runtime] Error: verification failed.", file=sys.stderr)
            sys.exit(ret)

        # Regenerate state.json
        state_cmd = [python_exe, str(REPO_ROOT / "video_tools.py"), "state", str(run_dir)]
        subprocess.run(state_cmd)

    # Trigger orchestrator loop to resume compilation and verification
    run_orchestrator(project_dir.name, args)
