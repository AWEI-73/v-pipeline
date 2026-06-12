import os
import json
import datetime
import re

def scan_materials_via_regex(workdir):
    materials = []
    if not os.path.isdir(workdir):
        return materials

    def add_material(filename, rel_path, category, segment_id):
        full_path = os.path.join(workdir, rel_path)
        size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
        materials.append({
            "name": filename,
            "path": rel_path,
            "category": category,
            "segment": segment_id,
            "size_bytes": size
        })

    # Scan root workdir
    for f in os.listdir(workdir):
        # 1-indexed stock files: mvstock_1.mp4
        m1 = re.match(r'^mvstock_(\d+)\.(mp4|webm|mov|avi|png|jpg|jpeg|gif)$', f, re.IGNORECASE)
        if m1:
            add_material(f, f, "raw_stock", int(m1.group(1)))
            continue
        # 0-indexed rendered segment clips: mvseg_000.mp4
        m2 = re.match(r'^mvseg_(\d+)\.(mp4|webm|mov)$', f, re.IGNORECASE)
        if m2:
            add_material(f, f, "rendered_segment", int(m2.group(1)) + 1)
            continue
        # 0-indexed narration txt files: nar_0.txt
        m3 = re.match(r'^nar_(\d+)\.txt$', f, re.IGNORECASE)
        if m3:
            add_material(f, f, "narration_text", int(m3.group(1)) + 1)
            continue
        # 0-indexed label txt files: lbl_0.txt
        m4 = re.match(r'^lbl_(\d+)\.txt$', f, re.IGNORECASE)
        if m4:
            add_material(f, f, "label_text", int(m4.group(1)) + 1)
            continue
        # 1-indexed general segment visual materials in root: seg1_user.png
        m5 = re.match(r'^seg(\d+)_[a-zA-Z0-9_-]+\.(mp4|webm|png|jpg|jpeg|gif)$', f, re.IGNORECASE)
        if m5:
            add_material(f, f, "user_upload", int(m5.group(1)))
            continue

    material_dirs = [
        ("student_uploads", "user_upload"),
        (os.path.join("materials", "selected"), "selected_material"),
        (os.path.join("materials", "generated"), "generated_material"),
        (os.path.join("materials", "stock"), "stock_material"),
    ]
    for rel_dir, category in material_dirs:
        uploads_dir = os.path.join(workdir, rel_dir)
        if not os.path.isdir(uploads_dir):
            continue
        for f in os.listdir(uploads_dir):
            m = re.match(r'^seg(\d+)_[a-zA-Z0-9_-]+\.(mp4|webm|png|jpg|jpeg|gif)$', f, re.IGNORECASE)
            if m:
                add_material(f, os.path.join(rel_dir, f), category, int(m.group(1)))
            else:
                num_match = re.search(r'seg(\d+)', f, re.IGNORECASE)
                if num_match:
                    add_material(f, os.path.join(rel_dir, f), category, int(num_match.group(1)))
                    
    return sorted(materials, key=lambda x: (x["segment"], x["category"], x["name"]))

