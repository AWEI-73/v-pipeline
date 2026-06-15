"""Visual family vocabulary validation and deterministic review normalization."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

def _nonempty_str(val) -> str:
    if not isinstance(val, str):
        raise ValueError(f"Value must be a string, got {type(val)}")
    trimmed = val.strip()
    if not trimmed:
        raise ValueError("String value cannot be empty or whitespace-only")
    return trimmed

def validate_visual_family_vocabulary(vocabulary) -> dict:
    """Validate a visual_family_vocabulary artifact and return a cleaned schema representation."""
    if not isinstance(vocabulary, dict):
        raise ValueError("Vocabulary must be a dictionary")
    
    role = vocabulary.get("artifact_role")
    version = vocabulary.get("version")
    
    if role != "visual_family_vocabulary":
        raise ValueError(f"Invalid artifact_role: expected 'visual_family_vocabulary', got {role!r}")
    if version != 1:
        raise ValueError(f"Invalid version: expected 1, got {version!r}")
        
    project = _nonempty_str(vocabulary.get("project"))
    
    families_list = vocabulary.get("families")
    if not isinstance(families_list, list):
        raise ValueError("Vocabulary 'families' must be a list")
        
    canonical_set = set()
    alias_to_canonical = {}
    
    validated_families = []
    
    for idx, fam in enumerate(families_list):
        ref = f"families[{idx}]"
        if not isinstance(fam, dict):
            raise ValueError(f"{ref} must be an object")
            
        family_name = _nonempty_str(fam.get("family"))
        definition = _nonempty_str(fam.get("definition"))
        aliases_list = fam.get("aliases")
        
        if not isinstance(aliases_list, list):
            raise ValueError(f"{ref}.aliases must be a list")
            
        if family_name in canonical_set:
            raise ValueError(f"Duplicate canonical family name: {family_name!r}")
        canonical_set.add(family_name)
        
        validated_aliases = []
        for a_idx, alias in enumerate(aliases_list):
            alias_ref = f"{ref}.aliases[{a_idx}]"
            alias_name = _nonempty_str(alias)
            
            if alias_name in alias_to_canonical:
                raise ValueError(
                    f"Alias {alias_name!r} in {ref} is already defined by family {alias_to_canonical[alias_name]!r}"
                )
            alias_to_canonical[alias_name] = family_name
            validated_aliases.append(alias_name)
            
        validated_families.append({
            "family": family_name,
            "definition": definition,
            "aliases": validated_aliases
        })
        
    # Check for alias conflicts with any canonical family name
    for alias_name, target_fam in alias_to_canonical.items():
        if alias_name in canonical_set:
            raise ValueError(
                f"Alias {alias_name!r} conflicts with canonical family name"
            )
            
    return {
        "project": project,
        "canonical_families": canonical_set,
        "alias_to_canonical": alias_to_canonical,
        "families": validated_families
    }

def normalize_visual_diversity_review(review, vocabulary) -> dict:
    """Normalize a review against a visual family vocabulary contract."""
    if not isinstance(review, dict):
        raise ValueError("Review must be a dictionary")
        
    role = review.get("artifact_role")
    version = review.get("version")
    
    if role != "visual_diversity_review":
        raise ValueError(f"Invalid artifact_role: expected 'visual_diversity_review', got {role!r}")
    if version != 1:
        raise ValueError(f"Invalid version: expected 1, got {version!r}")
        
    reviewer = _nonempty_str(review.get("reviewer"))
    at = _nonempty_str(review.get("at"))
    
    scenes = review.get("scenes")
    if not isinstance(scenes, list):
        raise ValueError("Review 'scenes' must be a list")
        
    # Validate vocabulary and extract lookup tables
    vocab_meta = validate_visual_family_vocabulary(vocabulary)
    project_name = vocab_meta["project"]
    canonical_families = vocab_meta["canonical_families"]
    alias_to_canonical = vocab_meta["alias_to_canonical"]
    
    normalized_scenes = []
    
    for idx, scene in enumerate(scenes):
        ref = f"scenes[{idx}]"
        if not isinstance(scene, dict):
            raise ValueError(f"{ref} must be an object")
            
        # visual_family must be a non-empty string
        original_family = _nonempty_str(scene.get("visual_family"))
        
        # Check normalization
        if original_family in canonical_families:
            canonical_family = original_family
        elif original_family in alias_to_canonical:
            canonical_family = alias_to_canonical[original_family]
        else:
            raise ValueError(
                f"Review scene at index {idx} has family {original_family!r} which is not defined in the vocabulary contract"
            )
            
        # Create a copy of the scene to avoid mutating the original
        new_scene = copy.deepcopy(scene)
        new_scene["visual_family"] = canonical_family
        new_scene["visual_family_normalization"] = {
            "vocabulary_project": project_name,
            "original_family": original_family,
            "canonical_family": canonical_family
        }
        normalized_scenes.append(new_scene)
        
    normalized_review = copy.deepcopy(review)
    normalized_review["reviewer"] = reviewer
    normalized_review["at"] = at
    normalized_review["scenes"] = normalized_scenes
    return normalized_review

def write_normalized_review(review_path, vocabulary_path, out_path):
    """Normalize a review against a vocabulary file and write atomically."""
    with open(review_path, encoding="utf-8-sig") as handle:
        review = json.load(handle)
    with open(vocabulary_path, encoding="utf-8-sig") as handle:
        vocabulary = json.load(handle)
        
    normalized = normalize_visual_diversity_review(review, vocabulary)
    
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".normalized-review.tmp")
    try:
        temp.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
    return normalized
