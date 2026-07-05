"""Machine-readable acceptance command contract for work-order gates."""

from __future__ import annotations

from typing import Iterable, List, Mapping, Optional

from tools.test_tiers import TEST_TIERS


ARTIFACT_ROLE = "acceptance_command_contract"
VERSION = 1
EXPECTED_EXIT_BEHAVIOR = "0=pass; nonzero=fail"


ACCEPTANCE_COMMANDS: List[dict] = [
    {
        "id": "full-unittest",
        "argv": ["python", "-m", "unittest", "discover", "-s", "tests"],
        "purpose": "Run the full Python regression suite.",
        "intended_use": "final pre-commit or supervisor signoff after focused gates pass",
        "needs_run_dir": False,
        "fixture_argument": None,
        "expected_exit_behavior": EXPECTED_EXIT_BEHAVIOR,
        "owner_category": "unit",
    },
    {
        "id": "e2e-smoke-stock-story",
        "argv": ["python", "video_tools.py", "e2e-smoke", "--case", "stock_story"],
        "purpose": "Validate the stock story end-to-end smoke route.",
        "intended_use": "work-order acceptance for story/stock route changes",
        "needs_run_dir": False,
        "fixture_argument": None,
        "expected_exit_behavior": EXPECTED_EXIT_BEHAVIOR,
        "owner_category": "route",
    },
    {
        "id": "e2e-smoke-single-long-highlight",
        "argv": ["python", "video_tools.py", "e2e-smoke", "--case", "single_long_highlight"],
        "purpose": "Validate the single long highlight end-to-end smoke route.",
        "intended_use": "work-order acceptance for source highlight route changes",
        "needs_run_dir": False,
        "fixture_argument": None,
        "expected_exit_behavior": EXPECTED_EXIT_BEHAVIOR,
        "owner_category": "route",
    },
    {
        "id": "registry-audit",
        "argv": ["python", "video_tools.py", "registry-audit"],
        "purpose": "Audit branch registry route ownership and stage integrity.",
        "intended_use": "route contract acceptance and documentation work-order gates",
        "needs_run_dir": False,
        "fixture_argument": None,
        "expected_exit_behavior": EXPECTED_EXIT_BEHAVIOR,
        "owner_category": "audit",
    },
    {
        "id": "interface-audit",
        "argv": ["python", "video_tools.py", "interface-audit"],
        "purpose": "Audit command, workflow, capability, and acceptance contract references.",
        "intended_use": "command-surface and work-order gate validation",
        "needs_run_dir": False,
        "fixture_argument": None,
        "expected_exit_behavior": EXPECTED_EXIT_BEHAVIOR,
        "owner_category": "audit",
    },
    {
        "id": "asset-path-audit-strict",
        "argv": ["python", "video_tools.py", "asset-path-audit", "--strict", "<run-folder>"],
        "purpose": "Strictly audit a run folder for unsafe artifact paths.",
        "intended_use": "artifact-manifest and run-output acceptance after a fresh smoke run",
        "needs_run_dir": True,
        "fixture_argument": "<run-folder>",
        "expected_exit_behavior": EXPECTED_EXIT_BEHAVIOR,
        "owner_category": "artifact",
    },
    {
        "id": "test-tier-dev",
        "argv": ["python", "video_tools.py", "test-tiers", "--tier", "dev"],
        "purpose": "Run the bounded development tier.",
        "intended_use": "routine inner-loop command-surface checks",
        "needs_run_dir": False,
        "fixture_argument": None,
        "expected_exit_behavior": EXPECTED_EXIT_BEHAVIOR,
        "owner_category": "tier",
    },
    {
        "id": "test-tier-work-order-acceptance",
        "argv": ["python", "video_tools.py", "test-tiers", "--tier", "work-order-acceptance"],
        "purpose": "Run the standard supervisor work-order acceptance tier.",
        "intended_use": "pre-handoff acceptance after focused owner tests pass",
        "needs_run_dir": False,
        "fixture_argument": None,
        "expected_exit_behavior": EXPECTED_EXIT_BEHAVIOR,
        "owner_category": "tier",
    },
    {
        "id": "test-tier-full",
        "argv": ["python", "video_tools.py", "test-tiers", "--tier", "full"],
        "purpose": "Run the bounded full regression tier.",
        "intended_use": "full regression signoff through the tier runner",
        "needs_run_dir": False,
        "fixture_argument": None,
        "expected_exit_behavior": EXPECTED_EXIT_BEHAVIOR,
        "owner_category": "tier",
    },
]


def _video_tools_command_ref(argv: List[str]) -> Optional[str]:
    for index, part in enumerate(argv[:-1]):
        if str(part).replace("\\", "/").endswith("video_tools.py"):
            return str(argv[index + 1])
    return None


def _test_tier_ref(argv: List[str]) -> Optional[str]:
    for index, part in enumerate(argv[:-1]):
        if part == "--tier":
            return str(argv[index + 1])
    return None


def build_acceptance_contract(
    dispatch_commands: Iterable[str],
    *,
    extra_commands: Optional[Iterable[Mapping[str, object]]] = None,
) -> dict:
    available_commands = {str(command) for command in dispatch_commands}
    commands = [dict(command) for command in ACCEPTANCE_COMMANDS]
    commands.extend(dict(command) for command in (extra_commands or []))

    invalid_refs = []
    missing_dispatch = []
    missing_tiers = []
    for command in commands:
        argv = [str(part) for part in command.get("argv") or []]
        video_tools_ref = _video_tools_command_ref(argv)
        if video_tools_ref and video_tools_ref not in available_commands:
            missing_dispatch.append(video_tools_ref)
            invalid_refs.append({
                "id": command.get("id"),
                "type": "video_tools_command",
                "ref": video_tools_ref,
            })

        tier_ref = _test_tier_ref(argv)
        if video_tools_ref == "test-tiers" and tier_ref and tier_ref not in TEST_TIERS:
            missing_tiers.append(tier_ref)
            invalid_refs.append({
                "id": command.get("id"),
                "type": "test_tier",
                "ref": tier_ref,
            })

    missing_dispatch = sorted(set(missing_dispatch))
    missing_tiers = sorted(set(missing_tiers))
    return {
        "artifact_role": ARTIFACT_ROLE,
        "version": VERSION,
        "commands": commands,
        "missing_dispatch_commands": missing_dispatch,
        "missing_test_tiers": missing_tiers,
        "invalid_command_refs": invalid_refs,
        "ok": not missing_dispatch and not missing_tiers and not invalid_refs,
    }
