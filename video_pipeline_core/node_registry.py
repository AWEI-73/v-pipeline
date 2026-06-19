import os
import json
from pathlib import Path

def verify_brief(workdir, artifacts, context):
    brief_data = artifacts.get("brief")
    status = "done" if brief_data else "missing"
    reason = "Brief specification exists" if status == "done" else "No brief found"
    return status, reason

def verify_contract(workdir, artifacts, context):
    contract_data = artifacts.get("contract")
    status = "done" if contract_data else "missing"
    reason = "Contract not defined"
    if contract_data:
        if isinstance(contract_data, list):
            reason = f"{len(contract_data)} segments defined"
        elif isinstance(contract_data, dict):
            segments = contract_data.get("segments", [])
            reason = f"{len(segments)} segments defined"
    return status, reason

def verify_material_coverage(workdir, artifacts, context):
    contract_data = artifacts.get("contract")
    material_coverage = artifacts.get("material_coverage")
    
    material_source_mode = None
    if isinstance(contract_data, dict):
        material_source_mode = contract_data.get("material_source_mode")
        
    status = "done" if material_coverage else "missing"
    reason = "Material coverage map exists" if status == "done" else "Material coverage not mapped"
    
    if isinstance(material_coverage, dict):
        weak = material_coverage.get("weak") or material_coverage.get("missing") or material_coverage.get("blocking")
        if weak:
            status = "warn"
            reason = "Coverage has weak/missing material"
            
    if material_source_mode == "stock_first":
        status = "done"
        reason = "Material coverage map optional (stock_first mode)"
        
    return status, reason

def verify_facets(workdir, artifacts, context):
    contract_data = artifacts.get("contract")
    facet_keys = ("core", "material_fit", "audio", "text_layer", "visual_style", "editing_grammar")
    reason_required = ("material_fit", "audio", "text_layer", "visual_style", "editing_grammar")
    status = "missing"
    reason = "Contract facets missing"
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
                    elif key == "text_layer" and facet == "none":
                        # the string "none" IS the explicit declaration (design rule:
                        # 留白也是顯式設計) — don't demand a reason dict for it, or the
                        # gate warns forever and agents learn to ignore warns.
                        reason_present += 1
            if present == total and reason_present == reason_total:
                status = "done"
                reason = "All required contract facets and reasons present"
            elif present == total:
                status = "warn"
                reason = f"Facet reasons incomplete ({reason_present}/{reason_total})"
            elif present > 0:
                status = "warn"
                reason = f"Partial facets present ({present}/{total})"
    return status, reason

def verify_audio(workdir, artifacts, context):
    music_struct = artifacts.get("music_structure")
    status = "done" if music_struct else "missing"
    reason = "Music structure analyzed" if status == "done" else "Audio structure missing"
    return status, reason

def verify_profile(workdir, artifacts, context):
    profile_data = artifacts.get("build_profile")
    gen_request_items = context.get("gen_request_items", [])
    generated_manifest = artifacts.get("generated_manifest")
    
    status = "missing"
    reason = "Build profile missing"
    if profile_data:
        if profile_data.get("fallback_visual_provider") == "comfyui":
            status = "blocked"
            reason = "blocked/deprecated provider comfyui"
        elif gen_request_items:
            if not generated_manifest:
                status = "warn"
                reason = "wait_for_generated_provider"
            else:
                status = "done"
                reason = f"Profile defined, {len(gen_request_items)} generated assets requested"
        else:
            status = "done"
            reason = "Build profile defined"
    return status, reason

def verify_assembly(workdir, artifacts, context):
    assembly_plan = artifacts.get("assembly_plan")
    status = "done" if assembly_plan else "missing"
    reason = "Assembly plan resolved" if status == "done" else "Assembly plan missing"
    return status, reason

def verify_timeline(workdir, artifacts, context):
    timeline_build = artifacts.get("timeline_build")
    status = "missing"
    reason = "Timeline not built"
    if timeline_build:
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
            status = "warn"
            reason = "timeline item has no trace"
        else:
            status = "done"
            reason = f"Timeline compiled ({len(clips)} clips)"
    return status, reason

