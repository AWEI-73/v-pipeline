"""blueprint_compile.py — Blueprint compiler from markdown to JSON.

Compiles a human-written narrative blueprint markdown file into a structured
narrative_blueprint JSON object.
All functions are pure (no I/O, no print).
"""
from __future__ import annotations

import re


def compile_blueprint_md(md_text: str) -> dict:
    """Compile a markdown narrative blueprint into a structured dictionary.

    Format expected in blueprint.md:
      - Global metadata lines anywhere (e.g. 'Mode: rhythmic_mv', 'Feeling: warm')
      - Section '# Thesis': the first sentence of the text under this header is the thesis.
      - Section '# Big Story': bullet points matching '- [ID|role] summary [feeling: X]'
      - Section '# Anti-goals': bullet points listing anti-goals.

    Raises:
        ValueError: If thesis is missing, or beats list is empty.
    """
    lines = md_text.splitlines()

    mode_hint = "warm_documentary"
    intended_feeling = "warm"
    thesis = ""
    beats = []
    anti_goals = []

    # Parse global metadata first
    for line in lines:
        stripped = line.strip()
        # Look for "Mode: <val>" or "Mode hint: <val>"
        mode_match = re.match(
            r"^(?:mode|mode[-_\s]+hint|video[-_\s]+mode)\s*:\s*(.*)$",
            stripped,
            re.IGNORECASE,
        )
        if mode_match:
            mode_hint = mode_match.group(1).strip()

        # Look for "Intended feeling: <val>" or "Feeling: <val>"
        feeling_match = re.match(
            r"^(?:intended[-_\s]+feeling|feeling)\s*:\s*(.*)$",
            stripped,
            re.IGNORECASE,
        )
        if feeling_match:
            intended_feeling = feeling_match.group(1).strip()

    # Split into sections based on headers
    current_section = ""
    section_texts: dict[str, list[str]] = {
        "thesis": [],
        "big story": [],
        "anti-goals": [],
    }

    for line in lines:
        stripped = line.strip()
        header_match = re.match(r"^#+\s*(.*)$", stripped)
        if header_match:
            header_name = header_match.group(1).strip().lower()
            if "thesis" in header_name:
                current_section = "thesis"
            elif "big story" in header_name or "story" in header_name:
                current_section = "big story"
            elif "anti-goals" in header_name or "anti_goals" in header_name:
                current_section = "anti-goals"
            else:
                current_section = ""
            continue

        if current_section:
            section_texts[current_section].append(line)

    # 1. Parse Thesis
    thesis_lines = section_texts["thesis"]
    thesis_text = " ".join([l.strip() for l in thesis_lines if l.strip()])
    if thesis_text:
        # Split into sentences by . or ! or ? or 。 or ！ or ？
        sentences = re.split(r"([.!?。！？]\s*)", thesis_text)
        if len(sentences) >= 2:
            thesis = sentences[0].strip() + sentences[1].strip()
        elif sentences:
            thesis = sentences[0].strip()

    if not thesis:
        raise ValueError("Missing required thesis section or first sentence under # Thesis header")

    # 2. Parse Beats
    beat_pattern = re.compile(
        r"^\s*[-*]\s*\[([^\]|]+)(?:\|([^\]]+))?\]\s*(.*)$"
    )
    for line in section_texts["big story"]:
        stripped = line.strip()
        if not stripped:
            continue
        match = beat_pattern.match(stripped)
        if match:
            b_id = match.group(1).strip()
            b_role = (match.group(2) or "detail").strip()
            b_summary = match.group(3).strip()

            # Inline feeling extraction e.g. [Feeling: calm] or (feeling: calm) or {feeling: calm}
            b_feeling = None
            feeling_inline_pattern = re.compile(
                r"[\[({](?:intended[-_]feeling|feeling):\s*([^\])}]+)[\])}]",
                re.IGNORECASE,
            )
            fim = feeling_inline_pattern.search(b_summary)
            if fim:
                b_feeling = fim.group(1).strip()
                b_summary = b_summary.replace(fim.group(0), "").strip()

            beat_dict: dict[str, str] = {
                "id": b_id,
                "role": b_role,
                "summary": b_summary,
            }
            if b_feeling:
                beat_dict["intended_feeling"] = b_feeling

            beats.append(beat_dict)

    if not beats:
        raise ValueError("Missing required beats in Big Story section")

    # 3. Parse Anti-goals
    bullet_pattern = re.compile(r"^\s*[-*]\s*(.*)$")
    for line in section_texts["anti-goals"]:
        stripped = line.strip()
        if not stripped:
            continue
        bm = bullet_pattern.match(stripped)
        if bm:
            anti_goals.append(bm.group(1).strip())

    return {
        "artifact_role": "narrative_blueprint",
        "version": 1,
        "thesis": thesis,
        "intended_feeling": intended_feeling,
        "mode_hint": mode_hint,
        "beats": beats,
        "anti_goals": anti_goals,
    }
