"""Unit tests for `capabilities/draft_product_truth.py`'s own pure
orchestration function (`orchestrate_product_truth_draft()`) -- the
draft -> gate -> bounded-repair cycle described by `RPOC-033`.

Every test drives `orchestrate_product_truth_draft()` directly against a
real temp-directory repository root and a real `ProductFactsV2`, with a
fake `draft_fn`/`verify_example_fn` standing in for the live LLM call and
the real disposable build -- but `capabilities/formats`, `limitations`,
and `audience/problems_solved` are routed through the real
`evidence_fact_candidate()`, `limitation_fact_candidate()`, and
`groundedness_fact_candidate()` gates, never a mock. The focused tests also
prove that positive API evidence cannot be misclassified as a limitation.

`tests/unit/test_agentic_drafting.py` covers `facts/agentic_drafting.py`
itself (the bounded-context selector, the citable-facts filter, and
`draft_product_truth()`'s own LLM-call wiring against a `FixtureAnalysisClient`).
The single real live dry-run proof (the taskcard's own most important
verification) lives outside the automated test suite, run once against
`aspose-cells-foss/Aspose.Cells-FOSS-for-Java`."""

from __future__ import annotations

from pathlib import Path

import pytest

from readme_agent.capabilities import draft_product_truth as capability
from readme_agent.facts.agentic_drafting import DraftProductTruthV1
from readme_agent.facts.example_execution import ExampleExecutionResultV1
from readme_agent.facts.interpretive_evidence import InterpretiveClaimV1
from readme_agent.facts.isolated_execution_schema import (
    ContainerCleanupV1,
    ContainerImageIdentityV1,
    IsolatedExecutionPolicyV1,
    IsolatedExecutionResultV1,
)
from readme_agent.facts.local_verification import LocalProductVerificationV1
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.registry.models import EvidenceBackedProductFact, MinimalExamplePolicy

ORG_REPO = "acme/widget"


def _source() -> FactSourceV2:
    return FactSourceV2(
        source_type="mechanical_repository",
        location="repository://acme/widget",
        source_revision="abc1234",
    )


def _established_fact(field_name: str, value, qualifier: str = "established") -> FactRecordV2:
    return FactRecordV2(
        fact_id=descriptive_fact_id(field_name, qualifier),
        field=field_name,
        value=value,
        source=_source(),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme.opening"],
    )


_IDENTITY = _established_fact(
    "product.identity",
    {
        "family": "widget",
        "platform": "java",
        "ecosystem": "java",
        "summary": "Widget is a backend library for Java developers to read and write XLSX files.",
    },
    "identity",
)


def _facts_so_far() -> ProductFactsV2:
    records = [_IDENTITY]
    seen = {fact.field for fact in records}
    for field_name in REQUIRED_PRODUCT_FIELDS:
        if field_name in seen:
            continue
        records.append(
            FactRecordV2(
                fact_id=descriptive_fact_id(field_name, "missing"),
                field=field_name,
                value=None,
                source=_source(),
                verification_state="missing",
                authoritative_owner="repository-owner",
                confidence=0.0,
                affected_surfaces=["readme"],
            )
        )
    selected = {}
    for fact in records:
        selected.setdefault(fact.field, fact.fact_id)
    return ProductFactsV2(org_repo=ORG_REPO, facts=records, selected_fact_ids=selected)


def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "Widget.java").write_text("public class Widget {}", encoding="utf-8")
    (tmp_path / "src" / "Format.java").write_text(
        'public final class Format {\n    public static final String XLSX = "xlsx";\n}\n',
        encoding="utf-8",
    )
    return tmp_path


def _good_draft() -> DraftProductTruthV1:
    return DraftProductTruthV1(
        audience=[
            InterpretiveClaimV1(
                claim_id="audience-1",
                text="Developers using Java.",
                supporting_fact_ids=[_IDENTITY.fact_id],
            )
        ],
        problems_solved=[
            InterpretiveClaimV1(
                claim_id="problem-1",
                text="Read and write XLSX files with a backend Java library.",
                supporting_fact_ids=[_IDENTITY.fact_id],
            )
        ],
        capabilities=[
            EvidenceBackedProductFact(
                value="Create and process Widget objects.",
                evidence_paths=["src/Widget.java"],
                required_symbols=["public class Widget"],
            )
        ],
        formats=[
            EvidenceBackedProductFact(
                value="Read and write XLSX files.",
                evidence_paths=["src/Format.java"],
                required_symbols=["XLSX"],
            )
        ],
        limitations=[],
        minimal_example=MinimalExamplePolicy(
            language="java",
            class_name="ReadmeExample",
            code="public class ReadmeExample {}",
            evidence_paths=["src/Widget.java"],
            required_symbols=["public class Widget"],
        ),
    )


