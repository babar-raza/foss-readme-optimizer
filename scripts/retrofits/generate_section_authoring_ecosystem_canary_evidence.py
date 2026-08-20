"""One-shot evidence generation: run the section-cluster authoring engine live against real
accepted ProductFactsV2 for the seven ecosystem canaries named in OPT-QWEN-SECTION-ENGINE /
OPT-QWEN-CANONICAL-FACT-PACKET-INTEGRATION (3D/Python, 3D/.NET, Cells/Java, Cells/C++, PDF/Go,
Cells/Rust, 3D/TypeScript).

This is authoring-layer evidence, not a complete README candidate and not a 30/30 portfolio
proof: it proves `specialists/section_cluster_authoring.py::execute_section_cluster_authoring`
against real live-called qwen3-next output for every ecosystem's already-accepted, verified
facts -- reusing the exact same canonical compact projection
(`readme/agentic_composition_inputs.py::composition_fact_payloads`) every other authoring/
reviewing caller uses, never a flattened or independently re-derived one -- and records each
outcome's deterministic acceptance-gate result (schema/disposition/protected-content/do-not-
claim -- all enforced inline by `execute_section_cluster_authoring` itself, so a returned
outcome has already passed every gate by construction).

Read-only against the product repositories: no facts pipeline, no candidate pipeline, no review
pipeline, no product-repository write. Output is tracked evidence under
plans/investigations/evidence/ (never runs/, which is gitignored disposable state).
"""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent import env
from readme_agent.evidence.writer import write_redacted_json
from readme_agent.facts.protected_content import fingerprint_protected_content
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm.section_author_client import build_live_section_cluster_author_client
from readme_agent.specialists.section_authoring_document import (
    SectionAuthoringSpecV1,
    author_readme_sections,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "section-authoring-seven-ecosystem-canaries-2026-08-20"
)

# (canary label, real accepted ProductFactsV2 tracked evidence path)
CANARY_FACT_SOURCES: tuple[tuple[str, Path], ...] = (
    (
        "3D/Python",
        REPO_ROOT
        / "plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25"
        / "aspose-3d-foss-for-python/product-facts-v2.json",
    ),
    (
        "3D/.NET",
        REPO_ROOT
        / "plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25"
        / "aspose-3d-foss-for--net/product-facts-v2.json",
    ),
    (
        "Cells/Java",
        REPO_ROOT
        / "plans/investigations/evidence/level8-local-readme-proposals-2026-07-24"
        / "cells-java/product-facts-v2.json",
    ),
    (
        "Cells/Cpp",
        REPO_ROOT
        / "plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25"
        / "aspose-cells-foss-for-cpp/product-facts-v2.json",
    ),
    (
        "PDF/Go",
        REPO_ROOT
        / "plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25"
        / "aspose-pdf-foss-for-go/product-facts-v2.json",
    ),
    (
        "Cells/Rust",
        REPO_ROOT
        / "plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25"
        / "aspose-cells-foss-for-rust/product-facts-v2.json",
    ),
    (
        "3D/TypeScript",
        REPO_ROOT
        / "plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25"
        / "aspose-3d-foss-for-typescript/product-facts-v2.json",
    ),
)

# Present, verified in every one of the seven bundles -- the uniform opening-summary cluster
# proven identically across every ecosystem, no platform branch.
_OPENING_SUMMARY_FIELDS = (
    "product.identity",
    "product.platforms",
    "installation.coordinates",
    "release.state",
)


def _load_product_facts(path: Path) -> ProductFactsV2:
    return ProductFactsV2.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _verified_selected_fact_id(product_facts: ProductFactsV2, field: str) -> str | None:
    fact_id = product_facts.selected_fact_ids.get(field)
    if fact_id is None:
        return None
    fact = product_facts.fact_by_id(fact_id)
    if (
        fact.verification_state not in {"verified", "policy_approved"}
        or fact.has_unresolved_conflict
    ):
        return None
    return fact_id


def _build_specs(product_facts: ProductFactsV2) -> list[SectionAuthoringSpecV1]:
    specs = [
        SectionAuthoringSpecV1(
            section_id="opening-summary",
            task_family="opening_summary",
            section_objective=(
                "Introduce the product, its supported platforms, and how to install it."
            ),
            accepted_fact_ids=tuple(
                fact_id
                for field in _OPENING_SUMMARY_FIELDS
                if (fact_id := _verified_selected_fact_id(product_facts, field)) is not None
            ),
        )
    ]
    capabilities_id = _verified_selected_fact_id(product_facts, "product.capabilities")
    formats_id = _verified_selected_fact_id(product_facts, "product.formats")
    limitations_id = _verified_selected_fact_id(product_facts, "product.limitations")
    if capabilities_id is not None and formats_id is not None:
        specs.append(
            SectionAuthoringSpecV1(
                section_id="capability-overview",
                task_family="capability_entry_cluster",
                section_objective="Introduce the primary supported capabilities and formats.",
                accepted_fact_ids=(capabilities_id, formats_id),
                do_not_claim_fact_ids=((limitations_id,) if limitations_id is not None else ()),
            )
        )
    return specs


def _outcome_evidence(outcome) -> dict:
    return {
        "target_section_id": outcome.target_section_id,
        "reused_from_cache": outcome.reused_from_cache,
        "units": [unit.model_dump(mode="json") for unit in outcome.result.units],
        "omitted": [item.model_dump(mode="json") for item in outcome.result.omitted],
        "acceptance_gates_passed": {
            "schema_valid": True,
            "no_unsupported_fact_id": True,
            "every_accepted_fact_disposed": True,
            "no_do_not_claim_citation": True,
            "no_authored_code_or_command": True,
        },
        "receipt": outcome.receipt.model_dump(mode="json"),
    }


def main() -> None:
    client = build_live_section_cluster_author_client(env.llm_base_url(), env.llm_api_key())
    protected_content = fingerprint_protected_content("# Example\n\nA focused library.\n")
    summary: list[dict] = []

    for label, fact_path in CANARY_FACT_SOURCES:
        if not fact_path.is_file():
            summary.append(
                {"canary": label, "status": "SKIPPED_MISSING_FACTS", "path": str(fact_path)}
            )
            print(f"[{label}] SKIPPED -- missing {fact_path}")
            continue
        product_facts = _load_product_facts(fact_path)
        specs = _build_specs(product_facts)
        source_revision = product_facts.facts[0].source.source_revision or "unknown"

        outcomes = author_readme_sections(
            org_repo=product_facts.org_repo,
            source_revision=source_revision,
            product_facts=product_facts,
            protected_content=protected_content,
            section_specs=specs,
            client=client,
        )

        canary_evidence = {
            "canary": label,
            "org_repo": product_facts.org_repo,
            "task_families_run": [spec.task_family for spec in specs],
            "sections": [_outcome_evidence(outcome) for outcome in outcomes],
        }
        canary_slug = label.replace("/", "-").lower()
        write_redacted_json(EVIDENCE_DIR / f"{canary_slug}.json", canary_evidence)
        summary.append(
            {
                "canary": label,
                "status": "PASS",
                "sections_authored": len(outcomes),
                "task_families_run": canary_evidence["task_families_run"],
                "total_logical_calls": sum(
                    outcome.receipt.logical_call_count for outcome in outcomes
                ),
            }
        )
        print(f"[{label}] PASS -- {len(outcomes)} section(s) authored")

    write_redacted_json(EVIDENCE_DIR / "SUMMARY.json", {"canaries": summary})
    print(f"\nEvidence written to {EVIDENCE_DIR}")


if __name__ == "__main__":
    main()
