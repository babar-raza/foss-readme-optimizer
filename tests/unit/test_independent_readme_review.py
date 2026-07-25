"""Unit tests for the independent, adversarial README-quality reviewer
(`RPOC-022`/`RPOC-023`) -- `specialists/independent_readme_review.py`.

Every LLM call in this file is mocked (`FixtureAnalysisClient`), and every
`get_product_facts` dispatch is mocked (monkeypatching the module-level
`dispatch_tool_call` name, the same pattern `test_readme_factuality.py`
already establishes for `readme_factuality.py`). The negative-control test
below (`test_negative_control...mock`) is explicitly a MOCK -- see
`tests/integration/test_independent_readme_review_live.py` for the REAL live
counterpart against the actual `qwen3-next` model, which is the taskcard's
own "single most important test."

Fixture README text reuses the AcmeCells fictional-product scenarios
RPOC-020's own live route-characterization already proved discriminate
cleanly on this exact prompt shape (`plans/investigations/tools/
probe_independent_review_route.py`'s `CANDIDATES` dict) -- not invented
fresh here."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from readme_agent.facts.migration import migrate_product_facts_v1
from readme_agent.facts.schema import ProductFactsV1
from readme_agent.llm.analysis_client import AnalysisResult, FixtureAnalysisClient
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.specialists import independent_readme_review as reviewer
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.migrations import ensure_run_state_v2
from readme_agent.state.readme_poc_lifecycle import transition_readme_poc_status

ORG_REPO = "acme/acmecells"

# The exact two scenario READMEs RPOC-020 live-proved qwen3-next
# discriminates correctly (100% verdict-correct, see `characterization-and-
# recommendation.md`'s Results table) -- `well_grounded_specific` (expected
# ACCEPT) and `generic_template_overpromotion` (expected REJECT_REPAIRABLE).
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

_PRESENTATION_PLAN = {"executable": True, "presentation_plan": {"dimensions": []}}
_DETERMINISTIC_VALIDATION_RESULT = {"verdict": "accept", "reason": "schema/citations ok"}


def _facts_result() -> dict:
    v1 = ProductFactsV1(org_repo=ORG_REPO, family="acmecells", platform="java", ecosystem="java")
    v2 = migrate_product_facts_v1(v1, source_revision="abc123")
    return {"product_facts_v2": v2.model_dump(mode="json")}


def _mock_get_product_facts(monkeypatch, *, outcome: str = "executed") -> None:
    def dispatch(tool_call, permissions, *, caller_domain=None):
        assert tool_call["function"]["name"] == "get_product_facts"
        assert caller_domain == "independent_verification"
        if outcome != "executed":
            return SimpleNamespace(outcome=outcome, result=None, error="state unavailable")
        return SimpleNamespace(outcome="executed", result=_facts_result(), error=None)

    monkeypatch.setattr(reviewer, "dispatch_tool_call", dispatch)


def _verdict_result(parsed: dict) -> AnalysisResult:
    return AnalysisResult(parsed=parsed, meta=LLMResponseMeta())


def _accept_verdict(**overrides) -> dict:
    base = {
        "verdict": "ACCEPT",
        "reasoning": "Every claim traces to a supplied fact; specific, complete, ready to ship.",
        "failed_criteria": [],
        "sections_affected": [],
        "required_repair": "",
        "preserve": [],
    }
    base.update(overrides)
    return base


def _reject_repairable_verdict(**overrides) -> dict:
    base = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "Generic marketing language with no product specifics; nothing is false.",
        "failed_criteria": ["product_specificity", "generic_template_symptoms"],
        "sections_affected": ["intro", "Why AcmeCells?"],
        "required_repair": "Replace marketing language with concrete capabilities from the facts.",
        "preserve": [],
    }
    base.update(overrides)
    return base


def _blocked_fact_conflict_verdict(**overrides) -> dict:
    base = {
        "verdict": "BLOCKED_FACT_CONFLICT",
        "reasoning": "Candidate claims .xls/VBA/pivot-table support, directly contradicting facts.",
        "failed_criteria": ["factuality"],
        "sections_affected": ["Capabilities"],
        "required_repair": "Remove claims of .xls/VBA/pivot-table support.",
        "preserve": [],
    }
    base.update(overrides)
    return base


class FakeReviewBackend:
    """In-memory `StateBackend` -- mirrors `test_readme_poc_lifecycle.py::
    FakeReadmePocBackend` exactly, this test module's own small fake per this
    codebase's "each state-machine test module owns its own small fake"
    convention."""

    def __init__(self):
        self.states: dict = {}
        self.locked: set = set()

    def load(self, org_repo: str):
        return self.states.get(org_repo)

    def save(self, org_repo: str, state, expected_version):
        current = self.states.get(org_repo)
        current_version = current.state_version if current else None
        if current_version != expected_version:
            return SaveResult("stale", current_version)
        new_version = (current_version or 0) + 1
        self.states[org_repo] = ensure_run_state_v2(state).model_copy(
            update={"org_repo": org_repo, "state_version": new_version}
        )
        return SaveResult("saved", new_version)

    def acquire_lock(self, org_repo: str):
        if org_repo in self.locked:
            return None
        self.locked.add(org_repo)
        return Lock(org_repo, "test", "9999-01-01T00:00:00+00:00")

    def release_lock(self, lock: Lock) -> None:
        self.locked.discard(lock.org_repo)

    def lock_still_held(self, lock: Lock) -> bool:
        return lock.org_repo in self.locked

    def acquire_run_lock(self, org_repo: str):
        return self.acquire_lock(f"run:{org_repo}")

    def release_run_lock(self, lock: Lock) -> None:
        self.release_lock(lock)

    def load_model_route_status(self, job: str):
        return None

    def save_model_route_status(self, status) -> None:
        return None


def _advance_to_candidate_generated(backend: FakeReviewBackend, org_repo: str) -> None:
    for status in [
        "SNAPSHOTTED",
        "PROFILED",
        "FACTS_COLLECTING",
        "FACTS_READY",
        "README_ASSESSED",
        "PLAN_READY",
        "CANDIDATE_GENERATED",
        "DETERMINISTIC_VALIDATED",
        "AGENT_REVIEWING",
    ]:
        transition_readme_poc_status(backend, org_repo, status, observed_by="test", reason="setup")


def test_independent_repair_plan_dispatch_keeps_the_registered_domain(monkeypatch):
    import readme_agent.specialists.independent_readme_review as reviewer_module

    captured: dict = {}

    def _fake_dispatch(*args, **kwargs):
        captured.update(kwargs)
        return reviewer_module.DispatchResult(outcome="executed", result={})

    monkeypatch.setattr(reviewer_module, "dispatch_tool_call", _fake_dispatch)
    reviewer_module._dispatch_presentation_plan(
        ORG_REPO,
        {
            "original_text": "# Original",
            "source_text": "# Source",
            "final_text": "# Candidate",
            "source_revision": "a" * 40,
        },
    )

    assert captured["caller_domain"] == "readme_presentation"


class TestPositiveControlMock:
    def test_well_grounded_candidate_is_accepted(self, monkeypatch):
        _mock_get_product_facts(monkeypatch)
        client = FixtureAnalysisClient([_verdict_result(_accept_verdict())])

        review = reviewer.run_independent_readme_review(
            ORG_REPO,
            WELL_GROUNDED_README,
            WELL_GROUNDED_README,
            _PRESENTATION_PLAN,
            _DETERMINISTIC_VALIDATION_RESULT,
            client=client,
        )

        assert review.verdict == "ACCEPT"
        assert review.failed_criteria == []


class TestNegativeControlMock:
    """MOCK -- the taskcard's own "single most important test" is the LIVE
    version in `tests/integration/test_independent_readme_review_live.py`.
    This mock version is a fast, deterministic regression guard for the
    wiring (prompt fill -> client -> parse -> never-ACCEPT assertion), not a
    substitute for proving the model itself can discriminate."""

    def test_generic_template_candidate_is_never_accepted_mock(self, monkeypatch):
        _mock_get_product_facts(monkeypatch)
        client = FixtureAnalysisClient([_verdict_result(_reject_repairable_verdict())])

        review = reviewer.run_independent_readme_review(
            ORG_REPO,
            WELL_GROUNDED_README,
            GENERIC_TEMPLATE_README,
            _PRESENTATION_PLAN,
            _DETERMINISTIC_VALIDATION_RESULT,
            client=client,
        )

        assert review.verdict != "ACCEPT"
        assert review.verdict in {
            "REJECT_REPAIRABLE",
            "BLOCKED_FACT_CONFLICT",
            "BLOCKED_MISSING_EVIDENCE",
            "SYSTEM_FAILURE",
        }


class TestSystemFailureOnFactsDispatchFailure:
    def test_fact_dispatch_failure_is_a_system_failure_never_a_crash(self, monkeypatch):
        _mock_get_product_facts(monkeypatch, outcome="failed")
        # No LLM call should happen -- FixtureAnalysisClient with zero seeded
        # results raises LLMError on any .analyze() call, proving this path
        # never reaches the client.
        client = FixtureAnalysisClient([])

        review = reviewer.run_independent_readme_review(
            ORG_REPO,
            WELL_GROUNDED_README,
            WELL_GROUNDED_README,
            _PRESENTATION_PLAN,
            _DETERMINISTIC_VALIDATION_RESULT,
            client=client,
        )

        assert review.verdict == "SYSTEM_FAILURE"
        assert "get_product_facts" in review.reasoning


class TestResponseSchemaValidation:
    def test_unknown_verdict_string_raises_llm_error(self, monkeypatch):
        _mock_get_product_facts(monkeypatch)
        client = FixtureAnalysisClient(
            [_verdict_result({"verdict": "MAYBE", "reasoning": "unsure"})]
        )

        with pytest.raises(reviewer.LLMError, match="did not match"):
            reviewer.run_independent_readme_review(
                ORG_REPO,
                WELL_GROUNDED_README,
                WELL_GROUNDED_README,
                _PRESENTATION_PLAN,
                _DETERMINISTIC_VALIDATION_RESULT,
                client=client,
            )

    def test_pydantic_model_rejects_unknown_verdict_directly(self):
        with pytest.raises(ValidationError):
            reviewer.IndependentReadmeReviewResultV1.model_validate(
                {"verdict": "NOT_A_REAL_VERDICT", "reasoning": "x"}
            )


class TestRecordReviewVerdict:
    def test_accept_transitions_to_agent_approved(self):
        backend = FakeReviewBackend()
        _advance_to_candidate_generated(backend, ORG_REPO)
        review = reviewer.IndependentReadmeReviewResultV1.model_validate(_accept_verdict())

        result = reviewer.record_review_verdict(backend, ORG_REPO, review)

        assert result.status == "AGENT_APPROVED"

    def test_rejection_transitions_to_agent_review_rejected(self):
        backend = FakeReviewBackend()
        _advance_to_candidate_generated(backend, ORG_REPO)
        review = reviewer.IndependentReadmeReviewResultV1.model_validate(
            _reject_repairable_verdict()
        )

        result = reviewer.record_review_verdict(backend, ORG_REPO, review)

        assert result.status == "AGENT_REVIEW_REJECTED"
        assert result.history[-1].evidence_refs == review.failed_criteria


class TestRepairLoopBound:
    """`RPOC-023`: `REJECT_REPAIRABLE` every single time must stop after
    `MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS` regenerations and escalate --
    never loop forever, never silently drop the repo."""

    def test_persistent_rejection_stops_after_max_attempts_and_escalates(self, monkeypatch):
        backend = FakeReviewBackend()
        _advance_to_candidate_generated(backend, ORG_REPO)
        _mock_get_product_facts(monkeypatch)
        # One initial review + MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS repair
        # re-reviews, all REJECT_REPAIRABLE -- exhausts the bound.
        seeded = [
            _verdict_result(_reject_repairable_verdict())
            for _ in range(reviewer.MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS + 1)
        ]
        client = FixtureAnalysisClient(seeded)
        regenerate_calls = []

        def fake_regenerate():
            regenerate_calls.append(1)
            return {
                "original_text": WELL_GROUNDED_README,
                "final_text": GENERIC_TEMPLATE_README,
                "presentation_plan": _PRESENTATION_PLAN,
                "deterministic_validation_result": _DETERMINISTIC_VALIDATION_RESULT,
            }

        outcome = reviewer.run_independent_review_with_repair_loop(
            ORG_REPO,
            backend,
            {
                "original_text": WELL_GROUNDED_README,
                "final_text": GENERIC_TEMPLATE_README,
                "presentation_plan": _PRESENTATION_PLAN,
                "deterministic_validation_result": _DETERMINISTIC_VALIDATION_RESULT,
            },
            client=client,
            regenerate_context=fake_regenerate,
        )

        assert outcome.outcome_kind == "repair_exhausted"
        assert outcome.attempts == reviewer.MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS
        assert len(regenerate_calls) == reviewer.MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS
        assert outcome.escalation is not None
        assert outcome.escalation["repository"] == ORG_REPO
        assert outcome.escalation["actionable"] is True
        assert (
            outcome.escalation["repair_attempts"] == reviewer.MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS
        )

        # Final durable status clearly reflects "still rejected after N
        # attempts" -- distinguishable from a repo that was never reviewed
        # (which would still read DISCOVERED) and from a first-pass reject
        # (whose reason would say "review pass 1", not the exhausted count).
        final_state = backend.load(ORG_REPO).readme_poc_lifecycle
        assert final_state.status == "AGENT_REVIEW_REJECTED"
        assert f"review pass {reviewer.MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS + 1}" in (
            final_state.history[-1].reason
        )

    def test_eventual_accept_within_bound_stops_the_loop_early(self, monkeypatch):
        backend = FakeReviewBackend()
        _advance_to_candidate_generated(backend, ORG_REPO)
        _mock_get_product_facts(monkeypatch)
        client = FixtureAnalysisClient(
            [
                _verdict_result(_reject_repairable_verdict()),
                _verdict_result(_accept_verdict()),
            ]
        )
        regenerate_calls = []

        def fake_regenerate():
            regenerate_calls.append(1)
            return {
                "original_text": WELL_GROUNDED_README,
                "final_text": WELL_GROUNDED_README,
                "presentation_plan": _PRESENTATION_PLAN,
                "deterministic_validation_result": _DETERMINISTIC_VALIDATION_RESULT,
            }

        outcome = reviewer.run_independent_review_with_repair_loop(
            ORG_REPO,
            backend,
            {
                "original_text": WELL_GROUNDED_README,
                "final_text": GENERIC_TEMPLATE_README,
                "presentation_plan": _PRESENTATION_PLAN,
                "deterministic_validation_result": _DETERMINISTIC_VALIDATION_RESULT,
            },
            client=client,
            regenerate_context=fake_regenerate,
        )

        assert outcome.outcome_kind == "accepted"
        assert outcome.attempts == 1
        assert len(regenerate_calls) == 1
        assert backend.load(ORG_REPO).readme_poc_lifecycle.status == "AGENT_APPROVED"


class TestBlockedVerdictNeverEntersRepairLoop:
    """`BLOCKED_FACT_CONFLICT`/`BLOCKED_MISSING_EVIDENCE`/`SYSTEM_FAILURE`
    need new evidence, not a reworded README -- the repair loop must never
    attempt a regeneration for any of them, structurally, not just by
    convention."""

    @pytest.mark.parametrize(
        ("verdict_dict", "expected_status"),
        [
            (_blocked_fact_conflict_verdict(), "BLOCKED_FACT_CONFLICT"),
            (
                {
                    "verdict": "BLOCKED_MISSING_EVIDENCE",
                    "reasoning": "Claims 50,000 rows/sec with no supporting fact.",
                    "failed_criteria": ["factuality"],
                    "sections_affected": ["intro"],
                    "required_repair": "Remove the unverifiable performance claim.",
                    "preserve": [],
                },
                "BLOCKED_MISSING_EVIDENCE",
            ),
            (
                {
                    "verdict": "SYSTEM_FAILURE",
                    "reasoning": "Candidate text was empty.",
                    "failed_criteria": [],
                    "sections_affected": [],
                    "required_repair": "",
                    "preserve": [],
                },
                "SYSTEM_FAILURE",
            ),
        ],
    )
    def test_blocked_verdict_stops_immediately_without_regenerating(
        self, verdict_dict, expected_status, monkeypatch
    ):
        backend = FakeReviewBackend()
        _advance_to_candidate_generated(backend, ORG_REPO)
        _mock_get_product_facts(monkeypatch)
        client = FixtureAnalysisClient([_verdict_result(verdict_dict)])
        regenerate_calls = []

        def fake_regenerate():
            regenerate_calls.append(1)
            raise AssertionError("regenerate_context must never be called for a blocked verdict")

        outcome = reviewer.run_independent_review_with_repair_loop(
            ORG_REPO,
            backend,
            {
                "original_text": WELL_GROUNDED_README,
                "final_text": GENERIC_TEMPLATE_README,
                "presentation_plan": _PRESENTATION_PLAN,
                "deterministic_validation_result": _DETERMINISTIC_VALIDATION_RESULT,
            },
            client=client,
            regenerate_context=fake_regenerate,
        )

        assert outcome.outcome_kind == "blocked"
        assert outcome.attempts == 0
        assert regenerate_calls == []
        assert outcome.escalation is None

        final_state = backend.load(ORG_REPO).readme_poc_lifecycle
        # A factual/system block retains its distinct first failing boundary
        # and never proceeds into REPAIRING.
        assert final_state.status == expected_status
        assert "blocked" in final_state.history[-1].reason
