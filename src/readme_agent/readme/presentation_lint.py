"""Run the complete deterministic visitor-facing README presentation lint."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.presentation_lint_models import PresentationLintResultV1
from readme_agent.readme.presentation_lint_semantics import (
    RULE_IDS as SEMANTIC_RULE_IDS,
)
from readme_agent.readme.presentation_lint_semantics import (
    lint_semantics,
)
from readme_agent.readme.presentation_lint_structure import (
    RULE_IDS as STRUCTURE_RULE_IDS,
)
from readme_agent.readme.presentation_lint_structure import (
    lint_structure,
)


def lint_readme_presentation(
    candidate_text: str,
    facts: ProductFactsV2 | None,
) -> PresentationLintResultV1:
    """Reject known visitor defects without an LLM call or product-name allowlist."""

    findings = lint_semantics(candidate_text, facts) + lint_structure(candidate_text)
    findings.sort(key=lambda finding: (finding.spans[0].start, finding.rule_id, finding.finding_id))
    rules_run = sorted({*SEMANTIC_RULE_IDS, *STRUCTURE_RULE_IDS})
    return PresentationLintResultV1(
        valid=not any(finding.severity == "critical" for finding in findings),
        rules_run=rules_run,
        findings=findings,
    )
