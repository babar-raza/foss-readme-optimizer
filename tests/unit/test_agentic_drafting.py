"""Unit tests for `facts/agentic_drafting.py`: the bounded repository-
context selector, the citable-objective-facts filter, the repair-hint
formatter, and `draft_product_truth()`'s own LLM-call wiring (mocked via
fixture analysis and forced-tool clients -- no live network call in this
file)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from readme_agent.errors import LLMError
from readme_agent.facts import agentic_drafting
from readme_agent.facts.agentic_drafting import DraftProductTruthV1
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.llm import prompt_registry
from readme_agent.llm.analysis_client import AnalysisResult, FixtureAnalysisClient
from readme_agent.llm.schema import LLMResponseMeta

ORG_REPO = "acme/widget"


def _source(state: str = "verified") -> FactSourceV2:
    return FactSourceV2(
        source_type="approved_policy" if state == "policy_approved" else "mechanical_repository",
        location="repository://acme/widget",
        source_revision="abc1234",
    )


def _fact(field_name: str, value, state: str = "verified", qualifier="q") -> FactRecordV2:
    return FactRecordV2(
        fact_id=descriptive_fact_id(field_name, qualifier),
        field=field_name,
        value=value,
        source=_source(state),
        verification_state=state,
        authoritative_owner="repository-owner",
        confidence=1.0 if state in {"verified", "policy_approved"} else 0.0,
        affected_surfaces=["readme.opening"],
    )


def _facts_so_far(*explicit: FactRecordV2) -> ProductFactsV2:
    records = list(explicit)
    seen = {fact.field for fact in records}
    for field_name in REQUIRED_PRODUCT_FIELDS:
        if field_name in seen:
            continue
        records.append(_fact(field_name, None, state="missing", qualifier="missing"))
    selected = {}
    for fact in records:
        selected.setdefault(fact.field, fact.fact_id)
    return ProductFactsV2(org_repo=ORG_REPO, facts=records, selected_fact_ids=selected)


class TestCitableObjectiveFacts:
    def test_self_referential_fields_are_always_excluded(self):
        audience = _fact("product.audience", ["existing audience"], state="policy_approved")
        problems = _fact("product.problems_solved", ["existing problem"], state="verified")
        identity = _fact("product.identity", {"family": "widget"}, state="verified")
        facts_so_far = _facts_so_far(audience, problems, identity)

        citable = agentic_drafting._citable_objective_facts(facts_so_far)
        fields = {entry["field"] for entry in citable["facts"]}

        assert "product.audience" not in fields
        assert "product.problems_solved" not in fields
        assert "example.minimal" not in fields
        assert "product.identity" in fields

    def test_evidence_backed_fields_are_citable_once_accepted(self):
        """Unlike the self-referential fields above, capabilities/formats/
        limitations ARE includable once accepted -- real, independently
        re-checkable grounding material for audience/problems_solved.
        `capabilities/draft_product_truth.py::orchestrate_product_truth_
        draft()` is what actually prevents a repository's PRE-EXISTING
        product_truth from leaking in (it resets these three fields to
        `missing` before calling this module at all); this module's own
        filter only needs to keep the self-referential fields out."""
        capabilities = _fact(
            "product.capabilities", ["freshly-drafted-and-verified capability"], state="verified"
        )
        facts_so_far = _facts_so_far(capabilities)

        citable = agentic_drafting._citable_objective_facts(facts_so_far)
        fields = {entry["field"] for entry in citable["facts"]}

        assert "product.capabilities" in fields

    def test_unaccepted_verification_states_are_excluded(self):
        blocked_license = _fact("product.license", "MIT", state="blocked")
        facts_so_far = _facts_so_far(blocked_license)

        citable = agentic_drafting._citable_objective_facts(facts_so_far)
        fields = {entry["field"] for entry in citable["facts"]}

        assert "product.license" not in fields

    def test_missing_fields_are_excluded_by_default(self):
        facts_so_far = _facts_so_far()

        citable = agentic_drafting._citable_objective_facts(facts_so_far)

        assert citable["facts"] == []
        assert citable["org_repo"] == ORG_REPO


class TestFormatRepairHints:
    def test_no_hints_returns_empty_string(self):
        assert agentic_drafting._format_repair_hints(None) == ""
        assert agentic_drafting._format_repair_hints({}) == ""

    def test_hints_are_formatted_per_field(self):
        text = agentic_drafting._format_repair_hints(
            {"product.capabilities": ["evidence file missing: src/Nope.java"]}
        )

        assert "product.capabilities" in text
        assert "evidence file missing: src/Nope.java" in text


def test_product_truth_prompt_requires_subject_bound_capability_anchors():
    prompt = prompt_registry.get("draft_product_truth")

    assert prompt is not None
    assert prompt.version == "17"
    assert "claim itself MUST name the exact subject" in prompt.system
    assert "one ambiguous, constraint-bearing, or subject-unbound" in prompt.system
    assert "repository-owned example source before README prose" in prompt.system
    assert '"<verified product name> Enterprise Edition"' in prompt.system
    assert "must contain no source comments" in prompt.system
    assert "add no unrelated or decorative anchors" in prompt.system
    assert "separately derives the actual imported package symbols" in prompt.system


class TestSelectBoundedRepoContext:
    def test_readme_manifest_and_source_are_included(self, tmp_path):
        (tmp_path / "README.md").write_text("# Widget\n\nA Java widget library.", encoding="utf-8")
        (tmp_path / "pom.xml").write_text(
            "<project><artifactId>widget</artifactId></project>", encoding="utf-8"
        )
        src = tmp_path / "src" / "main" / "java" / "Widget.java"
        src.parent.mkdir(parents=True)
        src.write_text("public class Widget {}", encoding="utf-8")

        context = agentic_drafting._select_bounded_repo_context(tmp_path, "java")

        assert "README.md" in context
        assert "A Java widget library" in context
        assert "pom.xml" in context
        assert "Widget.java" in context
        assert "public class Widget" in context

    @pytest.mark.parametrize(
        ("ecosystem", "filename", "content"),
        [
            ("net", "Widget.cs", "public class Widget {}"),
            ("cpp", "widget.cpp", "int widget() { return 1; }"),
            ("rust", "lib.rs", "pub fn widget() {}"),
        ],
    )
    def test_registry_ecosystem_names_include_their_native_sources(
        self, tmp_path, ecosystem, filename, content
    ):
        source = tmp_path / "src" / filename
        source.parent.mkdir()
        source.write_text(content, encoding="utf-8")

        context = agentic_drafting._select_bounded_repo_context(tmp_path, ecosystem)

        assert filename in context
        assert content in context

    def test_budget_is_respected(self, tmp_path):
        (tmp_path / "README.md").write_text("x" * 1000, encoding="utf-8")
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        for i in range(50):
            (src_dir / f"File{i}.java").write_text("y" * 2000, encoding="utf-8")

        context = agentic_drafting._select_bounded_repo_context(tmp_path, "java")

        assert len(context) <= agentic_drafting.MAX_CONTEXT_CHARS + 200

    def test_no_readable_content_returns_placeholder(self, tmp_path):
        context = agentic_drafting._select_bounded_repo_context(tmp_path, "java")

        assert context == "(no repository context could be read)"

    def test_noise_directories_are_excluded(self, tmp_path):
        noisy = tmp_path / "node_modules" / "dep"
        noisy.mkdir(parents=True)
        (noisy / "Ignored.java").write_text("public class Ignored {}", encoding="utf-8")

        context = agentic_drafting._select_bounded_repo_context(tmp_path, "java")

        assert "Ignored" not in context

    def test_production_source_precedes_tests_and_docs_under_budget(self, tmp_path, monkeypatch):
        source = tmp_path / "package" / "Widget.py"
        source.parent.mkdir()
        source.write_text("class Widget:\n    pass\n", encoding="utf-8")
        tests = tmp_path / "tests" / "test_widget.py"
        tests.parent.mkdir()
        tests.write_text("test detail " * 20, encoding="utf-8")
        docs = tmp_path / "docs" / "guide.md"
        docs.parent.mkdir()
        docs.write_text("documentation detail " * 20, encoding="utf-8")
        monkeypatch.setattr(agentic_drafting, "MAX_CONTEXT_CHARS", 80)

        context = agentic_drafting._select_bounded_repo_context(tmp_path, "python")

        assert "class Widget" in context
        assert "test detail" not in context
        assert "documentation detail" not in context

    def test_repository_owned_example_precedes_unrelated_production_source(self, tmp_path):
        (tmp_path / "README.md").write_text("# Widget", encoding="utf-8")
        example = tmp_path / "_examples" / "quickstart" / "main.go"
        example.parent.mkdir(parents=True)
        example.write_text("package main\nfunc main() { widget.Open() }\n", encoding="utf-8")
        unrelated = tmp_path / "aaa.go"
        unrelated.write_text("package widget\nfunc InternalDetail() {}\n", encoding="utf-8")

        context = agentic_drafting._select_bounded_repo_context(tmp_path, "go")

        assert context.index("_examples/quickstart/main.go") < context.index("aaa.go")


def _draft_payload(**overrides) -> dict:
    base = {
        "audience": [
            {
                "claim_id": "audience-1",
                "text": "Java developers.",
                "supporting_fact_ids": ["product.identity:q"],
            }
        ],
        "problems_solved": [
            {
                "claim_id": "problem-1",
                "text": "Process widgets.",
                "supporting_fact_ids": ["product.identity:q"],
            }
        ],
        "capabilities": [
            {
                "value": "Create widgets.",
                "evidence_paths": ["src/Widget.java"],
                "required_symbols": ["public class Widget"],
            }
        ],
        "formats": [
            {
                "value": "Read WGT files.",
                "evidence_paths": ["src/Widget.java"],
                "required_symbols": [],
            }
        ],
        "limitations": [],
        "minimal_example": {
            "language": "java",
            "class_name": "ReadmeExample",
            "code": "public class ReadmeExample {}",
            "evidence_paths": ["src/Widget.java"],
            "required_symbols": [],
        },
    }
    base.update(overrides)
    return base


class TestDraftProductTruth:
    def test_net_registry_key_uses_the_dotnet_typed_example_language(self):
        assert agentic_drafting._draft_language("net") == "dotnet"

    def test_capability_tool_contract_accepts_exactly_one_anchor_per_claim(self):
        schema = agentic_drafting._draft_product_truth_tool_schema(
            accepted_fact_ids=["product.platforms:q"],
            evidence_paths=["src/Widget.java"],
            language="java",
        )
        properties = schema["function"]["parameters"]["properties"]

        assert (
            properties["capabilities"]["items"]["properties"]["required_symbols"]["maxItems"] == 1
        )
        assert properties["formats"]["items"]["properties"]["required_symbols"]["maxItems"] == 4

    def test_valid_response_parses_into_draft_product_truth_v1(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            agentic_drafting,
            "require_listed",
            lambda org_repo: SimpleNamespace(org="acme", repo_name="widget", ecosystem="java"),
        )
        monkeypatch.setattr(agentic_drafting.paths, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(agentic_drafting, "clone_baseline", lambda entry, path: None)
        (tmp_path / "README.md").write_text("# Widget", encoding="utf-8")

        client = FixtureAnalysisClient(
            [AnalysisResult(parsed=_draft_payload(), meta=LLMResponseMeta())]
        )

        draft = agentic_drafting.draft_product_truth(
            ORG_REPO, facts_so_far=_facts_so_far(), client=client
        )

        assert isinstance(draft, DraftProductTruthV1)
        assert draft.minimal_example.language == "java"
        assert draft.audience[0].text == "Java developers."

    def test_production_transport_forces_the_complete_nested_schema(self, tmp_path, monkeypatch):
        captured = {}

        class FakeForcedToolClient:
            def __init__(self, *args, **kwargs):
                captured["init"] = (args, kwargs)

            def call(self, messages, tool_schema):
                captured["messages"] = messages
                captured["tool_schema"] = tool_schema
                return SimpleNamespace(arguments=_draft_payload(), meta=LLMResponseMeta())

        monkeypatch.setattr(
            agentic_drafting,
            "require_listed",
            lambda org_repo: SimpleNamespace(org="acme", repo_name="widget", ecosystem="java"),
        )
        monkeypatch.setattr(agentic_drafting.paths, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(agentic_drafting, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(agentic_drafting, "LiveForcedToolClient", FakeForcedToolClient)
        (tmp_path / "README.md").write_text("# Widget", encoding="utf-8")

        draft = agentic_drafting.draft_product_truth(
            ORG_REPO,
            facts_so_far=_facts_so_far(
                _fact("product.identity", {"ecosystem": "java"}, state="verified")
            ),
        )

        assert draft.audience[0].supporting_fact_ids == ["product.identity:q"]
        function = captured["tool_schema"]["function"]
        assert function["name"] == "submit_product_truth_draft"
        parameters = function["parameters"]
        assert set(parameters["required"]) == set(parameters["properties"])
        assert parameters["additionalProperties"] is False
        assert parameters["properties"]["audience"]["maxItems"] == 1
        assert parameters["properties"]["capabilities"]["maxItems"] == 8
        assert (
            parameters["properties"]["minimal_example"]["properties"]["evidence_paths"]["maxItems"]
            == 4
        )
        assert parameters["properties"]["problems_solved"]["items"]["type"] == "object"
        assert set(parameters["properties"]["problems_solved"]["items"]["required"]) == {
            "claim_id",
            "text",
            "supporting_fact_ids",
        }
        assert (
            "product.identity:q"
            in parameters["properties"]["problems_solved"]["items"]["properties"][
                "supporting_fact_ids"
            ]["items"]["enum"]
        )
        assert parameters["properties"]["capabilities"]["items"]["properties"]["evidence_paths"][
            "items"
        ]["enum"] == ["README.md"]
        assert "required_symbols" in parameters["properties"]["capabilities"]["items"]["required"]
        assert (
            parameters["properties"]["capabilities"]["items"]["properties"]["required_symbols"][
                "minItems"
            ]
            == 1
        )
        assert parameters["properties"]["minimal_example"]["properties"]["language"]["enum"] == [
            "java"
        ]
        assert "required_symbols" in parameters["properties"]["minimal_example"]["required"]
        assert (
            parameters["properties"]["minimal_example"]["properties"]["required_symbols"][
                "minItems"
            ]
            == 1
        )
        assert captured["init"][1]["timeout"] == agentic_drafting._REQUEST_TIMEOUT_SECONDS
        assert captured["init"][1]["max_tokens"] == agentic_drafting._MAX_RESPONSE_TOKENS

    def test_invalid_response_raises_llm_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            agentic_drafting,
            "require_listed",
            lambda org_repo: SimpleNamespace(org="acme", repo_name="widget", ecosystem="java"),
        )
        monkeypatch.setattr(agentic_drafting.paths, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(agentic_drafting, "clone_baseline", lambda entry, path: None)

        client = FixtureAnalysisClient(
            [AnalysisResult(parsed={"not_the_right_shape": True}, meta=LLMResponseMeta())]
        )

        with pytest.raises(LLMError, match="did not match"):
            agentic_drafting.draft_product_truth(
                ORG_REPO, facts_so_far=_facts_so_far(), client=client
            )

    def test_pydantic_model_requires_min_one_capability(self):
        with pytest.raises(ValidationError):
            DraftProductTruthV1.model_validate(_draft_payload(capabilities=[]))

    def test_pydantic_model_rejects_unknown_language(self):
        with pytest.raises(ValidationError):
            DraftProductTruthV1.model_validate(
                _draft_payload(
                    minimal_example={
                        "language": "cobol",
                        "class_name": "X",
                        "code": "X",
                        "evidence_paths": ["a"],
                        "required_symbols": [],
                    }
                )
            )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
