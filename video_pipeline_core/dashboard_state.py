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

    # Load artifacts safely
    brief_data = safe_load_json(manifest.get("brief", "brief.json"))
    contract_data = safe_load_json(manifest.get("canonical_contract", "segment_contract.json"))
    material_coverage = safe_load_json(manifest.get("material_coverage_map", "material_coverage_map.json"))
    music_struct_data = safe_load_json(manifest.get("music_structure", "music_structure.json"))
    profile_data = safe_load_json(manifest.get("build_profile", "build_profile.json"))
    gen_requests = safe_load_json(manifest.get("generated_asset_requests", "generated_asset_requests.json"))
    assembly_plan = safe_load_json(manifest.get("assembly_plan", "assembly_plan.json"))
    timeline_build = safe_load_json(manifest.get("timeline_build", "timeline_build.json"))
    editor_review = safe_load_json(manifest.get("editor_review", "editor_review.json"))
    state_data = safe_load_json(manifest.get("state", "state.json"))
    verify_result = safe_load_json(manifest.get("verify_result", "qa_report.json"))
    if not verify_result:
        verify_result = safe_load_json("verify_result.json")
    
    effects_render_plan = safe_load_json(manifest.get("motion_graphics_render_plan", "motion_graphics_render_plan.json"))
    effects_manifest = safe_load_json(manifest.get("motion_graphics_manifest", "motion_graphics_manifest.json"))
    generated_manifest = safe_load_json(manifest.get("generated_asset_manifest", "generated_asset_manifest.json"))

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

    # Node 0: Brief
    n0_status = "done" if brief_data else "missing"
    node_list.append({
        "node": 0,
        "label": "Brief",
        "skill": "video-workflow",
        "artifact": "brief.json",
        "status": n0_status,
        "reason": "Brief specification exists" if n0_status == "done" else "No brief found"
    })

    # Node 2: Material Coverage
    n2_status = "done" if material_coverage else "missing"
    n2_reason = "Material coverage map exists" if n2_status == "done" else "Material coverage not mapped"
    if isinstance(material_coverage, dict):
        weak = material_coverage.get("weak") or material_coverage.get("missing") or material_coverage.get("blocking")
        if weak:
            n2_status = "warn"
            n2_reason = "Coverage has weak/missing material"
    node_list.append({
        "node": 2,
        "label": "Material Coverage",
        "skill": "curator / gap-analyzer",
        "artifact": "material_coverage_map.json",
        "status": n2_status,
        "reason": n2_reason
    })

    # Node 3: Contract
    n3_status = "done" if contract_data else "missing"
    node_list.append({
        "node": 3,
        "label": "Contract",
        "skill": "spec-contract",
        "artifact": "segment_contract.json",
        "status": n3_status,
        "reason": f"{len(contract_data)} segments defined" if n3_status == "done" else "Contract not defined"
    })

    # Node 4-7: Contract Facets
    facet_keys = ("core", "material_fit", "audio", "text_layer", "visual_style", "editing_grammar")
    reason_required = ("material_fit", "audio", "text_layer", "visual_style", "editing_grammar")
    facet_status = "missing"
    facet_reason = "Contract facets missing"
    if contract_data:
        segments = contract_data.get("segments") if isinstance(contract_data, dict) else contract_data
        segments = segments if isinstance(segments, list) else []
        if segments:
            present = 0
            reason_present = 0
            total = len(segments) * len(facet_keys)
            reason_total = len(segments) * len(reason_required)
            for seg in segments:
                present += sum(1 for key in facet_keys if key in seg)
                for key in reason_required:
                    facet = seg.get(key)
                    if isinstance(facet, dict) and facet.get("reason"):
                        reason_present += 1
            if present == total and reason_present == reason_total:
                facet_status = "done"
                facet_reason = "All required contract facets and reasons present"
            elif present == total:
                facet_status = "warn"
                facet_reason = f"Facet reasons incomplete ({reason_present}/{reason_total})"
            elif present > 0:
                facet_status = "warn"
                facet_reason = f"Partial facets present ({present}/{total})"
    node_list.append({
        "node": "4-7",
        "label": "Contract Facets",
        "skill": "writer / audio-director / effects-director / director / curator",
        "artifact": "segment_contract.json",
        "status": facet_status,
        "reason": facet_reason
    })

    # Node 5: Audio
    n5_status = "done" if music_struct_data else "missing"
    node_list.append({
        "node": 5,
        "label": "Audio",
        "skill": "audio-director",
        "artifact": "music_structure.json",
        "status": n5_status,
        "reason": "Music structure analyzed" if n5_status == "done" else "Audio structure missing"
    })

    # Node 8: Fallback/Profile
    n8_status = "missing"
    n8_reason = "Build profile missing"
    if profile_data:
        if profile_data.get("fallback_visual_provider") == "comfyui":
            n8_status = "blocked"
            n8_reason = "blocked/deprecated provider comfyui"
            findings.append({
                "type": "error",
                "node": 8,
                "message": "ComfyUI provider in build profile produces blocked/deprecated finding"
            })
        elif gen_request_items:
            # check if generated manifest exists
            if not generated_manifest:
                n8_status = "warn"
                n8_reason = "wait_for_generated_provider"
                findings.append({
                    "type": "warning",
                    "node": 8,
                    "message": "Generated requests exist but no generated manifest"
                })
            else:
                n8_status = "done"
                n8_reason = f"Profile defined, {len(gen_request_items)} generated assets requested"
        else:
            n8_status = "done"
            n8_reason = "Build profile defined"
            
    node_list.append({
        "node": 8,
        "label": "Fallback/Profile",
        "skill": "gap-analyzer / generative-director",
        "artifact": "build_profile.json",
        "status": n8_status,
        "reason": n8_reason
    })

    # Node 9: Assembly
    n9_status = "done" if assembly_plan else "missing"
    node_list.append({
        "node": 9,
        "label": "Assembly",
        "skill": "editor",
        "artifact": "assembly_plan.json",
        "status": n9_status,
        "reason": "Assembly plan resolved" if n9_status == "done" else "Assembly plan missing"
    })

    # Node 10: Timeline
    n10_status = "missing"
    n10_reason = "Timeline not built"
    if timeline_build:
        # Check if timeline has clips and if any clip lacks trace
        clips = timeline_build.get("clips", [])
        if not clips and isinstance(timeline_build, list):
            clips = timeline_build
        lacks_trace = False
        if clips:
            for clip in clips:
                if not clip.get("trace"):
                    lacks_trace = True
                    break
        if lacks_trace:
            n10_status = "warn"
            n10_reason = "timeline item has no trace"
            findings.append({
                "type": "warning",
                "node": 10,
                "message": "Timeline item has no trace"
            })
        else:
            n10_status = "done"
            n10_reason = f"Timeline compiled ({len(clips)} clips)"
            
    node_list.append({
        "node": 10,
        "label": "Timeline",
        "skill": "editor",
        "artifact": "timeline_build.json",
        "status": n10_status,
        "reason": n10_reason
    })

    # Node 11: Editor Review
    n11_status = "missing"
    n11_reason = "Editor review pending"
    if editor_review:
        decision = editor_review.get("decision")
        if decision == "approve":
            n11_status = "done"
        elif decision in ("auto_fix", "route_change", "human_review"):
            n11_status = "warn"
        elif decision in ("rerender", "block"):
            n11_status = "blocked"
        n11_reason = editor_review.get("reason") or f"Decision: {decision}"
        
    node_list.append({
        "node": 11,
        "label": "Editor Review",
        "skill": "editor_review",
        "artifact": "editor_review.json",
        "status": n11_status,
        "reason": n11_reason
    })

    # Node 12: Verify
    n12_status = "missing"
    n12_reason = "Verification not run"
    if state_data or verify_result:
        t_state = state_data or verify_result
        if t_state.get("pass"):
            n12_status = "done"
            n12_reason = f"Technical verify passed (score: {t_state.get('qa', {}).get('score', 100)})"
        else:
            # check if it's blocked or just warning
            if t_state.get("blocking") or t_state.get("next_action") == "await_material":
                n12_status = "blocked"
                n12_reason = f"Blocked: {t_state.get('next_action') or 'Verify failed'}"
            else:
                n12_status = "warn"
                n12_reason = f"Warn: {t_state.get('next_action') or 'Verify failed'}"
                
    node_list.append({
        "node": 12,
        "label": "Verify",
        "skill": "verify",
        "artifact": "state.json",
        "status": n12_status,
        "reason": n12_reason
    })

    # Node 13: Render
    n13_status = "done" if final_exists else "missing"
    node_list.append({
        "node": 13,
        "label": "Render",
        "skill": "editor",
        "artifact": "final.mp4",
        "status": n13_status,
        "reason": "Final video rendered" if n13_status == "done" else "Video not rendered"
    })

    # Node 14: Revision / Iteration. Motion graphics effects are an optional
    # BUILD artifact surfaced here as a revision-capable output.
    n14_status = "optional"
    n14_reason = "No revision plan required"
    effects_required = False
    if profile_data:
        effects_required = profile_data.get("effects_enabled", False)
        
    if effects_render_plan or effects_manifest:
        n14_status = "done"
        n14_reason = "Motion graphics/effects plan resolved"
    elif effects_required:
        n14_status = "missing"
        n14_reason = "Effects enabled but render plan missing"
        findings.append({
            "type": "error",
            "node": 14,
            "message": "Effects enabled but render plan missing"
        })
        
    node_list.append({
        "node": 14,
        "label": "Revision",
        "skill": "route / editor / verify / dashboard",
        "artifact": "revision_plan.json",
        "status": n14_status,
        "reason": n14_reason
    })

    # Normalize next_action
    next_action = None
    if state_data and state_data.get("next_action"):
        next_action = state_data.get("next_action")
    elif editor_review and editor_review.get("decision") in ("rerender", "block", "human_review"):
        dec = editor_review.get("decision")
        if dec in ("rerender", "block"):
            next_action = "fix_timeline_or_assembly"
        else:
            next_action = "human_review"
    elif gen_request_items and not generated_manifest:
        next_action = "wait_for_generated_provider"
    else:
        # Check required missing nodes
        required_nodes_keys = [0, 2, 3, "4-7", 5, 8, 9, 10, 11, 12, 13]
        if effects_required:
            required_nodes_keys.append(14)
            
        missing_node = None
        for n in node_list:
            if n["node"] in required_nodes_keys and n["status"] == "missing":
                missing_node = n
                break
        if missing_node:
            next_action = f"missing_artifact:{missing_node['artifact']}"
            
    if not next_action:
        # Check if final exists and pass is true
        t_state = state_data or verify_result
        if final_exists and t_state and t_state.get("pass"):
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
        
        # BUILD Layer
        ap = assembly_map.get(seg_id, {})
        tb = timeline_map.get(seg_id, {})
        gr = gen_req_map.get(seg_id, {})
        
        build = {
            "provider": gr.get("provider", ap.get("provider", profile_data.get("fallback_visual_provider") if profile_data else "pexels")),
            "selected_source": tb.get("source_path", tb.get("file", s.get("file", ""))),
            "timeline_in_out": f"{tb.get('timeline_in', 0):.2f}s - {tb.get('timeline_out', 0):.2f}s" if 'timeline_in' in tb else "",
            "generated_request": gr.get("prompt", "")
        }
        
        # VERIFY Layer
        qs = qa_score_map.get(seg_id, {})
        
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
    normalized_state = {
        "run": {
            "project": project_name,
            "workdir": os.path.abspath(workdir),
            "final": final_file if final_exists else None,
            "next_action": next_action,
            "updated": updated_time,
            "pass": (state_data or verify_result).get("pass") if (state_data or verify_result) else False,
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
            "state": state_data
        },
        "next_action": next_action,
        "findings": findings
    }
    
    return normalized_state