def _draft_with_bad_capabilities_evidence() -> DraftProductTruthV1:
    draft = _good_draft()
    return draft.model_copy(
        update={
            "capabilities": [
                EvidenceBackedProductFact(
                    value="Create and process Widget objects.",
                    evidence_paths=["src/DoesNotExist.java"],
                    required_symbols=["public class Widget"],
                )
            ]
        }
    )


def _verified_local_result() -> LocalProductVerificationV1:
    ok = ExampleExecutionResultV1(
        argv=["mvn"], return_code=0, stdout="", stderr="", timed_out=False, environment_names=[]
    )
    image = "alpine@sha256:14358309a308569c32bdc37e2e0e9694be33a9d99e68afb0f5ff33cc1f695dce"
    isolated = IsolatedExecutionResultV1(
        truth_eligible=True,
        org_repo=ORG_REPO,
        source_revision="abc1234",
        argv=["mvn"],
        environment_names=[],
        input_sha256="a" * 64,
        input_file_count=1,
        policy_sha256="b" * 64,
        policy=IsolatedExecutionPolicyV1(immutable_image=image),
        image=ContainerImageIdentityV1(
            requested_reference=image,
            repo_digest=image,
            image_id="sha256:" + "c" * 64,
            operating_system="linux",
            architecture="amd64",
            engine_version="test",
        ),
        container_id="container",
        process_inventory=["PID PPID USER COMMAND"],
        return_code=0,
        stdout="",
        stderr="",
        timed_out=False,
        oom_killed=False,
        started_at="2026-07-26T00:00:00+00:00",
        finished_at="2026-07-26T00:00:01+00:00",
        cleanup=ContainerCleanupV1(
            execution_container_removed=True,
            seed_container_removed=True,
            workspace_volume_removed=True,
        ),
    )
    return LocalProductVerificationV1(
        org_repo=ORG_REPO,
        source_revision="abc1234",
        ecosystem="java",
        outcome="SOURCE_BUILD_VERIFIED",
        detail="source build and exact README example compilation passed",
        build=ok,
        example_compile=ok,
        isolated_execution=isolated,
        truth_eligible=True,
    )


def _always_verified_example(_example) -> LocalProductVerificationV1:
    return _verified_local_result()


class TestAllFieldsPass:
    def test_first_attempt_passes_every_gate_with_zero_repairs(self, tmp_path):
        root = _make_repo(tmp_path)
        facts_so_far = _facts_so_far()
        calls: list[tuple] = []

        def draft_fn(hints, current_facts):
            calls.append((hints, current_facts))
            return _good_draft()

        result = capability.orchestrate_product_truth_draft(
            ORG_REPO,
            facts_so_far,
            root,
            "abc1234",
            "2026-07-25T00:00:00+00:00",
            draft_fn=draft_fn,
            verify_example_fn=_always_verified_example,
        )

        assert result.repair_attempts == 0
        assert result.findings == []
        assert len(calls) == 1
        assert calls[0][0] is None
        for field_name in capability._GATED_FIELDS:
            assert result.gated_facts[field_name].verification_state == "verified", field_name
        example_value = result.gated_facts["example.minimal"].value
        assert example_value["verified_public_symbols"] == []
        assert example_value["rust_package"] is None
        assert example_value["rust_formats"] == []

        # Real evidence_fact_candidate()/groundedness_fact_candidate() reuse,
        # not a reimplementation -- confirmed structurally by their own
        # internal, state-dependent fact_id qualifiers (never produced by
        # any other code path in this codebase).
        assert result.gated_facts["product.capabilities"].fact_id.endswith(":repository-evidence")
        assert result.gated_facts["product.formats"].fact_id.endswith(":repository-evidence")
        assert result.gated_facts["product.audience"].fact_id.endswith(":agent-drafted-grounded")
        assert result.gated_facts["product.problems_solved"].fact_id.endswith(
            ":agent-drafted-grounded"
        )
        assert result.gated_facts["product.audience"].source.source_type == "agent_drafted"
        # evidence_fact_candidate() is deliberately source-agnostic (its own
        # docstring: "agnostic to human vs. machine authorship already") --
        # it always records mechanical_repository, whether the specification
        # came from a human-authored policy or this capability's own draft.
        assert result.gated_facts["product.capabilities"].source.source_type == (
            "mechanical_repository"
        )


