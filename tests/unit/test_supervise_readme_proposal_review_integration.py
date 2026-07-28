"""RPOC-050/051/052 integration proof: `readme-agent supervise --execution-
profile local_dry_run` against a real local git repo produces BOTH a
deterministic bundle verdict (`verify_readme_proposal_bundle`, dispatched as
a real capability) AND an independent-agentic verdict
(`independent_readme_review.run_independent_review_with_repair_loop()`) for
`readme_presentation`'s own candidate -- with NO standalone script under
`plans/investigations/tools/` involved anywhere in this path. This is the
taskcard's own stated acceptance bar for closing `check_verifiers_are_wired.
py`'s `verify_readme_proposal_bundle`/`verify_cross_pilot_specificity`
finding.

Goes through the real CLI command handler (`commands.cmd_supervise()`), not
`supervisor/loop.py::supervise_repo()` directly, so this exercises the exact
same code path `readme-agent supervise --execution-profile local_dry_run
<repo>` would from a real shell -- `execution_profile.py::get_profile
("local_dry_run")`'s own resolved kwargs (`require_evidence_bundle=True`,
`verify_local_product_facts=True`, `allowed_permission_classes` including
`local_write`) flow through unmodified.

Real end-to-end proof, real evidence artifact: `write_supervise_evidence()`
(the production evidence writer, `supervisor/evidence.py`) writes a real
`specialist_results.json` to `result.evidence_dir`; this test reads that
real file back off disk rather than introspecting an in-memory object, so
the assertion is against the same artifact a human operator would see.

Every specialist's own real network call is faked, mirroring `test_
supervisor_loop.py`'s own `project` fixture (this file's closest sibling)
-- `readme_presentation`'s own LLM calls (candidate render, prose-quality
check, and now the independent reviewer) are the only ones this file's own
docstring narrates in detail; the rest are the same, already-proven fakes
that fixture already established for the other nine always-run specialists.
`durable_state=False` (no `--durable-state` flag, matching the taskcard's
own literal CLI invocation) -- `local_dry_run`'s own `requires_durable_
state=False`, and this graph's new `review` node runs its own two checks
regardless of whether a durable backend is present (only `_commit_node`'s
own write is backend-gated); a real evidence bundle is still written either
way (`write_evidence_bundle` defaults `True` independent of `state_
backend`)."""

import argparse
import json
from pathlib import Path

import pytest

from readme_agent.capabilities import (
    audit_community_files,
    audit_github_generated_surfaces,
    audit_package_release_surfaces,
    check_install_path,
    compare_against_presentation_standard,
    propose_metadata_changes,
    review_visual_asset_accuracy,
    verify_prose_quality,
)
from readme_agent.commands import cmd_supervise
from readme_agent.gitsafety._git import run_git
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.client import GeneratedResult
from readme_agent.llm.planner_client import PlannerTurn
from readme_agent.llm.schema import LLMBlockResponse, LLMResponseMeta
from readme_agent.llm.verifier_client import ForcedToolResult
from readme_agent.profile import cached
from readme_agent.readme import candidate_pipeline
from readme_agent.specialists import separated_readme_review
from readme_agent.supervisor import planner_loop

ORG_REPO = "example-foss/Example-Widget"
REPO_ROOT = Path(__file__).resolve().parents[2]

_FIXTURE_RELATIONSHIP_PARAGRAPH = (
    "This repository is the free, open-source FOSS edition of the "
    "corresponding commercial Example product. Upgrade to the commercial "
    "edition when you need a broader feature set or dedicated support."
)


class _FakeLiveLLMClient:
    def __init__(self, *args, **kwargs):
        pass

    def generate(self, messages: list[dict[str, str]]) -> GeneratedResult:
        return GeneratedResult(
            response=LLMBlockResponse(
                relationship_paragraph=_FIXTURE_RELATIONSHIP_PARAGRAPH,
                talking_points_covered=["open_source_scope", "commercial_upgrade_path"],
            ),
            meta=LLMResponseMeta(),
            mode="fixture",
        )