def verify_visual_judge(workdir, artifacts, context):
    request = artifacts.get("visual_review_request")
    verdict = artifacts.get("visual_review_verdict")
    if request and verdict:
        return "done", "Visual review verdict recorded"
    if request:
        return "warn", "Visual review request awaits agent verdict"
    if verdict:
        return "warn", "Visual review verdict exists without request"
    return "optional", "No visual review requested"


def verify_editor_review(workdir, artifacts, context):
    editor_review = artifacts.get("editor_review")
    status = "missing"
    reason = "Editor review pending"
    if editor_review:
        decision = editor_review.get("decision")
        if not decision:
            status_val = editor_review.get("status")
            if status_val == "pass":
                decision = "approve"
            elif status_val == "warn":
                decision = "human_review"
            elif status_val == "fail":
                decision = "block"
        if decision == "approve":
            status = "done"
        elif decision in ("auto_fix", "route_change", "human_review"):
            status = "warn"
        elif decision in ("rerender", "block"):
            status = "blocked"
        reason = editor_review.get("reason") or f"Decision: {decision}"
    return status, reason

def verify_verify(workdir, artifacts, context):
    verify_result = artifacts.get("verify_result")
    state_data = artifacts.get("state")
    status = "missing"
    reason = "Verification report (verify_result.json) missing"
    if verify_result:
        if verify_result.get("pass"):
            status = "done"
            reason = f"Technical verify passed (score: {verify_result.get('score', 100)})"
        else:
            if verify_result.get("issues"):
                status = "blocked"
                reason = f"Blocked: Verify failed (score: {verify_result.get('score', 0)})"
            else:
                status = "warn"
                reason = f"Warn: Verify failed (score: {verify_result.get('score', 0)})"
    elif state_data:
        status = "warn"
        reason = "state.json exists but verify_result.json is missing"
    return status, reason

def verify_render(workdir, artifacts, context):
    final_exists = context.get("final_exists", False)
    status = "done" if final_exists else "missing"
    reason = "Final video rendered" if status == "done" else "Video not rendered"
    return status, reason

def verify_revision(workdir, artifacts, context):
    profile_data = artifacts.get("build_profile")
    effects_render_plan = artifacts.get("motion_graphics_render_plan")
    effects_manifest = artifacts.get("motion_graphics_manifest")
    baseline_review = artifacts.get("light_effects_baseline_review")
    effect_revision_request = artifacts.get("effect_revision_request")
    effect_recipe_patch = artifacts.get("effect_recipe_patch")
    
    effects_required = False
    if profile_data:
        effects_required = profile_data.get("effects_enabled", False)
        
    status = "optional"
    reason = "No revision plan required"
    if effect_recipe_patch and effect_recipe_patch.get("status") == "pending":
        count = (effect_recipe_patch.get("summary") or {}).get("patch_count", 0)
        status = "warn"
        reason = f"{count} effect recipe patch draft(s) pending review"
    elif effect_revision_request and effect_revision_request.get("status") == "pending":
        count = (effect_revision_request.get("summary") or {}).get("request_count", 0)
        status = "warn"
        reason = f"{count} effect revision request(s) pending Node14 routing"
    elif effect_revision_request and effect_revision_request.get("status") == "empty":
        status = "done"
        reason = "Effect revision request found no render gaps"
    elif baseline_review and baseline_review.get("status") == "gaps_found":
        gap_count = (baseline_review.get("metrics") or {}).get("gap_count", 0)
        status = "warn"
        reason = f"{gap_count} light-effects render gap(s) require recipes or wiring"
    elif effects_render_plan or effects_manifest or baseline_review:
        status = "done"
        reason = "Motion graphics/effects plan resolved"
    elif effects_required:
        status = "missing"
        reason = "Effects enabled but render plan missing"
    return status, reason

NODE_ORDER = ["0", "3", "2", "4-7", "5", "8", "9", "10", "10.5", "11", "13", "12", "14"]