class TestOneFieldBlockedThenRepaired:
    def test_repair_hint_fixes_the_blocked_field_on_second_attempt(self, tmp_path):
        root = _make_repo(tmp_path)
        facts_so_far = _facts_so_far()
        calls: list[tuple] = []

        def draft_fn(hints, current_facts):
            calls.append((hints, current_facts))
            if len(calls) == 1:
                return _draft_with_bad_capabilities_evidence()
            return _good_draft()

        result = capability.orchestrate_product_truth_draft(
            ORG_REPO,
            facts_so_far,
            root,
            "abc1234",
            "2026-07-25T00:00:00+00:00",
            draft_fn=draft_fn,
            verify_example_fn=_always_verified_example,
        )

        assert result.repair_attempts == 1
        assert result.findings == []
        assert len(calls) == 2
        assert calls[0][0] is None
        # The second call received the exact per-field failure reason the
        # real evidence_fact_candidate() gate produced -- not a generic or
        # re-derived message.
        second_hints = calls[1][0]
        assert "product.capabilities" in second_hints
        assert any(
            "evidence file missing" in reason for reason in second_hints["product.capabilities"]
        )
        assert result.gated_facts["product.capabilities"].verification_state == "verified"


class TestRepairExhaustionEscalates:
    """`RPOC-033` item 5: a field still blocked after
    `MAX_PRODUCT_TRUTH_DRAFT_REPAIR_ATTEMPTS` real repair attempts must
    escalate as a finding -- never silently dropped, never fabricated."""

    def test_persistent_block_stops_after_max_attempts_and_escalates(self, tmp_path):
        root = _make_repo(tmp_path)
        facts_so_far = _facts_so_far()
        calls: list[tuple] = []

        def draft_fn(hints, current_facts):
            calls.append((hints, current_facts))
            return _draft_with_bad_capabilities_evidence()

        result = capability.orchestrate_product_truth_draft(
            ORG_REPO,
            facts_so_far,
            root,
            "abc1234",
            "2026-07-25T00:00:00+00:00",
            draft_fn=draft_fn,
            verify_example_fn=_always_verified_example,
        )

        assert result.repair_attempts == capability.MAX_PRODUCT_TRUTH_DRAFT_REPAIR_ATTEMPTS
        # One initial attempt + MAX repair attempts.
        assert len(calls) == capability.MAX_PRODUCT_TRUTH_DRAFT_REPAIR_ATTEMPTS + 1
        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding["repository"] == ORG_REPO
        assert finding["field"] == "product.capabilities"
        assert finding["actionable"] is True
        assert finding["repair_attempts"] == capability.MAX_PRODUCT_TRUTH_DRAFT_REPAIR_ATTEMPTS
        assert any("evidence file missing" in reason for reason in finding["failure_reasons"])
        assert result.gated_facts["product.capabilities"].verification_state == "blocked"