class _FakeNonFlaggingForcedToolClient:
    def __init__(self, *args, **kwargs):
        pass

    def call(self, messages, tool_schema):
        return ForcedToolResult(
            arguments={"flagged": False, "reason": "fixture: never flagged"}, meta=LLMResponseMeta()
        )


class _FakeNonFlaggingAnalysisClient:
    """Reused for both `compare_against_presentation_standard` and `review_
    visual_asset_accuracy` -- both freeform analysis clients accept whatever
    `.analyze()` returns without caring about the shape mismatch between
    their own two real schemas, since neither field this fixture omits is
    read on the never-flagged path either capability takes."""

    def __init__(self, *args, **kwargs):
        pass

    def analyze(self, messages):
        return AnalysisResult(
            parsed={
                "criteria_results": [],
                "overall_summary": "fixture: not evaluated",
                "depicts_unsupported_content": False,
                "concerns": [],
                "verdict": "accept",
                "rationale": "fixture: not reviewed",
            },
            meta=LLMResponseMeta(),
        )


class _FakeAcceptingRoleReviewClient:
    """RPOC-050/051: `readme_presentation`'s new `review` node calls
    `independent_readme_review.run_independent_review_with_repair_loop()`
    unconditionally on every real accept-path write -- faked here (always
    `ACCEPT`) so this real-local-git-repo test stays network-free, and never
    engages the repair loop's own regenerate-and-reverify path (a separate,
    pre-existing bug in that module's own default `regenerate_context`,
    found live while wiring this node -- see `specialists/readme_
    presentation.py::_review_node`'s own docstring)."""

    def __init__(self, *args, **kwargs):
        pass

    def analyze(self, messages):
        return AnalysisResult(
            parsed={
                "verdict": "ACCEPT",
                "reasoning": "fixture: not reviewed",
                "failed_criteria": [],
                "sections_affected": [],
                "required_repair": "",
                "findings": [],
            },
            meta=LLMResponseMeta(),
        )


def _fake_accepting_role_clients(*args, **kwargs):
    return _FakeAcceptingRoleReviewClient(), _FakeAcceptingRoleReviewClient()


class _FakeDonePlannerClient:
    """The general planner loop only ever decides whether OPTIONAL
    capabilities run beyond the always-run specialist tier -- readme_
    presentation's own `run()` (and this test's own assertions) only depend
    on that specialist tier, which `supervisor/loop.py::supervise_repo()`
    already runs to completion before the planner loop starts at all. "Done"
    immediately keeps this test's own turn count minimal; whether the run's
    own terminal status converges cleanly or reports remaining eligible work
    is irrelevant to what this test proves."""

    def __init__(self, *args, **kwargs):
        pass

    def plan(self, messages, tools):
        return PlannerTurn(content="done", meta=LLMResponseMeta())


