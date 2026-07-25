"""Live proof against the real LLM gateway -- real network, real secrets --
for the independent, adversarial README-quality reviewer (`RPOC-022`).

This is the taskcard's own "single most important test": proving the real
routed model (`env.py::JOB_MODEL_ROUTING["independent_readme_review"]` ->
`qwen3-next`) can actually tell a well-grounded, product-specific README
apart from a generic, templated, marketing-fluff one against the REAL
`prompts/verification/independent_readme_review.yaml` prompt -- not a mock
standing in for the exact thing being proven.

Exercises the prompt-fill -> `LiveAnalysisClient` -> schema-validate chain
directly (mirrors `test_llm_live.py`'s own pattern of calling the client
against a hand-built prompt rather than the full org_repo/registry-dispatch
pipeline) -- the AcmeCells fixtures are fictional and not listed in
`data/products.json`, so `specialists/independent_readme_review.py::
run_independent_readme_review()`'s own `get_product_facts` dispatch would
reject them; that dispatch step is already covered by the mocked unit tests
in `tests/unit/test_independent_readme_review.py`. What this file proves
instead, for real, is the one thing no mock can prove: whether the routed
model itself discriminates correctly against this exact prompt.

Fixture README text and grounding facts are the same AcmeCells fictional
product `plans/investigations/tools/probe_independent_review_route.py`
(`RPOC-020`) already live-proved qwen3-next discriminates correctly on --
not invented fresh here."""

import json

import pytest

from readme_agent import env
from readme_agent.llm.analysis_client import LiveAnalysisClient
from readme_agent.llm.verification_prompts import build_independent_readme_review_messages
from readme_agent.specialists.independent_readme_review import IndependentReadmeReviewResultV1

ORG_REPO = "acmesoft/acmecells"

# Same grounding-fact shape RPOC-020's probe used (GROUNDING_FACTS), reused
# verbatim in spirit -- a JSON payload standing in for ProductFactsV2 in this
# prompt-level test (see module docstring for why the full ProductFactsV2
# dispatch path is not exercised here).
GROUNDING_FACTS_JSON = json.dumps(
    {
        "product_name": "AcmeCells",
        "language": "Java",
        "audience": "Java backend developers who need to generate or edit Excel-compatible "
        "spreadsheets without depending on Microsoft Office being installed on the server",
        "capabilities": [
            "Read and write .xlsx workbooks",
            "Apply cell styles, number formats, and conditional formatting",
            "Evaluate a subset of built-in Excel formulas (SUM, AVERAGE, VLOOKUP, IF -- 40 "
            "total, listed in docs/formulas.md)",
        ],
        "formats_supported": ["xlsx"],
        "formats_explicitly_not_supported": ["xls (legacy binary format)", "ods"],
        "limitations": [
            "No support for VBA macros",
            "No support for pivot tables",
            "Formula evaluation is limited to the 40 functions listed in docs/formulas.md -- "
            "unlisted functions are preserved as text but not recalculated",
        ],
        "installation": {
            "method": "Maven Central",
            "verified_acquisition": True,
            "coordinates": "com.acmesoft:acme-cells:3.2.0",
        },
        "license": "Apache-2.0",
        "minimal_example_verified": True,
    },
    indent=2,
)

WELL_GROUNDED_README = (
    "# AcmeCells\n\n"
    "AcmeCells is a Java library for reading and writing `.xlsx` workbooks on the JVM, "
    "for backend developers who need spreadsheet generation without Microsoft Office "
    "installed on the server.\n\n"
    "## Capabilities\n"
    "- Read and write `.xlsx` workbooks\n"
    "- Apply cell styles, number formats, and conditional formatting\n"
    "- Evaluate 40 built-in Excel formulas (SUM, AVERAGE, VLOOKUP, IF, and 36 others -- "
    "full list in `docs/formulas.md`); functions outside this list are preserved as text, "
    "not recalculated\n\n"
    "## Not supported\n"
    "- Legacy `.xls` binary format, or `.ods`\n"
    "- VBA macros\n"
    "- Pivot tables\n\n"
    "## Install (Maven Central)\n"
    "```xml\n<dependency>\n  <groupId>com.acmesoft</groupId>\n"
    "  <artifactId>acme-cells</artifactId>\n  <version>3.2.0</version>\n</dependency>\n"
    "```\n\n"
    "## Minimal example\n"
    "A 12-line example that creates a workbook, writes 3 cells, applies a currency "
    "number format, and saves to disk is in `examples/Minimal.java`.\n\n"
    "## License\nApache-2.0\n"
)