class TestMinimalExampleGating:
    def test_local_verification_none_blocks_example_without_a_crash(self, tmp_path):
        root = _make_repo(tmp_path)
        facts_so_far = _facts_so_far()

        result = capability.orchestrate_product_truth_draft(
            ORG_REPO,
            facts_so_far,
            root,
            "abc1234",
            "2026-07-25T00:00:00+00:00",
            draft_fn=lambda hints, facts: _good_draft(),
            verify_example_fn=lambda example: None,
        )

        assert result.gated_facts["example.minimal"].verification_state == "blocked"
        assert result.repair_attempts == capability.MAX_PRODUCT_TRUTH_DRAFT_REPAIR_ATTEMPTS
        assert any(f["field"] == "example.minimal" for f in result.findings)

    def test_compiler_diagnostic_is_passed_to_the_repair_attempt(self, tmp_path):
        root = _make_repo(tmp_path)
        facts_so_far = _facts_so_far()
        calls: list[dict[str, list[str]] | None] = []
        failed_compile = ExampleExecutionResultV1(
            argv=["dotnet", "build"],
            return_code=1,
            stdout="Build FAILED.",
            stderr="Program.cs(4,31): error CS1003: Syntax error, ',' expected",
            timed_out=False,
            environment_names=["CI"],
        )
        failed_result = LocalProductVerificationV1(
            org_repo=ORG_REPO,
            source_revision="abc1234",
            ecosystem="dotnet",
            outcome="BUILD_FAILED",
            detail="exact README example compilation failed",
            build=failed_compile,
            example_compile=failed_compile,
        )

        def draft_fn(hints, current_facts):
            calls.append(hints)
            return _good_draft()

        verification_results = iter([failed_result, _verified_local_result()])
        result = capability.orchestrate_product_truth_draft(
            ORG_REPO,
            facts_so_far,
            root,
            "abc1234",
            "2026-07-25T00:00:00+00:00",
            draft_fn=draft_fn,
            verify_example_fn=lambda example: next(verification_results),
        )

        assert result.findings == []
        assert result.repair_attempts == 1
        assert calls[0] is None
        assert "error CS1003" in calls[1]["example.minimal"][0]


class TestRealGateSpies:
    """Confirms the exact real functions are invoked with the expected
    arguments -- not just that their observable output shape matches."""

    def test_evidence_fact_candidate_is_invoked_for_each_evidence_backed_field(
        self, tmp_path, monkeypatch
    ):
        root = _make_repo(tmp_path)
        facts_so_far = _facts_so_far()
        recorded: list[str] = []
        real = capability.evidence_fact_candidate

        def spy(root_arg, source_revision, observed_at, field_name, specifications):
            recorded.append(field_name)
            return real(root_arg, source_revision, observed_at, field_name, specifications)

        monkeypatch.setattr(capability, "evidence_fact_candidate", spy)

        capability.orchestrate_product_truth_draft(
            ORG_REPO,
            facts_so_far,
            root,
            "abc1234",
            "2026-07-25T00:00:00+00:00",
            draft_fn=lambda hints, facts: _good_draft(),
            verify_example_fn=_always_verified_example,
        )

        assert set(recorded) == {"product.capabilities", "product.formats"}

    def test_positive_api_symbols_cannot_prove_a_negative_limitation(self, tmp_path):
        root = _make_repo(tmp_path)
        draft = _good_draft().model_copy(
            update={
                "limitations": [
                    EvidenceBackedProductFact(
                        value="Widget processing is incomplete.",
                        evidence_paths=["src/Widget.java"],
                        required_symbols=["Widget"],
                    )
                ]
            }
        )

        result = capability.orchestrate_product_truth_draft(
            ORG_REPO,
            _facts_so_far(),
            root,
            "abc1234",
            "2026-07-25T00:00:00+00:00",
            draft_fn=lambda hints, facts: draft,
            verify_example_fn=_always_verified_example,
        )

        limitation = result.gated_facts["product.limitations"]
        assert limitation.verification_state == "blocked"
        assert "does not express a constraint" in str(limitation.value)

    def test_explicit_constraint_anchor_can_prove_a_limitation(self, tmp_path):
        root = _make_repo(tmp_path)
        (root / "LIMITATIONS.md").write_text(
            "Streaming mode is not supported.\n",
            encoding="utf-8",
        )
        draft = _good_draft().model_copy(
            update={
                "limitations": [
                    EvidenceBackedProductFact(
                        value="Streaming mode is not supported.",
                        evidence_paths=["LIMITATIONS.md"],
                        required_symbols=["not supported"],
                    )
                ]
            }
        )

        result = capability.orchestrate_product_truth_draft(
            ORG_REPO,
            _facts_so_far(),
            root,
            "abc1234",
            "2026-07-25T00:00:00+00:00",
            draft_fn=lambda hints, facts: draft,
            verify_example_fn=_always_verified_example,
        )

        limitation = result.gated_facts["product.limitations"]
        assert limitation.verification_state == "verified"
        assert limitation.value == ["Streaming mode is not supported."]

    def test_groundedness_fact_candidate_is_invoked_for_each_interpretive_field(
        self, tmp_path, monkeypatch
    ):
        root = _make_repo(tmp_path)
        facts_so_far = _facts_so_far()
        recorded: list[str] = []
        real = capability.groundedness_fact_candidate

        def spy(field_name, claims, facts_so_far_arg, source_revision, observed_at):
            recorded.append(field_name)
            return real(field_name, claims, facts_so_far_arg, source_revision, observed_at)

        monkeypatch.setattr(capability, "groundedness_fact_candidate", spy)

        capability.orchestrate_product_truth_draft(
            ORG_REPO,
            facts_so_far,
            root,
            "abc1234",
            "2026-07-25T00:00:00+00:00",
            draft_fn=lambda hints, facts: _good_draft(),
            verify_example_fn=_always_verified_example,
        )

        assert set(recorded) == {"product.audience", "product.problems_solved"}