NODE_REGISTRY = {
    "0": {
        "node": "0",
        "label": "Brief",
        "skill": ["video-workflow"],
        "runner": "agent",
        "inputs": [],
        "outputs": ["brief.json"],
        "verify_fn": verify_brief,
        "description": "Brief specification"
    },
    "3": {
        "node": "3",
        "label": "Contract",
        "skill": ["spec-contract", "director"],
        "runner": "agent",
        "inputs": ["brief.json"],
        "outputs": ["segment_contract.json"],
        "verify_fn": verify_contract,
        "description": "Segment contract"
    },
    "2": {
        "node": "2",
        "label": "Material Coverage",
        "skill": ["curator", "gap-analyzer"],
        "runner": "curator",
        "inputs": ["segment_contract.json"],
        "outputs": ["material_coverage_map.json"],
        "verify_fn": verify_material_coverage,
        "description": "Material coverage map"
    },
    "4-7": {
        "node": "4-7",
        "label": "Contract Facets",
        "skill": ["writer", "audio-director", "effects-director", "director", "curator"],
        "runner": "agent",
        "inputs": ["segment_contract.json"],
        "outputs": [],
        "verify_fn": verify_facets,
        "description": "Populated contract facets"
    },
    "5": {
        "node": "5",
        "label": "Audio",
        "skill": ["audio-director"],
        "runner": "audio-director",
        "inputs": ["segment_contract.json"],
        "outputs": ["music_structure.json"],
        "verify_fn": verify_audio,
        "description": "Music structure"
    },
    "8": {
        "node": "8",
        "label": "Fallback/Profile",
        "skill": ["gap-analyzer", "generative-director"],
        "runner": "route",
        "inputs": ["segment_contract.json", "material_coverage_map.json"],
        "outputs": ["build_profile.json"],
        "verify_fn": verify_profile,
        "description": "Build profile"
    },
    "9": {
        "node": "9",
        "label": "Assembly",
        "skill": ["editor"],
        "runner": "editor",
        "inputs": ["segment_contract.json", "music_structure.json", "build_profile.json"],
        "outputs": ["assembly_plan.json"],
        "verify_fn": verify_assembly,
        "description": "Assembly plan"
    },
    "10": {
        "node": "10",
        "label": "Timeline",
        "skill": ["editor"],
        "runner": "editor",
        "inputs": ["assembly_plan.json"],
        "outputs": ["timeline_build.json"],
        "verify_fn": verify_timeline,
        "description": "EDL timeline build"
    },
    "10.5": {
        "node": "10.5",
        "label": "Visual Judge",
        "skill": ["visual_review"],
        "runner": "agent",
        "inputs": ["timeline_build.json", "visual_review_request.json"],
        "outputs": ["visual_review_request.json", "visual_review_verdict.json"],
        "verify_fn": verify_visual_judge,
        "description": "Agent visual-review gate"
    },
    "11": {
        "node": "11",
        "label": "Editor Review",
        "skill": ["editor_review"],
        "runner": "editor_review",
        "inputs": ["timeline_build.json"],
        "outputs": ["editor_review.json", "timeline_invariants.json", "broll_audit.json", "new_visual_information_audit.json", "caption_audit.json", "blueprint_coverage.json", "treatment_audit.json", "visual_fatigue_audit.json"],
        "verify_fn": verify_editor_review,
        "description": "Editor review decision"
    },
    "13": {
        "node": "13",
        "label": "Render Candidate",
        "skill": ["editor"],
        "runner": "compiler",
        "inputs": ["timeline_build.json", "editor_review.json"],
        "outputs": ["final.mp4", "polished_visual.mp4", "mv_av.mp4", "final_audio.wav", "subtitles.srt", "capcut_draft_manifest.json", "capcut_export_manifest.json"],
        "verify_fn": verify_render,
        "description": "Final video render (ffmpeg canonical; optional capcut_draft backend)"
    },
    "12": {
        "node": "12",
        "label": "Verify",
        "skill": ["verify"],
        "runner": "verify",
        "inputs": ["final.mp4"],
        "outputs": ["verify_result.json", "qa_report.json", "keyframe_grid.jpg", "visual_audit.json",
                    "presentation_feel_audit.json", "editorial_qa.json"],
        "verify_fn": verify_verify,
        "description": "QA verify report"
    },
    "14": {
        "node": "14",
        "label": "Revision",
        "skill": ["route", "editor", "verify", "dashboard"],
        "runner": "route",
        "inputs": ["verify_result.json"],
        "outputs": ["revision_plan.json", "motion_graphics_render_plan.json", "motion_graphics_manifest.json",
                    "light_effects_baseline_review.json", "effect_revision_request.json",
                    "effect_recipe_patch.json"],
        "verify_fn": verify_revision,
        "description": "Revision plan"
    }
}
