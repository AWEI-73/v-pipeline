import json
from pathlib import Path
from typing import Any, Dict, List, Optional


VALID_TARGET_BRANCHES = {
    "main-pipeline",
    "material-map",
    "soundtrack-arranger",
    "subtitle-voiceover",
    "effect-factory",
    "workbench-brownfield",
    "verify-delivery",
}

VALID_PROBLEM_TYPES = {
    "contract",
    "parameter",
    "material",
    "audio",
    "subtitle",
    "voiceover",
    "effect",
    "provider",
    "user_intent_unclear",
    "multi_branch",
}

VALID_SEVERITIES = {"blocking", "revise", "warning"}
VALID_ACTIONS = {"patch_contract", "rerun_branch", "ask_user", "route_back", "stop"}


class RevisionTarget:
    def __init__(self, artifact: str, field: str, issue: str, suggested_change: str):
        self.artifact = artifact
        self.field = field
        self.issue = issue
        self.suggested_change = suggested_change

    def to_dict(self) -> Dict[str, str]:
        return {
            "artifact": self.artifact,
            "field": self.field,
            "issue": self.issue,
            "suggested_change": self.suggested_change
        }


class RevisionPacket:
    """
    Agentic Revision Packet Schema for self-correction loops.
    Guides the agent on what failed, why, and how to repair it.
    """
    def __init__(
        self,
        source_review: str,
        target_branch: str,
        problem_type: str,
        severity: str,
        revision_targets: List[Dict[str, str]],
        allowed_actions: Optional[List[str]] = None,
        forbidden_actions: Optional[List[str]] = None,
        rerun_policy: Optional[Dict[str, Any]] = None,
    ):
        self._validate(
            target_branch=target_branch,
            problem_type=problem_type,
            severity=severity,
            revision_targets=revision_targets,
            allowed_actions=allowed_actions,
            forbidden_actions=forbidden_actions,
            rerun_policy=rerun_policy,
        )
        self.artifact_role = "revision_packet"
        self.source_review = source_review
        self.target_branch = target_branch
        self.problem_type = problem_type
        self.severity = severity
        self.revision_targets = revision_targets
        self.allowed_actions = allowed_actions or ["patch_contract", "rerun_branch", "ask_user", "route_back", "stop"]
        self.forbidden_actions = forbidden_actions or ["overwrite_final_mp4", "mutate_material_truth", "silently_downgrade_required_feature"]
        self.rerun_policy = rerun_policy or {
            "allowed": True,
            "max_attempts": 1,
            "requires_agent_decision": True
        }
        self.next_action = "agent_decide_repair"

    @staticmethod
    def _validate(
        *,
        target_branch: str,
        problem_type: str,
        severity: str,
        revision_targets: List[Dict[str, str]],
        allowed_actions: Optional[List[str]],
        forbidden_actions: Optional[List[str]],
        rerun_policy: Optional[Dict[str, Any]],
    ) -> None:
        if target_branch not in VALID_TARGET_BRANCHES:
            raise ValueError(f"invalid target_branch: {target_branch}")
        if problem_type not in VALID_PROBLEM_TYPES:
            raise ValueError(f"invalid problem_type: {problem_type}")
        if severity not in VALID_SEVERITIES:
            raise ValueError(f"invalid severity: {severity}")
        if not isinstance(revision_targets, list) or not revision_targets:
            raise ValueError("revision_targets must be a non-empty list")
        required_target_fields = {"artifact", "field", "issue", "suggested_change"}
        for index, target in enumerate(revision_targets):
            if not isinstance(target, dict):
                raise ValueError(f"revision_targets[{index}] must be an object")
            missing = [field for field in required_target_fields if not str(target.get(field) or "").strip()]
            if missing:
                raise ValueError(f"revision_targets[{index}] missing required fields: {', '.join(missing)}")
            target_branch_override = target.get("target_branch")
            if target_branch_override and target_branch_override not in VALID_TARGET_BRANCHES:
                raise ValueError(f"revision_targets[{index}] has invalid target_branch: {target_branch_override}")
        if allowed_actions is not None:
            if not allowed_actions:
                raise ValueError("allowed_actions must not be empty")
            unknown_actions = [action for action in allowed_actions if action not in VALID_ACTIONS]
            if unknown_actions:
                raise ValueError(f"unknown allowed_actions: {', '.join(unknown_actions)}")
        if forbidden_actions is not None and not all(str(action).strip() for action in forbidden_actions):
            raise ValueError("forbidden_actions must contain non-empty strings")
        if rerun_policy is not None:
            if not isinstance(rerun_policy.get("allowed"), bool):
                raise ValueError("rerun_policy.allowed must be a boolean")
            max_attempts = rerun_policy.get("max_attempts")
            if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 0 or max_attempts > 3:
                raise ValueError("rerun_policy.max_attempts must be an integer from 0 to 3")
            if rerun_policy.get("requires_agent_decision") is not True:
                raise ValueError("rerun_policy.requires_agent_decision must be true")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_role": self.artifact_role,
            "source_review": self.source_review,
            "target_branch": self.target_branch,
            "problem_type": self.problem_type,
            "severity": self.severity,
            "revision_targets": self.revision_targets,
            "allowed_actions": self.allowed_actions,
            "forbidden_actions": self.forbidden_actions,
            "rerun_policy": self.rerun_policy,
            "next_action": self.next_action
        }

    def save(self, path: Path) -> None:
        payload = self.to_dict()
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "RevisionPacket":
        if not path.exists():
            raise FileNotFoundError(f"Revision packet file not found at {path}")
        
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in revision packet: {e}")

        required = ("source_review", "target_branch", "problem_type", "severity", "revision_targets")
        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field '{field}' in revision packet.")

        return cls(
            source_review=str(data["source_review"]),
            target_branch=str(data["target_branch"]),
            problem_type=str(data["problem_type"]),
            severity=str(data["severity"]),
            revision_targets=list(data["revision_targets"]),
            allowed_actions=data.get("allowed_actions"),
            forbidden_actions=data.get("forbidden_actions"),
            rerun_policy=data.get("rerun_policy")
        )