class TestEvidenceBackedFactsFeedForwardIntoRepairGrounding:
    """The real fix behind the live dry-run proof's own qualitative finding:
    a repository with NO rich pre-existing objective fact (only bare
    mechanical facts like product.identity) cannot ground an audience/
    problems_solved claim on the FIRST attempt -- there is nothing citable
    yet. Once capabilities/formats/limitations are drafted and verified,
    THIS SAME draft's own freshly-gated technical facts become real,
    independently re-checkable grounding material a repair attempt can cite
    -- proven here end-to-end through the real groundedness_fact_candidate()
    gate, not asserted."""

    def test_audience_grounds_in_this_rounds_own_verified_capabilities_on_repair(self, tmp_path):
        root = _make_repo(tmp_path)
        # No rich descriptive fact available up front -- only a bare
        # mechanical identity fact with no product-shape vocabulary at all.
        bare_identity = _established_fact(
            "product.identity",
            {"family": "widget", "platform": "java", "ecosystem": "java"},
            "identity",
        )
        records = [bare_identity]
        seen = {"product.identity"}
        for field_name in REQUIRED_PRODUCT_FIELDS:
            if field_name in seen:
                continue
            records.append(
                FactRecordV2(
                    fact_id=descriptive_fact_id(field_name, "missing"),
                    field=field_name,
                    value=None,
                    source=_source(),
                    verification_state="missing",
                    authoritative_owner="repository-owner",
                    confidence=0.0,
                    affected_surfaces=["readme"],
                )
            )
        selected = {}
        for fact in records:
            selected.setdefault(fact.field, fact.fact_id)
        bare_facts_so_far = ProductFactsV2(
            org_repo=ORG_REPO, facts=records, selected_fact_ids=selected
        )

        capabilities_fact = EvidenceBackedProductFact(
            value="Create and process Widget objects.",
            evidence_paths=["src/Widget.java"],
            required_symbols=["public class Widget"],
        )

        def draft_fn(hints, current_facts):
            if hints is None:
                # First attempt: nothing yet to ground audience in (the bare
                # identity fact has no usable vocabulary) -- draft
                # capabilities/formats correctly (so they pass and get fed
                # forward) but let audience/problems_solved fail honestly.
                return DraftProductTruthV1(
                    audience=[
                        InterpretiveClaimV1(
                            claim_id="a1",
                            text="Developers using Java for Widget objects.",
                            supporting_fact_ids=[bare_identity.fact_id],
                        )
                    ],
                    problems_solved=[
                        InterpretiveClaimV1(
                            claim_id="p1",
                            text="Java developers who create and process Widget objects.",
                            supporting_fact_ids=[bare_identity.fact_id],
                        )
                    ],
                    capabilities=[capabilities_fact],
                    formats=[capabilities_fact],
                    limitations=[],
                    minimal_example=MinimalExamplePolicy(
                        language="java",
                        class_name="ReadmeExample",
                        code="public class ReadmeExample {}",
                        evidence_paths=["src/Widget.java"],
                        required_symbols=["public class Widget"],
                    ),
                )
            # Repair attempt: capabilities should now be citable in
            # `current_facts` -- cite it for a claim whose every word is a
            # literal substring of the (JSON-dumped, per `_value_text()`)
            # capabilities fact's own value, "Create and process Widget
            # objects.".
            capabilities_fact_id = current_facts.selected_fact_ids["product.capabilities"]
            return DraftProductTruthV1(
                audience=[
                    InterpretiveClaimV1(
                        claim_id="a1",
                        text="Developers using Java.",
                        supporting_fact_ids=[bare_identity.fact_id],
                    )
                ],
                problems_solved=[
                    InterpretiveClaimV1(
                        claim_id="p1",
                        text="Create and process Widget objects.",
                        supporting_fact_ids=[capabilities_fact_id],
                    )
                ],
                capabilities=[capabilities_fact],
                formats=[capabilities_fact],
                limitations=[],
                minimal_example=MinimalExamplePolicy(
                    language="java",
                    class_name="ReadmeExample",
                    code="public class ReadmeExample {}",
                    evidence_paths=["src/Widget.java"],
                    required_symbols=["public class Widget"],
                ),
            )

        result = capability.orchestrate_product_truth_draft(
            ORG_REPO,
            bare_facts_so_far,
            root,
            "abc1234",
            "2026-07-25T00:00:00+00:00",
            draft_fn=draft_fn,
            verify_example_fn=_always_verified_example,
        )

        assert result.gated_facts["product.capabilities"].verification_state == "verified"
        assert result.gated_facts["product.audience"].verification_state == "verified"
        assert result.gated_facts["product.problems_solved"].verification_state == "verified"
        assert result.repair_attempts == 1
        assert result.findings == []