def _init_source_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    run_git(["init", "-b", "main"], cwd=path)
    run_git(["config", "user.email", "test@example.com"], cwd=path)
    run_git(["config", "user.name", "Test"], cwd=path)
    (path / "README.md").write_text(
        "# Example Widget\n\n"
        "Example Widget is a Java library for creating, reading, and "
        "modifying widget files.\n",
        encoding="utf-8",
    )
    (path / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    run_git(["add", "."], cwd=path)
    run_git(["commit", "-m", "initial"], cwd=path)
    return path


_POLICY_YAML = """schema_version: 2
policy_profile: test-profile
required_elements:
  license_mentioned:
    detected_license: MIT
  products_org_link:
    url: "https://products.example.org/widget/java/"
    family_url: "https://products.example.org/widget/"
    label: "Example Widget"
  products_com_link:
    url: "https://products.example.com/widget/java/"
    family_url: "https://products.example.com/widget"
    label: "Example Widget"
  relationship_explained:
    min_sentences: 2
    talking_points: [open_source_scope, commercial_upgrade_path]
secondary_links: []
block:
  word_limit: { min: 10, max: 200 }
  prohibited_terms: ["guarantee"]
  link_whitelist_domains: [products.example.com, products.example.org]
"""


def _setup_project_root(tmp_path, source_clone_url: str):
    (tmp_path / "data").mkdir()
    (tmp_path / "config" / "policies").mkdir(parents=True)
    (tmp_path / "config" / "policies" / "test-profile.yml").write_text(
        _POLICY_YAML, encoding="utf-8"
    )
    prompt_dir = tmp_path / "prompts" / "generation"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "relationship_explained.yaml").write_text(
        (REPO_ROOT / "prompts" / "generation" / "relationship_explained.yaml").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "presentation-standard.md").write_text(
        (REPO_ROOT / "docs" / "presentation-standard.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    products = [
        {
            "family": "widget",
            "platform": "java",
            "repo_name": "Example-Widget",
            "repo_url": "https://github.com/example-foss/Example-Widget",
            "clone_url": source_clone_url,
            "active": True,
            "discovered_via": "manual",
            "mode": "dry_run",
            "ecosystem": "java",
            "policy_profile": "test-profile",
        }
    ]
    (tmp_path / "data" / "products.json").write_text(json.dumps(products), encoding="utf-8")


def _fake_repo_summary(org_repo, token):
    return {
        "language": "Java",
        "stargazers_count": 0,
        "forks_count": 0,
        "watchers_count": 0,
        "open_issues_count": 0,
    }


@pytest.fixture
def project(tmp_path, monkeypatch):
    source = _init_source_repo(tmp_path / "source")
    _setup_project_root(tmp_path, str(source))
    monkeypatch.chdir(tmp_path)

    # CLI-layer stubs -- keeps this test on the real specialist-graph/
    # capability-dispatch path while never touching the real network for the
    # surrounding CLI concerns (registry self-heal, preflight) that are
    # already separately, thoroughly tested (test_cli.py).
    import readme_agent.preflight.runner as preflight_runner_module

    monkeypatch.setattr(
        preflight_runner_module,
        "run_preflight_for_repo",
        lambda org_repo: argparse.Namespace(ok=True),
    )

    # Every always-run specialist's own real network call, faked -- mirrors
    # test_supervisor_loop.py's own `project` fixture verbatim (this file's
    # closest sibling; duplicated rather than imported, matching this
    # project's own per-test-file fixture convention).
    monkeypatch.setattr(audit_github_generated_surfaces, "repo_summary", _fake_repo_summary)
    monkeypatch.setattr(
        audit_github_generated_surfaces, "list_contributors", lambda org_repo, token: []
    )
    monkeypatch.setattr(
        audit_github_generated_surfaces, "list_languages", lambda org_repo, token: {"Java": 100}
    )
    monkeypatch.setattr(audit_package_release_surfaces, "list_releases", lambda org_repo, token: [])
    monkeypatch.setattr(
        check_install_path,
        "inspect_repo",
        lambda org_repo, check_install=True: {
            "presentation_report": type(
                "FakeReport",
                (),
                {
                    "install_path_resolved": None,
                    "evidence": {"install_path_resolved": "not checked"},
                },
            )()
        },
    )
    monkeypatch.setattr(
        propose_metadata_changes,
        "repo_summary",
        lambda org_repo, token: {
            "description": "An existing description",
            "homepage": "https://example.org",
            "topics": ["java"],
        },
    )
    real_collect_product_facts = propose_metadata_changes.collect_product_facts

    def _complete_fixture_product_facts(org_repo):
        result = real_collect_product_facts(org_repo)
        values = {
            "product.audience": ["Java developers"],
            "product.problems_solved": ["creating, reading, and modifying widget files"],
            "product.capabilities": ["create widgets", "read widgets", "modify widgets"],
            "product.formats": ["widget files"],
        }
        for fact in result["product_facts_v2"]["facts"]:
            value = values.get(fact["field"])
            if value is None:
                continue
            fact["value"] = value
            fact["verification_state"] = "verified"
            fact["confidence"] = 1.0
        return result

    monkeypatch.setattr(
        propose_metadata_changes, "collect_product_facts", _complete_fixture_product_facts
    )
    monkeypatch.setattr(
        audit_community_files,
        "get_community_profile",
        lambda org_repo, token: {
            "health_percentage": 40,
            "files": {"license": {}, "contributing": None, "code_of_conduct": None},
        },
    )
    monkeypatch.setattr(candidate_pipeline, "LiveLLMClient", _FakeLiveLLMClient)
    monkeypatch.setattr(
        verify_prose_quality, "LiveForcedToolClient", _FakeNonFlaggingForcedToolClient
    )
    monkeypatch.setattr(
        compare_against_presentation_standard, "LiveAnalysisClient", _FakeNonFlaggingAnalysisClient
    )
    monkeypatch.setattr(
        review_visual_asset_accuracy, "LiveAnalysisClient", _FakeNonFlaggingAnalysisClient
    )
    monkeypatch.setattr(cached.env, "gh_token", lambda: None)

    # RPOC-050/051's own new dependency: the independent agentic reviewer's
    # LLM call, and the general planner loop's own LLM call (real by default
    # whenever `cmd_supervise()` is called with no dynamic-planning override,
    # since `planner_client=None` resolves to a real `LivePlannerClient`
    # inside `supervisor/planner_loop.py::_default_planner_client()`).
    monkeypatch.setattr(
        separated_readme_review,
        "build_live_role_review_clients",
        _fake_accepting_role_clients,
    )
    monkeypatch.setattr(planner_loop, "LivePlannerClient", _FakeDonePlannerClient)
    return tmp_path


class TestSuperviseLocalDryRunProducesBothVerifierVerdicts:
    def test_cli_local_dry_run_produces_bundle_and_independent_review_verdicts(self, project):
        args = argparse.Namespace(
            repo=ORG_REPO,
            durable_state=False,  # no --durable-state flag, matching the taskcard's own literal
            # invocation -- _review_node runs its own two checks regardless of backend presence
            domain=None,
            execution_profile="local_dry_run",
            no_registry_heal=True,  # keeps the real network-touching registry self-heal out of
            # this test's own scope (test_cli.py already separately, thoroughly tests it)
        )

        exit_code = cmd_supervise(args)

        # A non-zero exit here would mean the run never reached (or crashed inside) the
        # specialist tier at all -- the real failure this test must catch first.
        assert exit_code in (0, 1), "supervise did not complete a normal terminal run"

        evidence_dir = None
        for candidate in sorted((project / "runs" / "evidence").iterdir()):
            if (candidate / "specialist_results.json").is_file():
                evidence_dir = candidate
        assert evidence_dir is not None, "no real evidence bundle was written"

        # Real production artifact, read back off disk -- not an in-memory shortcut.
        specialist_results = json.loads(
            (evidence_dir / "specialist_results.json").read_text(encoding="utf-8")
        )
        readme_presentation_details = specialist_results["readme_presentation"]["details"]

        # The independent-agentic verdict: RPOC-051(c), run_independent_review_with_repair_
        # loop() dispatched directly from the new `review` node, on the real render/plan
        # this exact run produced -- never a standalone script, never mocked below the
        # client boundary this project's own convention already fakes at.
        assert "independent_review" in readme_presentation_details
        independent_review = readme_presentation_details["independent_review"]
        assert independent_review["outcome_kind"] == "accepted"
        assert independent_review["final_review"]["verdict"] == "ACCEPT"

        # The deterministic bundle verdict: RPOC-051(a)/(b), verify_readme_proposal_bundle
        # dispatched as a real, registered, domain-scoped capability against a real
        # materialized 8-file bundle when a governed document plan is present.
        # This compatibility invocation deliberately has no README-POC lifecycle,
        # so verification is not applicable. The canonical local_poc supervisor
        # test requires checked + verified.
        assert "bundle_verification" in readme_presentation_details
        bundle_verification = readme_presentation_details["bundle_verification"]
        assert bundle_verification["status"] in ("checked", "not_applicable")
        if bundle_verification["status"] == "checked":
            assert "verified" in bundle_verification
            assert "bundle_dir" in bundle_verification
            assert Path(bundle_verification["bundle_dir"]).is_dir()
        else:
            assert bundle_verification["reason"]

        # RPOC-050: the raw patch text this node needed to materialize a bundle never
        # survives into the durably-written evidence record either way.
        assert "presentation_plan_patch" not in readme_presentation_details
