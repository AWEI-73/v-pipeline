from __future__ import annotations

import re
import unicodedata
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_TEXT_PATHS = (
    "README.md",
    "RUNBOOK.md",
    "HANDOFF_CURRENT.md",
    "roadmap.md",
    "docs/START_HERE_VIDEO_PIPELINE.md",
    "docs/INDEX.md",
    "docs/build-capability-alignment.md",
    "docs/canonical-video-pipeline-route.md",
    "docs/editorial-layer.md",
    "skills/video-pipeline.md",
    "skills/video-pipeline-route.md",
    "skills/verify.md",
)


def _private_use_characters(text: str) -> list[str]:
    return [
        character
        for character in text
        if unicodedata.category(character) == "Co"
    ]


def _suspicious_question_lines(text: str) -> list[str]:
    allowed_instructional_examples = re.compile(
        r"(?:placeholders?|literal question|not [`']?\?{4})",
        re.IGNORECASE,
    )
    return [
        line
        for line in text.splitlines()
        if "??" in line and not allowed_instructional_examples.search(line)
    ]


class ActiveTextIntegrityTest(unittest.TestCase):
    def test_active_surfaces_are_valid_utf8_without_corruption(self):
        failures: list[str] = []
        for relative_path in ACTIVE_TEXT_PATHS:
            path = ROOT / relative_path
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                failures.append(f"{relative_path}: invalid UTF-8: {exc}")
                continue
            if "\ufffd" in text:
                failures.append(f"{relative_path}: contains U+FFFD")
            private = _private_use_characters(text)
            if private:
                failures.append(
                    f"{relative_path}: contains {len(private)} private-use characters"
                )
            suspicious = _suspicious_question_lines(text)
            if suspicious:
                failures.append(
                    f"{relative_path}: contains suspicious ?? on "
                    f"{len(suspicious)} line(s)"
                )
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