def load_dashboard_state(workdir):
    # Safe JSON loader
    def safe_load_json(filename):
        if not filename:
            return None
        p = os.path.join(workdir, filename) if not os.path.isabs(filename) else filename
        if not os.path.exists(p):
            # Try joining with workdir if it is absolute but we need it relative
            p2 = os.path.join(workdir, os.path.basename(filename))
            if os.path.exists(p2):
                p = p2
            else:
                return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    manifest = safe_load_json("artifact_manifest.json")
    
    # If manifest doesn't exist, we build a fallback manifest from folder scanning
    if not manifest:
        manifest = {}
        if os.path.isdir(workdir):
            for f in os.listdir(workdir):
                if f == "brief.json":
                    manifest["brief"] = f
                elif f == "segment_contract.json":
                    manifest["canonical_contract"] = f
                elif f == "material_coverage_map.json":
                    manifest["material_coverage_map"] = f
                elif f == "music_structure.json":
                    manifest["music_structure"] = f
                elif f == "build_profile.json":
                    manifest["build_profile"] = f
                elif f == "generated_asset_requests.json":
                    manifest["generated_asset_requests"] = f
                elif f == "assembly_plan.json":
                    manifest["assembly_plan"] = f
                elif f == "timeline_build.json":
                    manifest["timeline_build"] = f
                elif f == "editor_review.json":
                    manifest["editor_review"] = f
                elif f == "visual_review_request.json":
                    manifest["visual_review_request"] = f
                elif f == "visual_review_verdict.json":
                    manifest["visual_review_verdict"] = f
                elif f == "state.json":
                    manifest["state"] = f
                elif f == "qa_report.json" or f == "verify_result.json":
                    manifest["verify_result"] = f
                elif f == "final.mp4":
                    manifest["final"] = f
                elif f == "motion_graphics_render_plan.json":
                    manifest["motion_graphics_render_plan"] = f
                elif f == "motion_graphics_manifest.json":
                    manifest["motion_graphics_manifest"] = f
                elif f == "light_effects_baseline_review.json":
                    manifest["light_effects_baseline_review"] = f
                elif f == "editorial_qa.json":
                    manifest["editorial_qa"] = f
                elif f == "presentation_feel_audit.json":
                    manifest["presentation_feel_audit"] = f

    # Load artifacts safely
    brief_data = safe_load_json(manifest.get("brief")) or safe_load_json("brief.json")
    contract_data = safe_load_json(manifest.get("canonical_contract")) or safe_load_json("segment_contract.json")
    material_coverage = safe_load_json(manifest.get("material_coverage_map")) or safe_load_json("material_coverage_map.json")
    music_struct_data = safe_load_json(manifest.get("music_structure")) or safe_load_json("music_structure.json")
    profile_data = safe_load_json(manifest.get("build_profile")) or safe_load_json("build_profile.json")
    gen_requests = safe_load_json(manifest.get("generated_asset_requests")) or safe_load_json("generated_asset_requests.json")
    assembly_plan = safe_load_json(manifest.get("assembly_plan")) or safe_load_json("assembly_plan.json")
    timeline_build = safe_load_json(manifest.get("timeline_build")) or safe_load_json("timeline_build.json")
    editor_review = safe_load_json(manifest.get("editor_review")) or safe_load_json("editor_review.json")
    visual_review_request = safe_load_json(manifest.get("visual_review_request")) or safe_load_json("visual_review_request.json")
    visual_review_verdict = safe_load_json(manifest.get("visual_review_verdict")) or safe_load_json("visual_review_verdict.json")
    state_data = safe_load_json(manifest.get("state")) or safe_load_json("state.json")
    verify_result = safe_load_json(manifest.get("verify_result")) or safe_load_json("qa_report.json") or safe_load_json("verify_result.json")
    
    effects_render_plan = safe_load_json(manifest.get("motion_graphics_render_plan")) or safe_load_json("motion_graphics_render_plan.json")
    effects_manifest = safe_load_json(manifest.get("motion_graphics_manifest")) or safe_load_json("motion_graphics_manifest.json")
    light_effects_baseline_review = (
        safe_load_json(manifest.get("light_effects_baseline_review"))
        or safe_load_json("light_effects_baseline_review.json")
    )
    generated_manifest = safe_load_json(manifest.get("generated_asset_manifest")) or safe_load_json("generated_asset_manifest.json")

    # P1 verification tool pack (optional VERIFY evidence, not SPEC truth)
    timeline_invariants = safe_load_json(manifest.get("timeline_invariants")) or safe_load_json("timeline_invariants.json")
    broll_audit = safe_load_json(manifest.get("broll_audit")) or safe_load_json("broll_audit.json")
    caption_audit = safe_load_json(manifest.get("caption_audit")) or safe_load_json("caption_audit.json")
    visual_audit = safe_load_json(manifest.get("visual_audit")) or safe_load_json("visual_audit.json")
    presentation_feel_audit = (
        safe_load_json(manifest.get("presentation_feel_audit"))
        or safe_load_json("presentation_feel_audit.json")
    )
    treatment_audit = safe_load_json(manifest.get("treatment_audit")) or safe_load_json("treatment_audit.json")
    visual_fatigue_audit = safe_load_json(manifest.get("visual_fatigue_audit")) or safe_load_json("visual_fatigue_audit.json")
    editorial_qa = safe_load_json(manifest.get("editorial_qa")) or safe_load_json("editorial_qa.json")
    keyframe_grid_rel = manifest.get("keyframe_grid") or "keyframe_grid.jpg"
    _kg_abs = keyframe_grid_rel if os.path.isabs(keyframe_grid_rel) else os.path.join(workdir, keyframe_grid_rel)
    keyframe_grid_present = os.path.exists(_kg_abs)

    audit_data = {
        "timeline_invariants": timeline_invariants,
        "broll_audit": broll_audit,
        "caption_audit": caption_audit,
        "visual_audit": visual_audit,
        "presentation_feel_audit": presentation_feel_audit,
        "treatment_audit": treatment_audit,
        "visual_fatigue_audit": visual_fatigue_audit,
        "editorial_qa": editorial_qa,
    }
    audit_evidence = {
        role: (manifest.get(role) or f"{role}.json")
        for role in ("timeline_invariants", "broll_audit", "caption_audit", "visual_audit",
                     "presentation_feel_audit",
                     "treatment_audit", "visual_fatigue_audit", "editorial_qa")
    }
    # node ownership: 11 = editor review, 12 = verify
    NODE_AUDIT_MAP = {
        11: ["timeline_invariants", "broll_audit", "caption_audit", "treatment_audit",
             "visual_fatigue_audit"],
        12: ["caption_audit", "keyframe_grid", "visual_audit", "presentation_feel_audit",
             "editorial_qa"],
    }
    AUDIT_PRIMARY_NODE = {
        "timeline_invariants": 11, "broll_audit": 11, "caption_audit": 11,
        "keyframe_grid": 12, "visual_audit": 12, "treatment_audit": 11,
        "visual_fatigue_audit": 11, "presentation_feel_audit": 12, "editorial_qa": 12,
    }

    def generated_request_items(payload):
        if not payload:
            return []
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            if isinstance(payload.get("items"), list):
                return payload["items"]
            if isinstance(payload.get("requests"), list):
                return payload["requests"]
        return []

    gen_request_items = generated_request_items(gen_requests)

    # Determine final video
    final_file = manifest.get("final", "final.mp4")
    final_exists = False
    if os.path.isabs(final_file):
        final_exists = os.path.exists(final_file)
    else:
        final_exists = os.path.exists(os.path.join(workdir, final_file))
    
    if not final_exists and os.path.isdir(workdir):
        # Scan for any *final*.mp4
        for f in os.listdir(workdir):
            if f.endswith("final.mp4") or "final" in f and f.endswith(".mp4"):
                final_exists = True
                final_file = f
                break

    project_name = os.path.basename(os.path.abspath(workdir))
    updated_time = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    findings = []
    node_list = []

    # Determine effects requirements first
    effects_required = False
    if profile_data:
        effects_required = profile_data.get("effects_enabled", False)

    # Load registry
    from video_pipeline_core.node_registry import NODE_REGISTRY, NODE_ORDER
    
    # Prepare artifacts dict
    artifacts = {
        "brief": brief_data,
        "contract": contract_data,
        "material_coverage": material_coverage,
        "music_structure": music_struct_data,
        "build_profile": profile_data,
        "generated_requests": gen_requests,
        "generated_manifest": generated_manifest,
        "assembly_plan": assembly_plan,
        "timeline_build": timeline_build,
        "editor_review": editor_review,
        "visual_review_request": visual_review_request,
        "visual_review_verdict": visual_review_verdict,
        "state": state_data,
        "verify_result": verify_result,
        "motion_graphics_render_plan": effects_render_plan,
        "motion_graphics_manifest": effects_manifest,
        "light_effects_baseline_review": light_effects_baseline_review,
    }
    
    # Determine pass status: Prioritize verify_result if present
    is_pass = False
    if verify_result and "pass" in verify_result:
        is_pass = verify_result["pass"]
    elif state_data and "pass" in state_data:
        is_pass = state_data["pass"]

    # Prepare context
    context = {
        "final_exists": final_exists,
        "effects_required": effects_required,
        "gen_request_items": gen_request_items,
        "is_pass": is_pass
    }

    
    # Evaluate nodes using registry
    for node_id in NODE_ORDER:
        node_def = NODE_REGISTRY[node_id]
        status, reason = node_def["verify_fn"](workdir, artifacts, context)
        artifact_links = []
        for output in node_def.get("outputs", []):
            role = os.path.splitext(os.path.basename(output))[0]
            declared = manifest.get(role) or output
            path = declared if os.path.isabs(str(declared)) else os.path.join(workdir, str(declared))
            if os.path.exists(path):
                artifact_links.append({
                    "role": role,
                    "path": os.path.abspath(path),
                    "kind": "directory" if os.path.isdir(path) else "file",
                })
        
        # Add warnings/errors to findings
        if node_id == "8" and status == "warn":
            findings.append({
                "type": "warning",
                "node": 8,
                "message": "Generated requests exist but no generated manifest"
            })
        elif node_id == "8" and status == "blocked":
            findings.append({
                "type": "error",
                "node": 8,
                "message": "ComfyUI provider in build profile produces blocked/deprecated finding"
            })
        elif node_id == "10" and status == "warn":
            findings.append({
                "type": "warning",
                "node": 10,
                "message": "Timeline item has no trace"
            })
        elif node_id == "14" and status == "missing":
            findings.append({
                "type": "error",
                "node": 14,
                "message": "Effects enabled but render plan missing"
            })
            
        node_int = int(node_id) if node_id.isdigit() else node_id
        node_audits = []
        for role in NODE_AUDIT_MAP.get(node_int, []):
            if role == "keyframe_grid":
                if keyframe_grid_present:
                    node_audits.append({"role": "keyframe_grid", "pass": None,
                                        "evidence": keyframe_grid_rel})
                continue
            data = audit_data.get(role)
            if data:
                node_audits.append({
                    "role": role,
                    "pass": data.get("pass"),
                    "next_action": data.get("next_action"),
                    "evidence": audit_evidence[role],
                })

        node_list.append({
            "node": node_int,
            "label": node_def["label"],
            "skill": " / ".join(node_def["skill"]),
            "artifact": node_def["outputs"][0] if node_def["outputs"] else "segment_contract.json", # fallback
            "status": status,
            "reason": reason,
            "audits": node_audits,
            "artifact_links": artifact_links,
        })



    # Surface P1 audit findings (failing -> error, warn-only -> warning)
    for role, data in audit_data.items():
        if not data:
            continue
        node_owner = AUDIT_PRIMARY_NODE[role]
        if data.get("pass") is False:
            findings.append({
                "type": "error",
                "node": node_owner,
                "artifact": role,
                "message": f"{role} failed: {data.get('next_action') or 'see findings'}",
            })
        else:
            sub = data.get("findings") or data.get("mechanical_findings") or []
            if any((f.get("level") in ("warn", "fail")) for f in sub):
                findings.append({
                    "type": "warning",
                    "node": node_owner,
                    "artifact": role,
                    "message": f"{role} reported advisory findings",
                })

    # Pre-BUILD SPEC review report (spec_review.json): blocking findings mean the
    # SPEC contradicts itself or will silently lose content — surface them so the
    # run never quietly proceeds past a not-ready SPEC.
    spec_review_data = safe_load_json("spec_review.json")
    if spec_review_data and not spec_review_data.get("ready_for_build", True):
        for b in (spec_review_data.get("blocking") or [])[:6]:
            findings.append({
                "type": "error",
                "node": 3,
                "artifact": "spec_review",
                "message": f"spec_review blocking: {b.get('message')}",
            })

    # Soul-layer guard: the contract declares editing intent (editing_intent /
    # material_treatment / sequence_grammar) but no editing_policy is active, so
    # the Node 11/12 soul guards (visual_fatigue_audit, editorial_qa) silently
    # skip. Surface that skip — the ai-video soul-v3 run shipped a monotone
    # single_hold film with zero warnings because of exactly this.
    _contract_segs = []
    if isinstance(contract_data, dict):
        _contract_segs = contract_data.get("segments") or []
    elif isinstance(contract_data, list):
        _contract_segs = contract_data
    soul_declared = any(
        isinstance(seg, dict) and (
            seg.get("editing_intent") or seg.get("material_treatment")
            or seg.get("sequence_grammar")
        )
        for seg in _contract_segs
    )
    if soul_declared and not (profile_data or {}).get("editing_policy"):
        findings.append({
            "type": "warning",
            "node": "10.5",
            "artifact": "editing_policy",
            "message": ("soul layer declared in contract but editing_policy is inactive "
                        "(no editorial_design.json) — visual_fatigue_audit and "
                        "editorial_qa were skipped"),
        })

    # Normalize next_action
    next_action = None
    if verify_result and verify_result.get("pass") is False:
        next_action = "verify_failed"
    elif state_data and state_data.get("next_action"):
        next_action = state_data.get("next_action")
    elif editor_review and editor_review.get("decision") in ("rerender", "block", "human_review"):
        dec = editor_review.get("decision")
        if dec in ("rerender", "block"):
            next_action = "fix_timeline_or_assembly"
        else:
            next_action = "human_review"
    elif gen_request_items and not generated_manifest:
        next_action = "wait_for_generated_provider"
    elif visual_review_request and not visual_review_verdict:
        next_action = "await_visual_review"
        findings.append({
            "type": "warning",
            "node": 11,
            "artifact": "visual_review_request.json",
            "message": "Visual review request awaits agent verdict",
        })
    else:
        # Check required missing nodes
        required_nodes_keys = [0, 3, 2, "4-7", 5, 8, 9, 10, "10.5", 11, 13, 12]
        if effects_required:
            required_nodes_keys.append(14)
            
        missing_node = None
        for n in node_list:
            if n["node"] in required_nodes_keys and n["status"] == "missing":
                missing_node = n
                break
        if missing_node:
            next_action = f"missing_artifact:{missing_node['artifact']}"

    if next_action == "missing_artifact:final.mp4":
        if profile_data and isinstance(profile_data, dict) and profile_data.get("render_backend") == "capcut_draft":
            draft_manifest_present = False
            capcut_exported_present = False
            if os.path.isdir(workdir):
                draft_manifest_present = os.path.exists(os.path.join(workdir, "capcut_draft_manifest.json"))
                capcut_exported_present = os.path.exists(os.path.join(workdir, "capcut_exported.mp4"))
            if draft_manifest_present and not capcut_exported_present:
                next_action = "await_capcut_export"
            
    if not next_action:
        # Check if final exists and pass is true
        if final_exists and is_pass:
            next_action = "complete_review_final"

    # Compile findings from verify result and state
    if state_data and state_data.get("blocking"):
        for b in state_data.get("blocking", []):
            findings.append({
                "type": "error",
                "segment": b.get("segment"),
                "message": f"seg{b.get('segment')} blocked: {b.get('reason')}"
            })

    # Populate segments timeline (three-layer)
    normalized_segs = []
    
    # 1. Start with contract data or fallback to state.json segments
    source_segments = []
    if contract_data:
        if isinstance(contract_data, list):
            source_segments = contract_data
        elif isinstance(contract_data, dict) and "segments" in contract_data:
            source_segments = contract_data["segments"]
            
    if not source_segments and state_data and "segments" in state_data:
        source_segments = state_data["segments"]

    # Load assembly plan maps
    assembly_map = {}
    if assembly_plan:
        plan_list = []
        if isinstance(assembly_plan, list):
            plan_list = assembly_plan
        elif isinstance(assembly_plan, dict) and "segments" in assembly_plan:
            plan_list = assembly_plan["segments"]
        for p in plan_list:
            if "segment" in p:
                assembly_map[p["segment"]] = p

    # Load timeline build maps
    timeline_map = {}
    if timeline_build:
        timeline_list = []
        if isinstance(timeline_build, list):
            timeline_list = timeline_build
        elif isinstance(timeline_build, dict) and "clips" in timeline_build:
            timeline_list = timeline_build["clips"]
        elif isinstance(timeline_build, dict) and "segments" in timeline_build:
            timeline_list = timeline_build["segments"]
            
        for t in timeline_list:
            if "segment" in t:
                timeline_map[t["segment"]] = t

    # Load gen requests maps
    gen_req_map = {}
    for r in gen_request_items:
        if "segment" in r:
            gen_req_map[r["segment"]] = r

    # Load verify score maps from content_qa or state
    qa_score_map = {}
    content_qa = safe_load_json("content_qa.json")
    if content_qa and "segments" in content_qa:
        for s in content_qa["segments"]:
            if "segment" in s:
                qa_score_map[s["segment"]] = s
    elif state_data and "segments" in state_data:
        for s in state_data["segments"]:
            if "segment" in s:
                qa_score_map[s["segment"]] = s

    for s in source_segments:
        seg_id = s.get("segment")
        if seg_id is None:
            continue
            
        # SPEC Layer
        spec = {
            "title": s.get("title", f"Segment {seg_id}"),
            "story_purpose": s.get("story_purpose", s.get("text", "")),
            "visual_desc": s.get("visual_desc", ""),
            "audio": s.get("audio", {}),
            "text": s.get("text", ""),
            "must_include": s.get("must_include", "")
        }
        
        # VERIFY Layer
        qs = qa_score_map.get(seg_id, {})

        # BUILD Layer
        ap = assembly_map.get(seg_id, {})
        tb = timeline_map.get(seg_id, {})
        gr = gen_req_map.get(seg_id, {})
        
        prov = tb.get("provider") or qs.get("provider") or gr.get("provider") or ap.get("provider")
        if not prov:
            src_val = s.get("source")
            src_path = tb.get("source_path", "")
            if src_val == "stock" or "mvstock_" in str(src_path):
                prov = "pexels"
            elif src_val == "local":
                prov = "local"
            else:
                prov = profile_data.get("fallback_visual_provider") if profile_data else "pexels"

        build = {
            "provider": prov,
            "selected_source": tb.get("source_path", tb.get("file", s.get("file", ""))),
            "timeline_in_out": f"{tb.get('timeline_in_sec', 0):.2f}s - {tb.get('timeline_out_sec', 0):.2f}s" if 'timeline_in_sec' in tb else "",
            "generated_request": gr.get("prompt", "")
        }
        
        verify = {
            "score": qs.get("score", s.get("score")),
            "status": qs.get("status", s.get("status", "done")),
            "finding": qs.get("block_reason", s.get("block_reason", "")),
            "next_action": qs.get("fix_target", s.get("fix_target", ""))
        }
        
        normalized_segs.append({
            "segment": seg_id,
            "title": spec.get("title", s.get("title", "")),
            "status": verify.get("status", "done"),
            "score": verify.get("score"),
            "source": s.get("source", "stock"),
            "layout": s.get("layout"),
            "kind": s.get("kind"),
            "fix_class": s.get("fix_class"),
            "fix_target": s.get("fix_target"),
            "block_reason": verify.get("finding", ""),
            "spec": spec,
            "build": build,
            "verify": verify
        })

    # Sort segments by segment ID
    normalized_segs.sort(key=lambda x: x["segment"])

    # Package normalized dashboard state
    generated_status = "none"
    if gen_request_items and generated_manifest:
        generated_status = "ready"
    elif gen_request_items:
        generated_status = "waiting"
    control_surface = {
        "read_only": True,
        "profile": {
            "render_profile": (profile_data or {}).get("render_profile"),
            "render_backend": (profile_data or {}).get("render_backend"),
            "fallback_visual_provider": (profile_data or {}).get("fallback_visual_provider"),
            "motion_graphics_backend": (profile_data or {}).get("motion_graphics_backend"),
            "effects_enabled": bool((profile_data or {}).get("effects_enabled")),
        },
        "generated_assets": {
            "requested": len(gen_request_items),
            "status": generated_status,
            "manifest_present": bool(generated_manifest),
        },
        "route": {
            "next_action": next_action,
            "pass": is_pass,
        },
    }
    normalized_state = {
        "run": {
            "project": project_name,
            "workdir": os.path.abspath(workdir),
            "final": final_file if final_exists else None,
            "next_action": next_action,
            "updated": updated_time,
            "pass": is_pass,
            "build_profile": profile_data or {}
        },
        "nodes": node_list,
        "segments": normalized_segs,
        "materials": scan_materials_via_regex(workdir),
        "artifacts": {
            "manifest": manifest,
            "build_profile": profile_data,
            "generated_requests": gen_requests,
            "generated_manifest": generated_manifest,
            "material_coverage": material_coverage,
            "assembly_plan": assembly_plan,
            "timeline_build": timeline_build,
            "editor_review": editor_review,
            "verify_result": verify_result,
            "state": state_data,
            "timeline_invariants": timeline_invariants,
            "broll_audit": broll_audit,
            "caption_audit": caption_audit,
            "visual_audit": visual_audit,
            "presentation_feel_audit": presentation_feel_audit,
            "editorial_qa": editorial_qa,
            "keyframe_grid": keyframe_grid_rel if keyframe_grid_present else None,
        },
        "next_action": next_action,
        "findings": findings,
        "controls": control_surface,
    }
    
    return normalized_state
