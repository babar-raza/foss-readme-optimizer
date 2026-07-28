"""Runtime wiring for context-isolated README reviewer roles."""

from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.llm.verification_prompts import separated_reviewer_standard_hash
from readme_agent.specialists.separated_readme_review import run_separated_readme_review

ORG_REPO = "example/example-foss"
ORIGINAL = "# Example\n\nOriginal material.\n"
CANDIDATE = "# Example\n\nSpecific, useful candidate.\n"
FACTS = {
    "schema_version": 2,
    "selected_fact_ids": {"product.identity": "fact-1"},
    "facts": [
        {
            "fact_id": "fact-1",
            "field": "product.identity",
            "value": "Example",
            "verification_state": "verified",
            "source": {"location": "README.md"},
            "conflicts": [],
        }
    ],
}
PLAN = {"operations": [{"operation_id": "readme.overview", "operation": "replace"}]}


class CapturingClient:
    def __init__(self, parsed):
        self.parsed = parsed
        self.messages = None

    def analyze(self, messages):
        self.messages = messages
        return AnalysisResult(parsed=self.parsed, meta=LLMResponseMeta())


class SequenceClient(CapturingClient):
    def __init__(self, parsed_items):
        self.parsed_items = parsed_items
        self.messages_seen = []

    def analyze(self, messages):
        self.messages_seen.append(messages)
        return AnalysisResult(
            parsed=self.parsed_items[len(self.messages_seen) - 1],
            meta=LLMResponseMeta(),
        )


def _accept(reason):
    return {
        "verdict": "ACCEPT",
        "reasoning": reason,
        "failed_criteria": [],
        "sections_affected": [],
        "required_repair": "",
        "findings": [],
    }


def test_two_accepts_produce_hash_bound_separate_records():
    blind = CapturingClient(_accept("visitor-ready"))
    factual = CapturingClient(_accept("facts and plan agree"))

    result = run_separated_readme_review(
        ORG_REPO,
        ORIGINAL,
        CANDIDATE,
        PLAN,
        FACTS,
        blind_client=blind,
        factual_client=factual,
    )

    assert result.verdict == "ACCEPT"
    assert result.combined_review.identity_separation_valid
    assert result.blind_quality_review.input_sha256 != result.factual_plan_review.input_sha256
    assert result.blind_quality_review.identity.prompt_id == "blind_readme_quality_review"
    assert result.factual_plan_review.identity.prompt_id == "factual_readme_plan_review"
    assert result.blind_quality_review.findings == []
    assert result.factual_plan_review.findings == []

    blind_context = "\n".join(message["content"] for message in blind.messages)
    factual_context = "\n".join(message["content"] for message in factual.messages)
    assert ORIGINAL in blind_context
    assert "fact-1" not in blind_context
    assert "readme.overview" not in blind_context
    assert ORIGINAL not in factual_context
    assert "fact-1" in factual_context
    assert "readme.overview" in factual_context


def test_blind_rejection_vetoes_factual_acceptance():
    result = run_separated_readme_review(
        ORG_REPO,
        ORIGINAL,
        CANDIDATE,
        PLAN,
        FACTS,
        blind_client=CapturingClient(
            {
                "verdict": "REJECT_REPAIRABLE",
                "reasoning": "The opening is generic.",
                "failed_criteria": ["product_specificity"],
                "sections_affected": ["overview"],
                "required_repair": "Name the concrete purpose.",
                "findings": [
                    {
                        "finding_id": "quality.generic-opening",
                        "kind": "quality",
                        "criterion": "product_specificity",
                        "section": "overview",
                        "claim": "The opening is generic.",
                        "quoted_candidate_span": "Specific, useful candidate.",
                        "fact_id": None,
                        "evidence_excerpt": None,
                        "expected_polarity": None,
                        "observed_polarity": None,
                        "polarity_result": "not_applicable",
                        "required_repair": "Name the concrete purpose.",
                    }
                ],
            }
        ),
        factual_client=CapturingClient(_accept("facts and plan agree")),
    )

    assert result.verdict == "REJECT_REPAIRABLE"
    assert result.failed_criteria == ["product_specificity"]
    assert result.required_repair == (
        "Revise overview for product_specificity around exact span: Specific, useful candidate."
    )
    assert result.blind_quality_review.findings[0].finding_id == "quality.generic-opening"
    assert "Name the concrete purpose." not in result.required_repair
    assert "product_specificity" in result.required_repair


def test_factual_conflict_vetoes_blind_acceptance():
    result = run_separated_readme_review(
        ORG_REPO,
        ORIGINAL,
        CANDIDATE,
        PLAN,
        FACTS,
        blind_client=CapturingClient(_accept("visitor-ready")),
        factual_client=CapturingClient(
            {
                "verdict": "BLOCKED_FACT_CONFLICT",
                "reasoning": "The acquisition claim contradicts fact-1.",
                "failed_criteria": ["factuality"],
                "sections_affected": ["installation"],
                "required_repair": "",
                "findings": [
                    {
                        "finding_id": "factual.unsupported-installation",
                        "kind": "factual",
                        "criterion": "factuality",
                        "section": "installation",
                        "claim": "The candidate makes an unsupported acquisition claim.",
                        "quoted_candidate_span": "Specific, useful candidate.",
                        "fact_id": "fact-1",
                        "evidence_excerpt": "Example",
                        "expected_polarity": None,
                        "observed_polarity": None,
                        "polarity_result": "contradicts",
                        "required_repair": "",
                    }
                ],
            }
        ),
    )

    assert result.verdict == "BLOCKED_FACT_CONFLICT"
    assert result.combined_review.verdict == "BLOCKED_FACT_CONFLICT"


def test_reviewer_standard_binds_both_role_prompts_not_legacy_prompt():
    from readme_agent.llm import prompt_registry

    standard = separated_reviewer_standard_hash()

    assert len(standard) == 64
    assert standard != prompt_registry.prompt_hash("independent_readme_review")


def test_ungrounded_quality_premise_gets_one_bounded_correction_turn():
    invalid = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The opening is generic.",
        "failed_criteria": ["product_specificity"],
        "sections_affected": ["overview"],
        "required_repair": "Name the purpose.",
        "findings": [
            {
                "finding_id": "quality.generic-opening",
                "kind": "quality",
                "criterion": "product_specificity",
                "section": "overview",
                "claim": "The opening is generic.",
                "quoted_candidate_span": "text that is not in the candidate",
                "fact_id": None,
                "evidence_excerpt": None,
                "expected_polarity": None,
                "observed_polarity": None,
                "polarity_result": "not_applicable",
                "required_repair": "Name the purpose.",
            }
        ],
    }
    corrected = {
        **invalid,
        "findings": [
            {
                **invalid["findings"][0],
                "quoted_candidate_span": "Specific, useful candidate.",
            }
        ],
    }
    blind = SequenceClient([invalid, corrected])

    result = run_separated_readme_review(
        ORG_REPO,
        ORIGINAL,
        CANDIDATE,
        PLAN,
        FACTS,
        blind_client=blind,
        factual_client=CapturingClient(_accept("facts and plan agree")),
    )

    assert result.verdict == "REJECT_REPAIRABLE"
    assert len(blind.messages_seen) == 2
    assert result.grounding_retry_history[0]["valid"] is False
    assert result.grounding_retry_history[1]["valid"] is True
    assert "validation_errors" in blind.messages_seen[1][-1]["content"]