class TestToPolicyShape:
    def test_drafted_result_round_trips_through_real_product_truth_policy(self):
        shape = capability._to_policy_shape(_good_draft())

        assert shape["audience"] == ["Developers using Java."]
        assert shape["capabilities"][0]["evidence_paths"] == ["src/Widget.java"]
        assert shape["minimal_example"]["language"] == "java"


class TestGeneratedCodeNormalization:
    def test_orchestration_normalizes_smart_quotes_before_verification_and_output(self, tmp_path):
        root = _make_repo(tmp_path)
        draft = _good_draft()
        draft = draft.model_copy(
            update={
                "minimal_example": draft.minimal_example.model_copy(
                    update={"code": "var name = \u201cBox\u201d;"}
                )
            }
        )
        verified_code: list[str] = []

        def verify(example):
            verified_code.append(example.code)
            return _always_verified_example(example)

        result = capability.orchestrate_product_truth_draft(
            ORG_REPO,
            _facts_so_far(),
            root,
            "abc1234",
            "2026-07-25T00:00:00+00:00",
            draft_fn=lambda hints, facts: draft,
            verify_example_fn=verify,
        )

        assert verified_code == ['var name = "Box";']
        assert result.draft.minimal_example.code == 'var name = "Box";'


class TestGeneratedExampleQuality:
    def test_private_python_attribute_blocks_before_compiler_and_drives_repair(self, tmp_path):
        root = _make_repo(tmp_path)
        bad = _good_draft()
        bad = bad.model_copy(
            update={
                "minimal_example": bad.minimal_example.model_copy(
                    update={
                        "language": "python",
                        "code": "mesh._control_points.append(point)",
                    }
                )
            }
        )
        good = _good_draft()
        calls: list[dict[str, list[str]] | None] = []

        def draft_fn(hints, facts):
            calls.append(hints)
            return bad if hints is None else good

        def verify(example):
            assert example.code != bad.minimal_example.code
            return _always_verified_example(example)

        result = capability.orchestrate_product_truth_draft(
            ORG_REPO,
            _facts_so_far(),
            root,
            "abc1234",
            "2026-07-25T00:00:00+00:00",
            draft_fn=draft_fn,
            verify_example_fn=verify,
        )

        assert result.gated_facts["example.minimal"].verification_state == "verified"
        assert calls[1] is not None
        assert "_control_points" in calls[1]["example.minimal"][0]


