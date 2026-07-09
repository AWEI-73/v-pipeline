"""Lightweight docs/reference hygiene checks for route facts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


REFERENCE_SURFACES = [
    "docs/INDEX.md",
    "docs/branch-contract-registry.md",
    "docs/branch-contract-registry.json",
    "docs/pipeline-decision-tree.md",
    "docs/video-pipeline-operating-map.md",
    "docs/reference-repos-map.md",
]

EXEMPT_ROOT_DOCS = {
    "docs/build-capability-alignment.md": "historical_or_design_note",
    "docs/capcut-pipeline-integration-design.md": "reference_only_backend_design",
    "docs/dashboard-node-skill-output-spec.md": "reference_only_dashboard_design",
    "docs/windows-native-migration-spec.md": "historical_migration_record",
}


def _normalize_doc(rel: str | Path) -> str:
    return str(rel).replace("\\", "/")


def evaluate_doc_reference_hygiene(
    *,
    repo_root: str | Path,
    root_docs: Iterable[str | Path],
    reference_texts: Iterable[str],
    exemptions: Iterable[str | Path] | dict[str, str],
) -> dict[str, object]:
    refs = "\n".join(reference_texts)
    exempt_map = (
        {_normalize_doc(key): value for key, value in exemptions.items()}
        if isinstance(exemptions, dict)
        else {_normalize_doc(item): "explicit_exemption" for item in exemptions}
    )
    referenced: list[str] = []
    exempted: list[dict[str, str]] = []
    orphan: list[str] = []

    for doc in sorted({_normalize_doc(item) for item in root_docs}):
        if doc == "docs/INDEX.md":
            referenced.append(doc)
            continue
        if doc in exempt_map:
            exempted.append({"path": doc, "classification": str(exempt_map[doc])})
            continue
        basename = Path(doc).name
        if doc in refs or basename in refs:
            referenced.append(doc)
            continue
        orphan.append(doc)

    return {
        "artifact_role": "doc_reference_hygiene_report",
        "version": 1,
        "ok": not orphan,
        "classified_count": len(referenced) + len(exempted) + len(orphan),
        "referenced_docs": referenced,
        "exempted_docs": exempted,
        "orphan_canonical_docs": orphan,
    }


def evaluate_current_doc_reference_hygiene(repo_root: str | Path) -> dict[str, object]:
    root = Path(repo_root)
    root_docs = [f"docs/{path.name}" for path in (root / "docs").glob("*.md")]
    reference_texts = [
        (root / rel).read_text(encoding="utf-8")
        for rel in REFERENCE_SURFACES
        if (root / rel).exists()
    ]
    return evaluate_doc_reference_hygiene(
        repo_root=root,
        root_docs=root_docs,
        reference_texts=reference_texts,
        exemptions=EXEMPT_ROOT_DOCS,
    )


def write_doc_reference_hygiene_report(repo_root: str | Path, out: str | Path) -> dict[str, object]:
    report = evaluate_current_doc_reference_hygiene(repo_root)
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
