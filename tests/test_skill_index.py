import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "skills" / "INDEX.md"
REGISTRY = ROOT / "docs" / "branch-contract-registry.json"


def _parse_index():
    rows = {}
    pattern = re.compile(
        r"^\|\s*`(?P<path>skills/[^`]+\.md)`\s*\|\s*(?P<owner>[^|]+?)\s*\|"
        r"\s*(?P<segment>[^|]+?)\s*\|\s*(?P<role>[^|]+?)\s*\|$"
    )
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        rows[match.group("path")] = {
            "owners": [item.strip() for item in match.group("owner").split(",")],
            "segment": match.group("segment").strip(),
            "role": match.group("role").strip(),
        }
    return rows


def _registry_claims():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    claims = {}
    for branch in registry["branches"]:
        owner = branch["branch_id"]
        for skill in branch.get("skills") or []:
            claims.setdefault(skill, set()).add(owner)
        for stage in branch.get("stages") or []:
            skill = stage.get("skill")
            if skill:
                claims.setdefault(skill, set()).add(owner)
    return claims, {branch["branch_id"] for branch in registry["branches"]}


class SkillIndexTest(unittest.TestCase):
    def test_every_live_skill_has_exactly_one_index_row(self):
        rows = _parse_index()
        skills = {
            path.as_posix().replace(f"{ROOT.as_posix()}/", "")
            for path in (ROOT / "skills").glob("*.md")
            if path.name != "INDEX.md"
        }

        live_rows = {rel for rel in rows if not rel.startswith("skills/archive/")}
        self.assertEqual(live_rows, skills)
        for rel in rows:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_registry_claimed_skills_have_same_owner(self):
        rows = _parse_index()
        claims, _owners = _registry_claims()

        for skill, expected_owners in claims.items():
            self.assertIn(skill, rows)
            self.assertEqual(set(rows[skill]["owners"]), expected_owners, skill)

    def test_index_owners_are_registry_branches_or_shared_or_archive(self):
        rows = _parse_index()
        _claims, branch_ids = _registry_claims()
        allowed = branch_ids | {"shared", "archive"}

        for skill, row in rows.items():
            for owner in row["owners"]:
                self.assertIn(owner, allowed, skill)


if __name__ == "__main__":
    unittest.main()