class TestRepositoryExampleFallback:
    def test_repeated_bad_draft_uses_only_a_locally_verified_readme_example(self, tmp_path):
        root = _make_repo(tmp_path)
        (root / "README.md").write_text(
            """# Widget

```java
public class ReadmeExample {}
```
""",
            encoding="utf-8",
        )
        bad = _good_draft().model_copy(
            update={
                "minimal_example": MinimalExamplePolicy(
                    language="java",
                    class_name="Broken",
                    code="public class Broken { Missing value; }",
                    evidence_paths=["src/Widget.java"],
                    required_symbols=["Missing"],
                )
            }
        )
        verified: list[str] = []

        def verify(example):
            if example.code == "public class ReadmeExample {}\n":
                verified.append(example.code)
                return _always_verified_example(example)
            return LocalProductVerificationV1(
                org_repo=ORG_REPO,
                source_revision="abc1234",
                ecosystem="java",
                outcome="BUILD_FAILED",
                detail="example compilation failed",
            )

        result = capability.orchestrate_product_truth_draft(
            ORG_REPO,
            _facts_so_far(),
            root,
            "abc1234",
            "2026-07-25T00:00:00+00:00",
            draft_fn=lambda hints, facts: bad,
            verify_example_fn=verify,
        )

        assert result.repair_attempts == capability.MAX_PRODUCT_TRUTH_DRAFT_REPAIR_ATTEMPTS
        assert verified == ["public class ReadmeExample {}\n"]
        assert result.draft.minimal_example.code == "public class ReadmeExample {}\n"
        assert result.gated_facts["example.minimal"].verification_state == "verified"
        assert all(finding["field"] != "example.minimal" for finding in result.findings)


class TestGatedFieldsExhaustive:
    def test_all_six_gated_fields_always_present_in_result(self, tmp_path):
        root = _make_repo(tmp_path)
        facts_so_far = _facts_so_far()

        result = capability.orchestrate_product_truth_draft(
            ORG_REPO,
            facts_so_far,
            root,
            "abc1234",
            "2026-07-25T00:00:00+00:00",
            draft_fn=lambda hints, facts: _good_draft(),
            verify_example_fn=_always_verified_example,
        )

        assert set(result.gated_facts) == set(capability._GATED_FIELDS)


class TestResetFieldsToMissing:
    def test_gated_fields_reset_to_missing_even_when_previously_policy_approved(self):
        capabilities = _established_fact(
            "product.capabilities", ["pre-existing capability"], "repository-evidence"
        )
        facts_so_far_with_existing = ProductFactsV2(
            org_repo=ORG_REPO,
            facts=[*_facts_so_far().facts, capabilities],
            selected_fact_ids={
                **_facts_so_far().selected_fact_ids,
                "product.capabilities": capabilities.fact_id,
            },
        )

        reset = capability._reset_fields_to_missing(
            facts_so_far_with_existing, capability._GATED_FIELDS
        )

        assert reset.selected_fact("product.capabilities").verification_state == "missing"
        assert reset.selected_fact("product.identity").verification_state == "verified"


class TestReplaceFacts:
    def test_replaces_without_violating_fact_id_uniqueness(self):
        facts_so_far = _facts_so_far()
        new_capabilities = _established_fact(
            "product.capabilities", ["freshly verified"], "repository-evidence"
        )

        updated = capability._replace_facts(
            facts_so_far, {"product.capabilities": new_capabilities}
        )

        assert updated.selected_fact("product.capabilities").fact_id == new_capabilities.fact_id
        assert len([f for f in updated.facts if f.field == "product.capabilities"]) == 1


class TestSourceBuildAcquisitionPromotion:
    def test_verified_drafted_example_promotes_blocked_source_build(self):
        facts = _facts_so_far()
        acquisition = _established_fact(
            "installation.verified_acquisition",
            {
                "method": "source_build",
                "outcome": "BLOCKED_LOCAL_VERIFICATION",
                "detail": "no example yet",
            },
            "disposable-source-build",
        ).model_copy(update={"verification_state": "blocked", "confidence": 0.0})
        facts = capability._replace_facts(facts, {"installation.verified_acquisition": acquisition})
        example = _established_fact(
            "example.minimal",
            {
                "verification_outcome": "SOURCE_BUILD_VERIFIED",
                "verification_detail": "source build and exact example compilation passed",
            },
            "agent-drafted-example",
        )

        updates = capability._promote_source_build_acquisition(facts, {"example.minimal": example})

        promoted = updates["installation.verified_acquisition"]
        assert promoted.verification_state == "verified"
        assert promoted.value["outcome"] == "SOURCE_BUILD_VERIFIED"
        assert promoted.confidence == 1.0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