# Deliberately templated: marketing fluff, zero product specifics, nothing
# actually FALSE against the grounding facts above (a real "generic template
# overwrite" -- the codebase's own audit language for this exact failure
# mode, see plans/investigations RPOC-020 characterization). Expected verdict
# is REJECT_REPAIRABLE, not BLOCKED_*, precisely because nothing here
# contradicts a fact -- it just says nothing real.
GENERIC_TEMPLATE_README = (
    "# AcmeCells\n\n"
    "AcmeCells is a next-generation, enterprise-grade, blazing-fast spreadsheet solution "
    "trusted by developers worldwide. Effortlessly handle any spreadsheet workflow with "
    "zero configuration and maximum flexibility.\n\n"
    "## Why AcmeCells?\n"
    "- Lightning-fast performance\n"
    "- Rock-solid reliability\n"
    "- Seamless integration with your existing stack\n"
    "- Loved by developers everywhere\n\n"
    "## Getting started\n"
    "Install the package for your platform and follow the quick-start guide to get up "
    "and running in seconds.\n\n"
    "## Support\n"
    "Join our community for help and best practices.\n"
)

_PRESENTATION_PLAN_JSON = json.dumps(
    {"executable": True, "note": "live-test fixture, not a real plan"}
)
_DETERMINISTIC_VALIDATION_RESULT_JSON = json.dumps(
    {"verdict": "accept", "reason": "live-test fixture -- schema/structural checks only"}
)


def _review(candidate_text: str) -> IndependentReadmeReviewResultV1:
    client = LiveAnalysisClient(
        env.llm_base_url(), env.llm_api_key(), env.llm_model_for_job("independent_readme_review")
    )
    messages = build_independent_readme_review_messages(
        ORG_REPO,
        WELL_GROUNDED_README,
        candidate_text,
        GROUNDING_FACTS_JSON,
        _PRESENTATION_PLAN_JSON,
        _DETERMINISTIC_VALIDATION_RESULT_JSON,
    )
    result = client.analyze(messages)
    return IndependentReadmeReviewResultV1.model_validate(result.parsed)


@pytest.mark.live
def test_live_positive_control_well_grounded_readme_is_accepted():
    review = _review(WELL_GROUNDED_README)

    assert review.verdict == "ACCEPT", (
        f"expected ACCEPT for a fully fact-grounded README, got {review.verdict}: "
        f"{review.reasoning}"
    )


@pytest.mark.live
def test_live_negative_control_generic_template_is_never_accepted():
    """The taskcard's own "single most important test in this whole
    taskcard": a deliberately generic, templated, product-specificity-free
    candidate must NEVER be accepted by the real routed model. A false
    ACCEPT here would mean the reviewer rubber-stamps exactly the failure
    mode it exists to catch."""
    review = _review(GENERIC_TEMPLATE_README)

    assert review.verdict != "ACCEPT", (
        "independent reviewer ACCEPTed a generic, templated, product-specificity-free "
        f"README -- this must never happen. reasoning={review.reasoning!r}"
    )
    assert review.verdict in {
        "REJECT_REPAIRABLE",
        "BLOCKED_FACT_CONFLICT",
        "BLOCKED_MISSING_EVIDENCE",
        "SYSTEM_FAILURE",
    }
    # A quality rejection (the expected outcome here -- nothing in the
    # candidate is actually FALSE, it is just generic) must be actionable:
    # failed_criteria non-empty, required_repair non-empty.
    if review.verdict == "REJECT_REPAIRABLE":
        assert review.failed_criteria, "REJECT_REPAIRABLE must name at least one failed criterion"
        assert review.required_repair, "REJECT_REPAIRABLE must state what repair is required"
