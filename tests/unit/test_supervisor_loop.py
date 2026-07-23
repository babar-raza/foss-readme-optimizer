"""`supervise_repo()` end to end against the real capability registry and
dispatcher, a synthetic local git repo (no network), and a fixture planner
-- a materially harder proof than Wave 1's N=1 spike: multi-round, real
replanning after a real failure, real durable convergence on a second call.
Mirrors `test_orchestrator.py`'s synthetic-local-repo fixture pattern."""

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
    registry,
    review_visual_asset_accuracy,
    verify_prose_quality,
)
from readme_agent.errors import LLMError
from readme_agent.gitsafety._git import run_git
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.client import GeneratedResult
from readme_agent.llm.planner_client import FixturePlannerClient, PlannerTurn
from readme_agent.llm.schema import LLMBlockResponse, LLMResponseMeta, Usage
from readme_agent.llm.verifier_client import ForcedToolResult
from readme_agent.profile import cached
from readme_agent.readme import candidate_pipeline
from readme_agent.specialists import registry as specialists_registry
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.schema import DomainStateV1, ModelRouteStatusV1, RunStateV1
from readme_agent.supervisor.loop import supervise_repo

# Proven-valid against the real word-count/prohibited-terms/talking-points
# rules (identical policy to test_orchestrator.py's own FIXTURE_RESPONSE,
# which those rules already validate) -- reused verbatim rather than
# hand-rolling a second sentence that might miss a rule's nuance.
_FIXTURE_RELATIONSHIP_PARAGRAPH = (
    "This repository is the free, open-source FOSS edition of the "
    "corresponding commercial Example product. Upgrade to the commercial "
    "edition when you need a broader feature set or dedicated support."
)


class _FakeLiveLLMClient:
    """Wave 7g: `readme_presentation` is the first specialist whose render
    step can reach the one real LLM call (`relationship_explained`) -- every
    test in this file used to be LLM-free, since no earlier specialist ever
    rendered anything. Faked here for the same reason every other real
    network call in this fixture already is: this project's own
    `@pytest.mark.live` convention keeps the offline suite genuinely
    offline."""

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
    """Wave 8.6 (`VER-006` reversal): `_verify_node` now additionally
    dispatches `verify_prose_quality` after a deterministic accept -- faked
    here (never flagged) so this file's existing accept/commit assertions
    are unaffected, matching `_FakeLiveLLMClient`'s own convention."""

    def __init__(self, *args, **kwargs):
        pass

    def call(self, messages, tool_schema):
        return ForcedToolResult(
            arguments={"flagged": False, "reason": "fixture: never flagged"}, meta=LLMResponseMeta()
        )


class _FakeAnalysisClient:
    """Wave 8.6 (comparison capability): `presentation_benchmarking` is a
    tenth always-run specialist whose classify step can reach a real LLM
    analysis call -- faked here for the same reason every other real
    network call in this fixture already is."""

    def __init__(self, *args, **kwargs):
        pass

    def analyze(self, messages):
        return AnalysisResult(
            parsed={"criteria_results": [], "overall_summary": "fixture: not evaluated"},
            meta=LLMResponseMeta(),
        )


class _FakeVisualAccuracyAnalysisClient:
    """Wave 8.6 (item H): `visual_preparation`'s classify step is followed
    by an additive, advisory-only vision-accuracy review -- faked here
    (never flags) for the same reason."""

    def __init__(self, *args, **kwargs):
        pass

    def analyze(self, messages):
        return AnalysisResult(
            parsed={
                "depicts_unsupported_content": False,
                "concerns": [],
                "verdict": "accept",
                "rationale": "fixture: not reviewed",
            },
            meta=LLMResponseMeta(),
        )


ORG_REPO = "example-foss/Example-FOSS-for-Java"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _tool_call(call_id: str, capability_id: str, arguments: dict | None = None) -> dict:
    return {
        "id": call_id,
        "function": {"name": capability_id, "arguments": json.dumps(arguments or {})},
    }


def _init_source_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    run_git(["init", "-b", "main"], cwd=path)
    run_git(["config", "user.email", "test@example.com"], cwd=path)
    run_git(["config", "user.name", "Test"], cwd=path)
    # Wave 8b: a title-only README (no body sentence at all) still has real
    # gaps (no license/products-links/relationship-explained mention) but
    # fails real validation once rendered (product_first_opening has nothing
    # to anchor to) -- proven-valid two-line body, matching test_orchestrator.
    # py's own BLANK_SLATE_README exactly, product name substituted, so the
    # independent verifier (Wave 8b) accepts the resulting real GENERATED
    # candidate instead of rejecting it.
    (path / "README.md").write_text(
        "# Example FOSS for Java\n\n"
        "Example FOSS for Java is a Java library for creating, reading, and "
        "modifying document files.\n",
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
    url: "https://products.example.org/thing/java/"
    family_url: "https://products.example.org/thing/"
    label: "Example FOSS for Java"
  products_com_link:
    url: "https://products.example.com/thing/java/"
    family_url: "https://products.example.com/thing"
    label: "Example for Java"
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
    # Wave 7d: metadata_presentation dispatches get_product_facts, which
    # needs a real config/policies/*.yml -- unlike 7b/7c's specialists, none
    # of which needed one, since neither dispatches get_product_facts.
    (tmp_path / "config" / "policies").mkdir(parents=True)
    (tmp_path / "config" / "policies" / "test-profile.yml").write_text(
        _POLICY_YAML, encoding="utf-8"
    )
    # Wave 8.5: llm.prompts.prompt_content_hash() reads
    # prompts/generation/relationship_explained.yaml fresh, cwd-relative, on
    # every call (readme_presentation's render step calls build_prompt()
    # unconditionally whenever relationship_explained is a real gap -- true
    # for this fixture's minimal README -- regardless of llm_mode). Staged
    # here the same way test_orchestrator.py's own _setup_project_root()
    # already does. build_prompt()/the supervisor's own prompt are read from
    # the eagerly import-time-cached prompt_registry instead, unaffected by
    # cwd, so no other prompt file needs staging here.
    prompt_dir = tmp_path / "prompts" / "generation"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "relationship_explained.yaml").write_text(
        (REPO_ROOT / "prompts" / "generation" / "relationship_explained.yaml").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    # Wave 8.6: compare_against_presentation_standard reads
    # docs/presentation-standard.md fresh, cwd-relative, on every call --
    # presentation_benchmarking is a tenth always-run specialist, so this
    # must be staged here the same way the prompt file above is.
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "presentation-standard.md").write_text(
        (REPO_ROOT / "docs" / "presentation-standard.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    products = [
        {
            "family": "thing",
            "platform": "java",
            "repo_name": "Example-FOSS-for-Java",
            "repo_url": "https://github.com/example-foss/Example-FOSS-for-Java",
            "clone_url": source_clone_url,
            "active": True,
            "discovered_via": "manual",
            "mode": "dry_run",
            "ecosystem": "java",
            "policy_profile": "test-profile",
        }
    ]
    (tmp_path / "data" / "products.json").write_text(json.dumps(products), encoding="utf-8")


class FakeStateBackend:
    """Wave 8.5: upgraded to the real `Lock` dataclass (was a bare
    `type("Lock", (), {"org_repo": ...})()` stand-in missing `holder_id`/
    `leased_until` entirely, confirmed by adversarial review to have already
    diverged from `tests/unit/test_state_backend.py::FakeStateBackend`'s own
    real lease semantics) plus a second, genuinely separate `_run_locks`
    dict for the new run-lock, mirroring the real `GitStateBackend`'s own
    two-tracking-dict design exactly."""

    def __init__(self):
        self._states: dict[str, RunStateV1] = {}
        self._locks: dict[str, Lock] = {}
        self._run_locks: dict[str, Lock] = {}
        self._model_routes: dict[str, object] = {}

    def load(self, org_repo):
        return self._states.get(org_repo)

    def save(self, org_repo, state, expected_version):
        current = self._states.get(org_repo)
        cv = current.state_version if current else None
        if expected_version != cv:
            return SaveResult(outcome="stale", new_version=cv)
        nv = (cv or 0) + 1
        self._states[org_repo] = state.model_copy(update={"state_version": nv})
        return SaveResult(outcome="saved", new_version=nv)

    def acquire_lock(self, org_repo):
        if org_repo in self._locks:
            return None
        lock = Lock(org_repo=org_repo, holder_id="fake-holder", leased_until="9999-01-01T00:00:00")
        self._locks[org_repo] = lock
        return lock

    def release_lock(self, lock):
        self._locks.pop(lock.org_repo, None)

    def lock_still_held(self, lock):
        current = self._locks.get(lock.org_repo)
        return current is not None and current.holder_id == lock.holder_id

    def acquire_run_lock(self, org_repo):
        if org_repo in self._run_locks:
            return None
        lock = Lock(
            org_repo=org_repo, holder_id="fake-run-holder", leased_until="9999-01-01T00:00:00"
        )
        self._run_locks[org_repo] = lock
        return lock

    def release_run_lock(self, lock):
        self._run_locks.pop(lock.org_repo, None)

    def load_model_route_status(self, job):
        return self._model_routes.get(job)

    def save_model_route_status(self, status):
        self._model_routes[status.job] = status


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
    # Wave 7b: github_generated_surface_audit is now a second, always-run
    # specialist -- unlike readme_reconciliation (which only ever touches the
    # local baseline clone, itself a local file:// path in these tests), its
    # classify step makes a real GitHub API call. Faked here so the entire
    # offline suite stays network-free, matching this project's own
    # `@pytest.mark.live` convention for anything that genuinely needs the
    # network.
    monkeypatch.setattr(audit_github_generated_surfaces, "repo_summary", _fake_repo_summary)
    monkeypatch.setattr(
        audit_github_generated_surfaces, "list_contributors", lambda org_repo, token: []
    )
    monkeypatch.setattr(
        audit_github_generated_surfaces, "list_languages", lambda org_repo, token: {"Java": 100}
    )
    # Wave 7c: package_release_audit is a third always-run specialist,
    # dispatching audit_package_release_surfaces (a real GitHub API call) and
    # the existing check_install_path (a real Maven Central resolution) --
    # both faked here for the same reason as 7b's mocks above.
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
    # Wave 7d: metadata_presentation is a fourth always-run specialist,
    # dispatching propose_metadata_changes (a real GitHub API call, distinct
    # from 7b's own `repo_summary` import) -- faked for the same reason.
    monkeypatch.setattr(
        propose_metadata_changes,
        "repo_summary",
        lambda org_repo, token: {
            "description": "An existing description",
            "homepage": "https://example.org",
            "topics": ["java"],
        },
    )
    # Wave 7e: community_files_presentation is a fifth always-run specialist,
    # dispatching audit_community_files -- its local clone+scan half runs for
    # real against the local file:// source (same as readme_reconciliation's
    # own local-only classify step, never faked), only its Community Profile
    # API half (a real GitHub network call) is faked here.
    monkeypatch.setattr(
        audit_community_files,
        "get_community_profile",
        lambda org_repo, token: {
            "health_percentage": 40,
            "files": {"license": {}, "contributing": None, "code_of_conduct": None},
        },
    )
    # Wave 7g: readme_presentation is a sixth (and seventh, counting cross_
    # surface_validation) always-run specialist -- the first whose render
    # step can reach the one real LLM call, faked for the same reason.
    monkeypatch.setattr(candidate_pipeline, "LiveLLMClient", _FakeLiveLLMClient)
    # Wave 8.6 (`VER-006` reversal): _verify_node now additionally dispatches
    # verify_prose_quality after a deterministic accept -- faked here (never
    # flagged) so this fixture's existing accept/commit assertions across
    # the whole file are unaffected.
    monkeypatch.setattr(
        verify_prose_quality, "LiveForcedToolClient", _FakeNonFlaggingForcedToolClient
    )
    # Wave 8.6 (comparison capability): presentation_benchmarking is a tenth
    # always-run specialist whose classify step can reach a real LLM
    # analysis call, faked for the same reason.
    monkeypatch.setattr(
        compare_against_presentation_standard, "LiveAnalysisClient", _FakeAnalysisClient
    )
    # Wave 8.6 (item H): visual_preparation's classify step is followed by
    # an additive, advisory-only vision-accuracy review, faked for the
    # same reason.
    monkeypatch.setattr(
        review_visual_asset_accuracy, "LiveAnalysisClient", _FakeVisualAccuracyAnalysisClient
    )
    # Wave 7h: visual_preparation is an eighth always-run specialist,
    # dispatching get_product_facts -- whose profiling path
    # (profile.cached.get_or_build_profile) takes a real GitHub-API branch
    # whenever env.gh_token() is truthy (SCL-004, decision #40/Part F).
    # Unlike 7b-7g's specialists above, this one was never faked here, so on
    # any machine with a real GH_TOKEN/GITHUB_PAT already set (routine for
    # anyone who has run this project's own live proofs) this "offline" test
    # silently took a real network branch against this fixture's fake
    # org_repo -- intermittently hanging at DNS/connect with no timeout
    # reached (found live, 2026-07-21, `OPS-010`). Same fix
    # `test_profile_cached.py` already established for the identical
    # problem: force the local-clone path.
    monkeypatch.setattr(cached.env, "gh_token", lambda: None)
    return tmp_path


class TestBasicLoop:
    def test_bootstrap_then_planner_capability_then_stop_converges(self, project):
        turns = [
            PlannerTurn(
                tool_call=_tool_call("c1", "detect_readme_gaps", {"org_repo": ORG_REPO}),
                meta=LLMResponseMeta(),
            ),
            PlannerTurn(content="done", meta=LLMResponseMeta()),
        ]
        result = supervise_repo(
            ORG_REPO, planner_client=FixturePlannerClient(turns), write_evidence_bundle=False
        )

        assert result.status == "CONVERGED_NO_CHANGE"
        capability_ids = [t.capability_id for t in result.task_graph.tasks.values()]
        assert "inspect_repository" in capability_ids  # the deterministic bootstrap
        assert "detect_readme_gaps" in capability_ids  # the planner's own choice
        assert all(t.state == "PASSED" for t in result.task_graph.tasks.values())

    def test_planner_calling_the_real_stop_capability_converges_without_dispatch(self, project):
        """TC-17 (decision #46, `AGT-006`): a planner calling the real,
        registered `stop` capability must end the run the same way an
        explicit no-tool-call turn does -- and must never reach the task
        graph as a dispatched task at all."""
        turns = [
            PlannerTurn(
                tool_call=_tool_call("c1", "stop", {"reason": "nothing left to investigate"}),
                meta=LLMResponseMeta(),
            ),
        ]
        result = supervise_repo(
            ORG_REPO, planner_client=FixturePlannerClient(turns), write_evidence_bundle=False
        )

        assert result.status == "CONVERGED_NO_CHANGE"
        capability_ids = [t.capability_id for t in result.task_graph.tasks.values()]
        assert "stop" not in capability_ids  # never dispatched as an ordinary task
        stop_decisions = [d for d in result.decisions if d.kind == "stop"]
        assert any("stop capability called" in d.detail for d in stop_decisions)

    def test_deterministic_backstop_ends_a_run_of_repeated_duplicate_calls_early(self, project):
        """TC-18 (Pillar A.2, decision #46's own rerun-consistency redesign):
        a planner that just keeps re-proposing an already-answered capability
        must not burn every remaining turn -- NO_PROGRESS_TURN_LIMIT
        consecutive SUPERSEDED (duplicate) turns ends the run deterministically,
        well short of DEFAULT_MAX_TURNS, without ever reaching repair_exhausted."""
        turns = [
            PlannerTurn(
                tool_call=_tool_call(f"c{i}", "detect_readme_gaps", {"org_repo": ORG_REPO}),
                meta=LLMResponseMeta(),
            )
            for i in range(1, 8)  # far more repeats than the backstop should ever consume
        ]
        result = supervise_repo(
            ORG_REPO, planner_client=FixturePlannerClient(turns), write_evidence_bundle=False
        )

        assert result.status in ("CONVERGED_NO_CHANGE", "CONVERGED_APPLIED")
        backstop_decisions = [
            d
            for d in result.decisions
            if d.kind == "stop" and "deterministic termination backstop" in d.detail
        ]
        assert len(backstop_decisions) == 1
        # Dispatched for real exactly once -- every further "call" was a
        # SUPERSEDED short-circuit, never re-executed against the capability.
        matching = [
            t for t in result.task_graph.tasks.values() if t.capability_id == "detect_readme_gaps"
        ]
        assert sum(1 for t in matching if t.state == "PASSED") == 1
        assert sum(1 for t in matching if t.state == "SUPERSEDED") == 3

    def test_deterministic_backstop_ends_a_run_of_repeated_unknown_capability_calls_early(
        self, project
    ):
        """Same backstop, the other no-forward-progress path: an unrecognized
        (hallucinated) capability name that keeps recurring is BLOCKED every
        time (never SUPERSEDED, since a rejected call never reaches PASSED)
        -- must still trip the same NO_PROGRESS_TURN_LIMIT counter rather than
        running all the way to DEFAULT_MAX_TURNS/repair_exhausted."""
        turns = [
            PlannerTurn(
                tool_call=_tool_call(f"c{i}", "totally_unknown_capability", {"org_repo": ORG_REPO}),
                meta=LLMResponseMeta(),
            )
            for i in range(1, 8)
        ]
        result = supervise_repo(
            ORG_REPO, planner_client=FixturePlannerClient(turns), write_evidence_bundle=False
        )

        # A capability gap alongside the passed bootstrap classifies as
        # PARTIAL_WITH_CAPABILITY_GAP, never BLOCKED: repair_exhausted -- the
        # exact outcome this backstop exists to prevent.
        assert result.status == "PARTIAL_WITH_CAPABILITY_GAP"
        backstop_decisions = [
            d
            for d in result.decisions
            if d.kind == "stop" and "deterministic termination backstop" in d.detail
        ]
        assert len(backstop_decisions) == 1
        dispatched = [
            t
            for t in result.task_graph.tasks.values()
            if t.capability_id == "totally_unknown_capability"
        ]
        assert len(dispatched) == 3  # NO_PROGRESS_TURN_LIMIT -- never all 7 offered turns

    def test_planner_never_consulted_when_it_would_only_repeat_itself(self, project):
        """SUPERSEDED dedup: asking for the same capability+arguments twice
        short-circuits instead of re-dispatching."""
        turns = [
            PlannerTurn(
                tool_call=_tool_call("c1", "inspect_repository", {"org_repo": ORG_REPO}),
                meta=LLMResponseMeta(),
            ),
            PlannerTurn(content="done", meta=LLMResponseMeta()),
        ]
        result = supervise_repo(
            ORG_REPO, planner_client=FixturePlannerClient(turns), write_evidence_bundle=False
        )
        superseded = [t for t in result.task_graph.tasks.values() if t.state == "SUPERSEDED"]
        assert len(superseded) == 1
        assert superseded[0].capability_id == "inspect_repository"


class TestOrgRepoTrustBoundary:
    def test_planner_supplied_org_repo_is_overridden_not_trusted(self, project):
        """`supervisor/loop.py`'s dispatch previously used `arguments.
        setdefault("org_repo", org_repo)`, which only fills in the trusted
        active repo when the planner's own tool-call JSON omits one entirely
        -- a planner-supplied org_repo (hallucination, injected content read
        from a repo, or a plain model mistake) would silently win instead.
        Proven here with the planner supplying an org_repo that isn't even a
        registered repo: if it were trusted, the dispatch would reject via
        NotAllowlistedError; the fix must instead always dispatch against the
        real, active ORG_REPO and pass."""
        turns = [
            PlannerTurn(
                tool_call=_tool_call(
                    "c1", "detect_readme_gaps", {"org_repo": "not-a-real-org/not-a-real-repo"}
                ),
                meta=LLMResponseMeta(),
            ),
            PlannerTurn(content="done", meta=LLMResponseMeta()),
        ]
        result = supervise_repo(
            ORG_REPO, planner_client=FixturePlannerClient(turns), write_evidence_bundle=False
        )

        gaps_tasks = [
            t for t in result.task_graph.tasks.values() if t.capability_id == "detect_readme_gaps"
        ]
        assert len(gaps_tasks) == 1
        assert gaps_tasks[0].arguments["org_repo"] == ORG_REPO
        assert gaps_tasks[0].state == "PASSED"


class TestCapabilityGap:
    def test_unknown_capability_gap_alongside_independent_passed_branch(self, project):
        """GAP-001's 'continue independent supported work' + GAP-002's exact
        literal status string, proven together against the real dispatcher."""
        turns = [
            PlannerTurn(
                tool_call=_tool_call("c1", "totally_unknown_capability", {"org_repo": ORG_REPO}),
                meta=LLMResponseMeta(),
            ),
            PlannerTurn(
                tool_call=_tool_call("c2", "detect_readme_gaps", {"org_repo": ORG_REPO}),
                meta=LLMResponseMeta(),
            ),
            PlannerTurn(content="done", meta=LLMResponseMeta()),
        ]
        result = supervise_repo(
            ORG_REPO, planner_client=FixturePlannerClient(turns), write_evidence_bundle=False
        )

        assert result.status == "PARTIAL_WITH_CAPABILITY_GAP"
        gap_tasks = [t for t in result.task_graph.tasks.values() if t.gap is not None]
        assert len(gap_tasks) == 1
        assert gap_tasks[0].state == "BLOCKED"
        passed = [t for t in result.task_graph.tasks.values() if t.state == "PASSED"]
        assert any(t.capability_id == "detect_readme_gaps" for t in passed)


class TestRepair:
    def test_execution_error_triggers_an_automatic_repair_that_recovers(self, project, monkeypatch):
        """ORC-002/VER-002: a repairable failure creates a repair task and
        the run still converges, without discarding the unrelated
        bootstrap's already-PASSED result."""
        real_executor = registry.get_executor("detect_readme_gaps")
        calls = {"n": 0}

        def flaky(org_repo):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("simulated transient failure")
            return real_executor(org_repo)

        monkeypatch.setitem(registry._EXECUTORS, "detect_readme_gaps", flaky)

        turns = [
            PlannerTurn(
                tool_call=_tool_call("c1", "detect_readme_gaps", {"org_repo": ORG_REPO}),
                meta=LLMResponseMeta(),
            ),
            PlannerTurn(content="done", meta=LLMResponseMeta()),
        ]
        result = supervise_repo(
            ORG_REPO, planner_client=FixturePlannerClient(turns), write_evidence_bundle=False
        )

        assert calls["n"] == 2  # the original attempt + exactly one auto-repair
        assert result.status == "CONVERGED_NO_CHANGE"
        assert any(t.state == "FAILED" for t in result.task_graph.tasks.values())
        assert any(
            t.state == "PASSED" and t.capability_id == "detect_readme_gaps"
            for t in result.task_graph.tasks.values()
        )
        repair_decisions = [d for d in result.decisions if d.kind == "repair"]
        assert len(repair_decisions) == 1


class TestDurableConvergence:
    def test_second_call_with_unchanged_upstream_converges_with_zero_planning_calls(self, project):
        """VER-003, proven against the real freshness check: a
        FixturePlannerClient seeded with zero turns would raise if `.plan()`
        were ever called -- the assertion is structural, not just
        behavioral. `write_evidence_bundle=True` here (unlike the other
        tests in this file) -- matches `orchestrator.py`'s own established
        contract that `write_evidence_bundle=False` means "no side effects
        at all," including no durable write-back (`validate_repo()`'s
        precedent), so the freshness check has nothing to read back from
        without it."""
        backend = FakeStateBackend()
        first = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert first.status == "CONVERGED_NO_CHANGE"

        class _RaisingPlanner:
            def plan(self, messages, tools):
                raise AssertionError("planner must not be consulted on an unchanged rerun")

        second = supervise_repo(
            ORG_REPO,
            planner_client=_RaisingPlanner(),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert second.status == "CONVERGED_NO_CHANGE"
        assert second.task_graph.tasks == {}  # no tasks even attempted


class TestSpecialistDrivenConvergence:
    """Wave 6 (decision #39): a second, registry-driven convergence tier
    ahead of the existing coarse commit-SHA check. The coarse check alone
    would force a full replan on ANY upstream commit, even one that touches
    nothing this tool tracks (README/LICENSE/community files)."""

    def test_upstream_commit_changes_but_tracked_content_unchanged_converges_without_planning(
        self, project
    ):
        backend = FakeStateBackend()
        first = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert first.status == "CONVERGED_NO_CHANGE"

        # An upstream commit that touches nothing the fingerprint tracks.
        source = project / "source"
        (source / "CHANGELOG.md").write_text("Unrelated changelog entry.\n", encoding="utf-8")
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "chore: unrelated"], cwd=source)

        class _RaisingPlanner:
            def plan(self, messages, tools):
                raise AssertionError("planner must not be consulted when nothing tracked changed")

        second = supervise_repo(
            ORG_REPO,
            planner_client=_RaisingPlanner(),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert second.status == "CONVERGED_NO_TRACKED_CHANGE"
        assert second.task_graph.tasks == {}  # no tasks even attempted

    def test_tracked_content_change_falls_through_to_full_planner_loop(self, project):
        backend = FakeStateBackend()
        first = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert first.status == "CONVERGED_NO_CHANGE"

        source = project / "source"
        (source / "README.md").write_text(
            "# Example FOSS for Java\n\nA new paragraph a maintainer added.\n", encoding="utf-8"
        )
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "docs: update"], cwd=source)

        second = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert second.status == "BLOCKED"
        assert second.blocked_reason is not None
        assert second.blocked_reason.startswith("specialist_failed:")
        # The bootstrap/planner loop actually ran this time, not short-circuited.
        assert "inspect_repository" in [t.capability_id for t in second.task_graph.tasks.values()]


class TestSpecialistSkipIntegration:
    """Wave 8.6 (`ORC-003` reversal): `enable_specialist_skip`/
    `specialist_selection_client` default fully off (every test above this
    class proves that implicitly, by never passing them) -- these tests
    exercise the opt-in path directly."""

    def test_a_skipped_domain_prevents_the_no_tracked_change_shortcut(self, project):
        """The crux correctness guarantee: an upstream commit that touches
        nothing any domain's own fingerprint tracks would normally converge
        via CONVERGED_NO_TRACKED_CHANGE with zero planning calls (see
        TestSpecialistDrivenConvergence's identical baseline scenario) -- but
        if one domain was SKIPPED rather than genuinely reclassified this
        run, that shortcut must not fire, even though every domain that DID
        run reports NO_CHANGE. Forces the full, safer planner loop instead."""
        backend = FakeStateBackend()
        first = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert first.status == "CONVERGED_NO_CHANGE"

        # An upstream commit that touches nothing any domain's own
        # fingerprint tracks -- same shape as TestSpecialistDrivenConvergence's
        # own baseline, so every domain that actually runs still reports
        # NO_CHANGE.
        source = project / "source"
        (source / "CHANGELOG.md").write_text("Unrelated changelog entry.\n", encoding="utf-8")
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "chore: unrelated"], cwd=source)

        skip_client = FixturePlannerClient(
            [
                PlannerTurn(
                    tool_call=_tool_call(
                        "call-1",
                        "select_specialists_to_skip",
                        {"skip_domains": ["visual_preparation"]},
                    ),
                    meta=LLMResponseMeta(),
                )
            ]
        )
        second = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
            enable_specialist_skip=True,
            specialist_selection_client=skip_client,
        )

        assert second.status != "CONVERGED_NO_TRACKED_CHANGE"
        state = backend.load(ORG_REPO)
        skipped = state.domain_states["visual_preparation"]
        assert skipped.skipped_this_run is True
        assert skipped.consecutive_skip_count == 1
        # The full planner loop actually ran -- proof this fell through,
        # not just a status-string coincidence.
        assert "inspect_repository" in [t.capability_id for t in second.task_graph.tasks.values()]

    def test_default_off_never_invokes_the_skip_decision(self, project):
        """`enable_specialist_skip=False` (the default) must mean
        `specialist_selection.decide_skips()` is never even called --
        proven structurally, not just by absence of a skip in the result."""
        backend = FakeStateBackend()
        first = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert first.status == "CONVERGED_NO_CHANGE"

        source = project / "source"
        (source / "CHANGELOG.md").write_text("Unrelated changelog entry.\n", encoding="utf-8")
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "chore: unrelated"], cwd=source)

        class _RaisingSelectionClient:
            def plan(self, messages, tools):
                raise AssertionError("decide_skips() must never be invoked when disabled")

        second = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
            # enable_specialist_skip left False (the default)
            specialist_selection_client=_RaisingSelectionClient(),
        )
        assert second.status == "CONVERGED_NO_TRACKED_CHANGE"
        state = backend.load(ORG_REPO)
        assert state.domain_states["visual_preparation"].skipped_this_run is False


class TestModelRouteDisablement:
    """Wave 8.6 (`OPS-011` extension): a disabled model route blocks the
    run outright, before any clone/specialist work, never a silent
    substitute-model fallback."""

    def test_disabled_route_blocks_before_any_work(self, project):
        backend = FakeStateBackend()
        backend.save_model_route_status(
            ModelRouteStatusV1(
                job="supervisor_planning",
                status="disabled",
                reason="golden-set pass-rate below threshold",
            )
        )

        class _RaisingPlanner:
            def plan(self, messages, tools):
                raise AssertionError("planner must not be consulted when the route is disabled")

        result = supervise_repo(ORG_REPO, planner_client=_RaisingPlanner(), state_backend=backend)

        assert result.status == "BLOCKED"
        assert result.blocked_reason == (
            "model_route_disabled:supervisor_planning:golden-set pass-rate below threshold"
        )

    def test_no_recorded_status_proceeds_normally(self, project):
        backend = FakeStateBackend()
        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
        )
        assert result.status == "CONVERGED_NO_CHANGE"

    def test_enabled_status_proceeds_normally(self, project):
        backend = FakeStateBackend()
        backend.save_model_route_status(
            ModelRouteStatusV1(job="supervisor_planning", status="enabled")
        )
        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
        )
        assert result.status == "CONVERGED_NO_CHANGE"


class TestNotOnboardedGate:
    """Wave 8.7: a registry entry missing ecosystem/policy_profile
    previously produced four different observable outcomes depending on
    which capability the planner happened to reach first -- three
    different raised exceptions plus a slow DEFAULT_MAX_TURNS-turn burn
    ending in BLOCKED/repair_exhausted. This is the one, fast, early gate
    that replaces all four for anything reached through supervise_repo() --
    proven here with zero clone and zero specialist dispatch, mirroring
    TestRunLockContention's own spy-assertion style."""

    def _rewrite_products_json(self, project, **overrides):
        products_path = project / "data" / "products.json"
        products = json.loads(products_path.read_text(encoding="utf-8"))
        products[0].update(overrides)
        products_path.write_text(json.dumps(products), encoding="utf-8")

    def test_missing_both_fields_blocks_before_any_clone_or_dispatch(self, project, monkeypatch):
        import readme_agent.specialists.registry as specialists_registry_module
        from readme_agent.supervisor import loop as loop_module

        self._rewrite_products_json(project, ecosystem=None, policy_profile=None)

        def _raising_clone_baseline(entry, baseline_path):
            raise AssertionError("clone_baseline must not be called for a not-onboarded entry")

        def _raising_run_domain(domain, org_repo, backend_arg, **kwargs):
            raise AssertionError(
                f"specialist {domain!r} must not be dispatched for a not-onboarded entry"
            )

        monkeypatch.setattr(loop_module, "clone_baseline", _raising_clone_baseline)
        monkeypatch.setattr(specialists_registry_module, "run_domain", _raising_run_domain)

        class _RaisingPlanner:
            def plan(self, messages, tools):
                raise AssertionError("planner must not be consulted for a not-onboarded entry")

        result = supervise_repo(
            ORG_REPO, planner_client=_RaisingPlanner(), write_evidence_bundle=False
        )

        assert result.status == "BLOCKED"
        assert result.blocked_reason == "not_onboarded"
        assert result.task_graph.tasks == {}

    def test_missing_ecosystem_only_still_blocks(self, project):
        self._rewrite_products_json(project, ecosystem=None)

        class _RaisingPlanner:
            def plan(self, messages, tools):
                raise AssertionError("planner must not be consulted")

        result = supervise_repo(
            ORG_REPO, planner_client=_RaisingPlanner(), write_evidence_bundle=False
        )
        assert result.status == "BLOCKED"
        assert result.blocked_reason == "not_onboarded"

    def test_missing_policy_profile_only_still_blocks(self, project):
        self._rewrite_products_json(project, policy_profile=None)

        class _RaisingPlanner:
            def plan(self, messages, tools):
                raise AssertionError("planner must not be consulted")

        result = supervise_repo(
            ORG_REPO, planner_client=_RaisingPlanner(), write_evidence_bundle=False
        )
        assert result.status == "BLOCKED"
        assert result.blocked_reason == "not_onboarded"

    def test_unregistered_rust_ecosystem_is_explicitly_unsupported(self, project):
        self._rewrite_products_json(
            project,
            platform="rust",
            ecosystem=None,
            policy_profile=None,
        )

        result = supervise_repo(ORG_REPO, write_evidence_bundle=False)

        assert result.status == "BLOCKED"
        assert result.blocked_reason == "unsupported_ecosystem:rust"
        assert result.decisions[0].kind == "capability_gap"

    def test_fully_onboarded_entry_is_unaffected_by_the_new_gate(self, project):
        """Control case: the project fixture's default entry (ecosystem=
        "java", policy_profile="test-profile", matching the 3 real onboarded
        pilots' shape) must pass straight through the new check unchanged."""
        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            write_evidence_bundle=False,
        )
        assert result.status != "BLOCKED"


class TestBaselineCloneFailureDegradesGracefully:
    """SCL-004 extension (2026-07-22): before this fix, a `GitSafetyError`
    from `clone_baseline()` (e.g. a 15.5k-file repo timing out against the
    previous hardcoded 300s) propagated uncaught out of `supervise_repo()`,
    through `cmd_supervise()`, to the CLI's bare `error: ...` print and exit
    3 -- no `SuperviseResult`, no evidence bundle, nothing for a portfolio
    pass or a human to inspect afterward. Proven here with a real onboarded
    entry (ecosystem/policy_profile set) so the not-onboarded gate above
    doesn't short-circuit before the clone is ever reached."""

    def test_clone_failure_returns_blocked_with_evidence_instead_of_raising(
        self, project, monkeypatch
    ):
        from readme_agent.errors import GitSafetyError
        from readme_agent.supervisor import loop as loop_module

        def _raising_clone_baseline(entry, baseline_path):
            raise GitSafetyError(f"baseline clone of {entry.org_repo} failed: timed out after 600s")

        monkeypatch.setattr(loop_module, "clone_baseline", _raising_clone_baseline)

        class _RaisingPlanner:
            def plan(self, messages, tools):
                raise AssertionError("planner must not be consulted after a clone failure")

        result = supervise_repo(ORG_REPO, planner_client=_RaisingPlanner())

        assert result.status == "BLOCKED"
        assert result.blocked_reason is not None
        assert "baseline_clone_failed" in result.blocked_reason
        assert "timed out after 600s" in result.blocked_reason
        assert result.evidence_dir is not None
        assert (result.evidence_dir / "manifest.json").exists()
        assert (result.evidence_dir / "decisions.json").exists()
        decisions = json.loads((result.evidence_dir / "decisions.json").read_text(encoding="utf-8"))
        assert decisions[0]["kind"] == "baseline_clone_failed"

    def test_clone_failure_with_evidence_disabled_still_returns_blocked(self, project, monkeypatch):
        from readme_agent.errors import GitSafetyError
        from readme_agent.supervisor import loop as loop_module

        monkeypatch.setattr(
            loop_module,
            "clone_baseline",
            lambda entry, baseline_path: (_ for _ in ()).throw(GitSafetyError("boom")),
        )

        result = supervise_repo(ORG_REPO, write_evidence_bundle=False)

        assert result.status == "BLOCKED"
        assert result.evidence_dir is None


class TestMultiDomainCoexistence:
    """`MEM-004`/`CAP-006`, live-proven for the first time with a genuine
    second domain (Wave 7b): two specialists writing their own accepted
    result into the same `RunStateV1.domain_states` record, in the same
    run, must never collide or clobber each other -- previously only ever
    exercised with one real domain."""

    def test_all_domains_land_in_the_same_run_without_collision(self, project):
        backend = FakeStateBackend()
        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert result.status == "CONVERGED_NO_CHANGE"

        state = backend.load(ORG_REPO)
        assert state is not None
        assert set(state.domain_states) == {
            "readme_reconciliation",
            "github_generated_surface_audit",
            "package_release_audit",
            "metadata_presentation",
            "community_files_presentation",
            "cross_surface_validation",
            "readme_presentation",
            "visual_preparation",
            "presentation_benchmarking",
            "independent_verification",
        }
        assert state.domain_states["readme_reconciliation"].accepted_status == "FIRST_OBSERVATION"
        assert (
            state.domain_states["github_generated_surface_audit"].accepted_status
            == "FIRST_OBSERVATION"
        )
        assert state.domain_states["package_release_audit"].accepted_status == "FIRST_OBSERVATION"
        assert state.domain_states["metadata_presentation"].accepted_status == "FIRST_OBSERVATION"
        assert (
            state.domain_states["community_files_presentation"].accepted_status
            == "FIRST_OBSERVATION"
        )
        assert (
            state.domain_states["cross_surface_validation"].accepted_status == "FIRST_OBSERVATION"
        )
        assert state.domain_states["readme_presentation"].accepted_status == "FIRST_OBSERVATION"
        # mode: "dry_run" in this fixture -- written locally (a real gap
        # exists), never committed, regardless of render/validation outcome.
        assert state.domain_states["readme_presentation"].details["written"] is True
        assert state.domain_states["readme_presentation"].details["committed"] is False
        assert state.domain_states["visual_preparation"].accepted_status == "FIRST_OBSERVATION"
        # No image asset exists in this fixture repo -- a real candidate is
        # prepared, never written anywhere.
        assert state.domain_states["visual_preparation"].details["existing_asset_found"] is False
        assert (
            state.domain_states["visual_preparation"].details["prepared_candidate"]["filename"]
            == "banner.png"
        )
        # The audit's actual snapshot lives in `details`, not just the verdict.
        assert state.domain_states["github_generated_surface_audit"].details[
            "primary_language"
        ] == ("Java")
        assert state.domain_states["package_release_audit"].details["releases_count"] == 0
        # Existing description/homepage/topics -- no proposal needed for any of them.
        assert state.domain_states["metadata_presentation"].details["has_proposal"] is False
        assert (
            state.domain_states["community_files_presentation"].details["present_files"]["LICENSE"]
            is True
        )
        # No inconsistency: the fixture README never mentions a license at
        # all (license_claim is None), so nothing is compared against the
        # LICENSE file's own "MIT" classification.
        assert state.domain_states["cross_surface_validation"].details["inconsistencies"] == []

    def test_second_run_all_domains_independently_report_no_change(self, project):
        backend = FakeStateBackend()
        supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )

        source = project / "source"
        (source / "CHANGELOG.md").write_text("Unrelated changelog entry.\n", encoding="utf-8")
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "chore: unrelated"], cwd=source)

        second = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient([]),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert second.status == "CONVERGED_NO_TRACKED_CHANGE"

        state = backend.load(ORG_REPO)
        assert state.domain_states["readme_reconciliation"].accepted_status == "NO_CHANGE"
        assert state.domain_states["github_generated_surface_audit"].accepted_status == "NO_CHANGE"
        assert state.domain_states["package_release_audit"].accepted_status == "NO_CHANGE"
        assert state.domain_states["metadata_presentation"].accepted_status == "NO_CHANGE"
        assert state.domain_states["community_files_presentation"].accepted_status == "NO_CHANGE"
        assert state.domain_states["cross_surface_validation"].accepted_status == "NO_CHANGE"
        assert state.domain_states["readme_presentation"].accepted_status == "NO_CHANGE"
        assert state.domain_states["visual_preparation"].accepted_status == "NO_CHANGE"


class TestSpecialistResultsEvidence:
    """Wave 7 fix: before this, a specialist's findings were only ever
    visible embedded in the LLM's own conversation content on the full-loop
    path, and not recorded as evidence at all on the CONVERGED_NO_TRACKED_
    CHANGE shortcut path (which didn't even generate an evidence_dir).
    `specialist_results.json` must exist and be populated on both paths."""

    def test_specialist_results_json_written_on_the_shortcut_path(self, project):
        backend = FakeStateBackend()
        first = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert first.status == "CONVERGED_NO_CHANGE"

        source = project / "source"
        (source / "CHANGELOG.md").write_text("Unrelated changelog entry.\n", encoding="utf-8")
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "chore: unrelated"], cwd=source)

        second = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient([]),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert second.status == "CONVERGED_NO_TRACKED_CHANGE"
        assert second.evidence_dir is not None

        payload = json.loads((second.evidence_dir / "specialist_results.json").read_text())
        assert payload["readme_reconciliation"]["accepted_status"] == "NO_CHANGE"
        assert "details" in payload["readme_reconciliation"]

    def test_specialist_results_json_written_on_the_full_loop_path(self, project):
        backend = FakeStateBackend()
        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert result.status == "CONVERGED_NO_CHANGE"
        assert result.evidence_dir is not None

        payload = json.loads((result.evidence_dir / "specialist_results.json").read_text())
        assert payload["readme_reconciliation"]["accepted_status"] == "FIRST_OBSERVATION"


class TestRunManifestV2Evidence:
    """Wave 13.1 (`EVID-001`): `manifest.json` is now a typed `RunManifestV2`
    -- proven here with real, non-`None` values on the full-loop path,
    which has the richest context available."""

    def test_manifest_json_carries_the_new_run_manifest_v2_fields(self, project):
        backend = FakeStateBackend()
        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert result.status == "CONVERGED_NO_CHANGE"
        assert result.evidence_dir is not None

        manifest = json.loads((result.evidence_dir / "manifest.json").read_text())
        assert manifest["run_id"]
        assert manifest["org_repo"] == ORG_REPO
        assert manifest["control_plane_fingerprint"]  # a real, non-empty hash
        assert manifest["upstream_revision"]  # a real commit SHA
        assert manifest["prompt_registry_content_hash"]
        assert isinstance(manifest["surface_freshness"], dict)
        # Not yet threaded through this path -- explicit null, not faked.
        assert manifest["authorization_record_id"] is None
        assert manifest["trigger_dedup_key"] is None

    def test_requirement_ids_exercised_reflects_independent_verifications_own_map(self, project):
        backend = FakeStateBackend()
        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert result.status == "CONVERGED_NO_CHANGE"
        assert result.evidence_dir is not None

        manifest = json.loads((result.evidence_dir / "manifest.json").read_text())
        specialist_results = json.loads(
            (result.evidence_dir / "specialist_results.json").read_text()
        )
        expected = specialist_results["independent_verification"]["details"]["requirement_map"]
        assert manifest["requirement_ids_exercised"] == {
            requirement_id: info["exercised_without_error"]
            for requirement_id, info in expected.items()
        }
        assert len(manifest["requirement_ids_exercised"]) > 0


class TestEvidenceCompletenessGate:
    """Wave 8d: the run-level meaning of "evidence completeness gates" --
    all four evidence files must exist and be valid JSON before
    `supervise_repo()` returns, on both the shortcut and full-loop paths."""

    def test_all_four_files_present_on_the_full_loop_path(self, project):
        backend = FakeStateBackend()
        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert result.evidence_dir is not None
        for name in (
            "specialist_results.json",
            "task_graph.json",
            "decisions.json",
            "manifest.json",
        ):
            path = result.evidence_dir / name
            assert path.exists()
            json.loads(path.read_text())  # must parse -- structural completeness

    def test_all_four_files_present_on_the_shortcut_path(self, project):
        backend = FakeStateBackend()
        supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        source = project / "source"
        (source / "CHANGELOG.md").write_text("Unrelated changelog entry.\n", encoding="utf-8")
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "chore: unrelated"], cwd=source)

        second = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient([]),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert second.status == "CONVERGED_NO_TRACKED_CHANGE"
        assert second.evidence_dir is not None
        for name in (
            "specialist_results.json",
            "task_graph.json",
            "decisions.json",
            "manifest.json",
        ):
            path = second.evidence_dir / name
            assert path.exists()
            json.loads(path.read_text())

    def test_assert_evidence_complete_raises_on_a_missing_file(self, tmp_path):
        from readme_agent.supervisor.evidence import assert_evidence_complete

        (tmp_path / "specialist_results.json").write_text("{}", encoding="utf-8")
        (tmp_path / "task_graph.json").write_text("{}", encoding="utf-8")
        (tmp_path / "decisions.json").write_text("[]", encoding="utf-8")
        # manifest.json deliberately never written.

        with pytest.raises(RuntimeError, match="manifest.json"):
            assert_evidence_complete(tmp_path)

    def test_assert_evidence_complete_raises_on_invalid_json(self, tmp_path):
        from readme_agent.supervisor.evidence import assert_evidence_complete

        (tmp_path / "specialist_results.json").write_text("{}", encoding="utf-8")
        (tmp_path / "task_graph.json").write_text("{}", encoding="utf-8")
        (tmp_path / "decisions.json").write_text("[]", encoding="utf-8")
        (tmp_path / "manifest.json").write_text("not valid json", encoding="utf-8")

        with pytest.raises(RuntimeError, match="manifest.json"):
            assert_evidence_complete(tmp_path)


class TestEscalationAlert:
    """Wave 8d (`VER-002`/"repair loops"): a domain crossing the failure-
    escalation threshold gets a distinct, visible signal in `decisions`,
    read from `independent_verification`'s own audit (Wave 8c)."""

    def test_escalation_alert_appears_when_threshold_is_crossed(self, project):
        backend = FakeStateBackend()
        # Seed a sibling already at the escalation threshold, so
        # independent_verification's own audit surfaces it on this run.
        backend._states[ORG_REPO] = RunStateV1(
            org_repo=ORG_REPO,
            domain_states={
                "readme_reconciliation": DomainStateV1(
                    domain="readme_reconciliation",
                    accepted_status="ERROR:execution_error:boom",
                    consecutive_failure_count=3,
                    last_failure_reason="execution_error",
                )
            },
        )

        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=False,
        )

        alerts = [d for d in result.decisions if d.kind == "escalation_alert"]
        assert len(alerts) == 1
        assert "readme_reconciliation" in alerts[0].detail
        assert "3" in alerts[0].detail

    def test_no_escalation_alert_below_threshold(self, project):
        backend = FakeStateBackend()
        backend._states[ORG_REPO] = RunStateV1(
            org_repo=ORG_REPO,
            domain_states={
                "readme_reconciliation": DomainStateV1(
                    domain="readme_reconciliation",
                    accepted_status="ERROR:execution_error:boom",
                    consecutive_failure_count=1,
                    last_failure_reason="execution_error",
                )
            },
        )

        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=False,
        )

        assert [d for d in result.decisions if d.kind == "escalation_alert"] == []


class TestSpecialistFailureIsolation:
    """Wave 7 root-cause fix: an unhandled exception in one specialist must
    not abort the whole `supervise_repo()` call. Before this fix,
    `supervisor/loop.py:227-232`'s `for domain in specialist_domains` had no
    try/except -- with only one specialist ever registered, this was latent;
    Wave 7 registering six more makes it a real risk."""

    def test_a_raising_specialist_does_not_abort_the_run(self, project, monkeypatch):
        def _raising_run_domain(domain, org_repo, backend):
            raise RuntimeError("simulated network timeout inside a specialist")

        monkeypatch.setattr(specialists_registry, "run_domain", _raising_run_domain)

        backend = FakeStateBackend()
        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        # The run completes -- it does not propagate the specialist's
        # exception -- but it must not misreport that failure as convergence.
        assert result.status == "BLOCKED"
        assert result.blocked_reason is not None
        assert result.blocked_reason.startswith("specialist_failed:")

    def test_a_raising_specialists_error_never_looks_like_no_change_to_the_shortcut(
        self, project, monkeypatch
    ):
        """An `ERROR`-status domain must fail the `all(status == "NO_CHANGE")`
        convergence-shortcut check, forcing the real bootstrap/planner loop
        to run -- an errored specialist silently masquerading as a converged,
        nothing-to-do repo would be a much worse failure mode than the crash
        this fix already prevents."""

        def _raising_run_domain(domain, org_repo, backend):
            raise RuntimeError("simulated failure")

        monkeypatch.setattr(specialists_registry, "run_domain", _raising_run_domain)
        backend = FakeStateBackend()

        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )

        assert result.status != "CONVERGED_NO_TRACKED_CHANGE"
        assert result.status == "BLOCKED"
        assert result.blocked_reason is not None
        assert result.blocked_reason.startswith("specialist_failed:")
        # The bootstrap dispatch only happens past the shortcut -- direct
        # proof the full loop ran rather than short-circuiting.
        assert "inspect_repository" in [t.capability_id for t in result.task_graph.tasks.values()]


class TestDomainCoverageTracking:
    """`VER-005` (found live, Wave 8e full-registry pass, 2026-07-21): a
    domain that crashes before its own record node ever runs must still be
    durably recorded (via the `SupervisorStateV1` write's own enriched
    payload, `merge_unrecorded_failures()`), and the coarse `is_fresh()`
    shortcut must not trust an incomplete-coverage prior run as converged."""

    def test_a_crashing_domain_is_durably_recorded_with_the_error_colon_convention(
        self, project, monkeypatch
    ):
        """Direct regression test for the placeholder-string bug the
        adversarial review caught before it shipped: a bare `"ERROR"` (no
        colon) fails `record_failure_or_reset()`'s own `is_error` check,
        silently treating a genuine crash as a successful accept."""
        real_run_domain = specialists_registry.run_domain

        def _raise_for_one_domain(domain, org_repo, backend):
            if domain == "readme_reconciliation":
                raise RuntimeError("simulated crash for readme_reconciliation only")
            return real_run_domain(domain, org_repo, backend)

        monkeypatch.setattr(specialists_registry, "run_domain", _raise_for_one_domain)
        backend = FakeStateBackend()

        supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )

        stored = backend.load(ORG_REPO).domain_states["readme_reconciliation"]
        # No prior good baseline existed -- `accepted_status` correctly
        # stays `None` (the same "never persist a bad baseline" guarantee
        # `save_domain_with_failure_tracking()` already has), never the raw
        # crash placeholder mistaken for an accepted value. The colon
        # convention shows up in what it *does* correctly classify:
        assert stored.accepted_status is None
        assert stored.last_failure_reason == "execution_error"
        assert stored.consecutive_failure_count == 1  # a real crash, not non-escalating

        # The bug this regression test exists for: had the placeholder
        # stayed a bare "ERROR" (no colon), `is_error` would have evaluated
        # `False`, and this crash would have been recorded as a clean
        # accept instead -- confirm that did NOT happen.
        assert stored.accepted_status != "ERROR"

    def test_domain_coverage_complete_gates_the_coarse_shortcut(self, project):
        """The exact gap this fix closes: a fully healthy run must record
        `domain_coverage_complete=True`, but a stale/incomplete record (the
        shape a record written before this field existed, or one left by a
        crash mid-loop that never reached `_record_supervisor_state()` at
        all, would have) must force one real run rather than being trusted
        -- proven directly against the durable record, not by re-deriving
        `is_fresh()`'s own already-unit-tested logic here."""
        backend = FakeStateBackend()
        first = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert first.status == "CONVERGED_NO_CHANGE"
        stored = backend.load(ORG_REPO)
        assert stored.supervisor_state.domain_coverage_complete is True

        # Simulate the shape of a stale/never-completed record directly,
        # rather than fighting this fix's own same-run fold-in (which
        # already closes the "specialist crashes, loop.py's own except-
        # block catches it" case within a single run -- this test targets
        # the *durable record*, not that already-covered mechanism).
        corrupted = stored.model_copy(
            update={
                "supervisor_state": stored.supervisor_state.model_copy(
                    update={"domain_coverage_complete": None}
                )
            }
        )
        backend._states[ORG_REPO] = corrupted

        second = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        # The coarse `is_fresh()` shortcut must NOT have fired -- proven by
        # the *status*, not by "inspect_repository ran": upstream is
        # genuinely unchanged here, so once is_fresh() is correctly bypassed
        # and the specialist tier actually runs, every domain legitimately
        # reports NO_CHANGE, correctly hitting Wave 6's own separate,
        # finer-grained `CONVERGED_NO_TRACKED_CHANGE` shortcut instead (a
        # real, distinct convergence tier, not this fix's own bug). Had the
        # coarse shortcut incorrectly fired despite the corrupted record,
        # the status would be `CONVERGED_NO_CHANGE` (zero specialist
        # dispatch) instead.
        assert second.status == "CONVERGED_NO_TRACKED_CHANGE"

        # Self-heals: coverage is complete again after that real run, so a
        # third, genuinely unchanged call must finally hit the fast path --
        # this must not force a full run forever.
        class _RaisingPlanner:
            def plan(self, messages, tools):
                raise AssertionError("planner must not be consulted once coverage is complete")

        third = supervise_repo(
            ORG_REPO,
            planner_client=_RaisingPlanner(),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert third.status == "CONVERGED_NO_CHANGE"


class TestLockContention:
    def test_lock_already_held_is_blocked_not_silently_ignored(self, project):
        backend = FakeStateBackend()
        held_lock = backend.acquire_lock(ORG_REPO)
        assert held_lock is not None

        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient([]),
            state_backend=backend,
            write_evidence_bundle=False,
        )
        assert result.status == "BLOCKED"
        assert result.blocked_reason == "lock_held"


class TestRunLockContention:
    """Wave 8.5 (`SCL-005` extension): the corrected two-lock-ref fix -- the
    run-lock is acquired BEFORE the specialist tier starts, closing the
    lock-race where two concurrent supervise_repo() calls for the same repo
    could both pay for the full specialist tier before either was rejected."""

    def test_run_lock_already_held_blocks_before_any_specialist_dispatch(
        self, project, monkeypatch
    ):
        import readme_agent.specialists.registry as specialists_registry_module

        backend = FakeStateBackend()
        held_run_lock = backend.acquire_run_lock(ORG_REPO)
        assert held_run_lock is not None

        def _raising_run_domain(domain, org_repo, backend_arg):
            raise AssertionError(
                f"specialist {domain!r} must not be dispatched while the run-lock is held"
            )

        monkeypatch.setattr(specialists_registry_module, "run_domain", _raising_run_domain)

        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient([]),
            state_backend=backend,
            write_evidence_bundle=False,
        )
        assert result.status == "BLOCKED"
        assert result.blocked_reason == "run_lock_held"

    def test_run_lock_is_released_after_converged_no_tracked_change(self, project):
        backend = FakeStateBackend()
        first = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert first.status == "CONVERGED_NO_CHANGE"

        source = project / "source"
        (source / "CHANGELOG.md").write_text("Unrelated changelog entry.\n", encoding="utf-8")
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "chore: unrelated"], cwd=source)

        class _RaisingPlanner:
            def plan(self, messages, tools):
                raise AssertionError("planner must not be consulted when nothing tracked changed")

        second = supervise_repo(
            ORG_REPO,
            planner_client=_RaisingPlanner(),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert second.status == "CONVERGED_NO_TRACKED_CHANGE"

        # The exact regression an earlier adversarial review caught: a naive
        # widening of the run-lock's try/finally that covered only the
        # specialist tier's normal completion path -- not this shortcut
        # return -- would leak the run-lock for its full ~900s lease here.
        reacquired = backend.acquire_run_lock(ORG_REPO)
        assert reacquired is not None

    def test_first_freshness_shortcut_acquires_zero_locks(self, project):
        backend = FakeStateBackend()
        first = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert first.status == "CONVERGED_NO_CHANGE"

        call_counts = {"acquire_lock": 0, "acquire_run_lock": 0}
        original_acquire_lock = backend.acquire_lock
        original_acquire_run_lock = backend.acquire_run_lock

        def _counting_acquire_lock(org_repo):
            call_counts["acquire_lock"] += 1
            return original_acquire_lock(org_repo)

        def _counting_acquire_run_lock(org_repo):
            call_counts["acquire_run_lock"] += 1
            return original_acquire_run_lock(org_repo)

        backend.acquire_lock = _counting_acquire_lock
        backend.acquire_run_lock = _counting_acquire_run_lock

        class _RaisingPlanner:
            def plan(self, messages, tools):
                raise AssertionError("planner must not be consulted on an unchanged rerun")

        second = supervise_repo(
            ORG_REPO,
            planner_client=_RaisingPlanner(),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert second.status == "CONVERGED_NO_CHANGE"
        assert call_counts == {"acquire_lock": 0, "acquire_run_lock": 0}


class TestLockReleaseFailureDoesNotDiscardResult:
    """Found live, 2026-07-22: `release_lock()`/`release_run_lock()` raising
    inside `supervise_repo()`'s own `finally:` blocks (a real, non-stale-lease
    push failure -- e.g. a hung git subprocess, a transient network error)
    used to replace whatever `return SuperviseResult(...)` the `try` block
    was already returning, per Python's finally-discards-pending-return
    semantics -- silently losing a fully successful run's result (evidence
    bundle already written to disk) and surfacing only as an unrelated crash.
    These tests prove the fix: a release failure is caught and logged, and
    the run's actual result still comes back intact."""

    def test_release_lock_failure_does_not_discard_a_successful_result(self, project, capsys):
        backend = FakeStateBackend()
        real_release_lock = backend.release_lock

        def _raising_release_lock(lock):
            # `release_lock` is used both by supervise_repo()'s own top-level
            # per-op lock AND internally by every specialist's save_domain()
            # call -- performing the real release first (not just raising)
            # keeps the fake's tracking state consistent across the whole
            # run, isolating this test to the one thing it means to prove:
            # a release failure is caught and logged, never left unhandled.
            real_release_lock(lock)
            raise RuntimeError("push of the per-op lock ref failed: connection reset")

        backend.release_lock = _raising_release_lock

        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )

        assert result.status == "CONVERGED_NO_CHANGE"
        assert "warning: releasing lock" in capsys.readouterr().err

    def test_release_run_lock_failure_does_not_discard_a_successful_result(self, project, capsys):
        backend = FakeStateBackend()

        def _raising_release_run_lock(lock):
            raise RuntimeError("push of the run-lock ref failed: connection reset")

        backend.release_run_lock = _raising_release_run_lock

        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )

        assert result.status == "CONVERGED_NO_CHANGE"
        assert "warning: releasing run-lock" in capsys.readouterr().err


class TestPreCloneShortcut:
    """Wave 8.5 (`ORC-006`): a cheap pre-clone SHA probe short-circuits to
    CONVERGED_NO_CHANGE before clone_baseline() ever runs, for the common
    "scheduled run, nothing changed upstream" case -- eliminating 100% of
    the clone cost for that case, not just the specialist-tier cost the
    existing post-clone shortcut already avoided."""

    def test_matching_probe_skips_the_clone_entirely(self, project, monkeypatch):
        import readme_agent.supervisor.loop as loop_module

        backend = FakeStateBackend()
        first = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(
                [PlannerTurn(content="done", meta=LLMResponseMeta())]
            ),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert first.status == "CONVERGED_NO_CHANGE"

        clone_calls: list[str] = []
        original_clone_baseline = loop_module.clone_baseline

        def _counting_clone_baseline(entry, baseline_path):
            clone_calls.append(entry.org_repo)
            return original_clone_baseline(entry, baseline_path)

        monkeypatch.setattr(loop_module, "clone_baseline", _counting_clone_baseline)

        class _RaisingPlanner:
            def plan(self, messages, tools):
                raise AssertionError(
                    "planner must not be consulted when the pre-clone probe already matches"
                )

        second = supervise_repo(
            ORG_REPO,
            planner_client=_RaisingPlanner(),
            state_backend=backend,
            write_evidence_bundle=True,
        )
        assert second.status == "CONVERGED_NO_CHANGE"
        assert clone_calls == []  # the pre-clone probe already matched -- zero clones

        # Wave 8.7 (Item N): found live, 2026-07-22, that this shortcut wrote
        # no evidence at all (only a console line) -- a human debugging
        # months later could not tell this cheapest path fired versus the
        # run never happening. Now it writes a real, minimal bundle with a
        # distinguishing decision kind.
        assert second.evidence_dir is not None
        assert second.evidence_dir.exists()
        for name in (
            "manifest.json",
            "decisions.json",
            "task_graph.json",
            "specialist_results.json",
        ):
            assert (second.evidence_dir / name).exists()
        assert any(d.kind == "sha_probe_shortcut" for d in second.decisions)


class TestTokenBudget:
    """AGT-008/Wave 8.5: a defensive circuit breaker on the planner's own
    conversation size, tracked off the gateway's own reported usage.
    `detect_readme_gaps` (not `inspect_repository`) is used as the planner's
    own tool call in these tests -- the bootstrap task already dispatches
    `inspect_repository`, so a planner turn repeating it would hit the
    SUPERSEDED dedup path and never reach the post-dispatch token-budget
    check this class is testing."""

    def test_exceeding_the_budget_blocks_the_run(self, project):
        turns = [
            PlannerTurn(
                tool_call=_tool_call("c1", "detect_readme_gaps", {"org_repo": ORG_REPO}),
                meta=LLMResponseMeta(usage=Usage(prompt_tokens=30_000)),
            ),
        ]
        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(turns),
            write_evidence_bundle=False,
        )
        assert result.status == "BLOCKED"
        assert result.blocked_reason is not None
        assert result.blocked_reason.startswith("dossier_token_budget_exceeded")

    def test_missing_usage_never_trips_the_breaker_or_crashes(self, project):
        turns = [
            PlannerTurn(
                tool_call=_tool_call("c1", "detect_readme_gaps", {"org_repo": ORG_REPO}),
                meta=LLMResponseMeta(),  # usage=None, the default -- must not crash
            ),
            PlannerTurn(content="done", meta=LLMResponseMeta()),
        ]
        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(turns),
            write_evidence_bundle=False,
        )
        assert result.status == "CONVERGED_NO_CHANGE"


class TestPlannerFailureEvidence:
    """Wave 8.5 (D3): an uncaught planner-LLM failure used to propagate
    straight out of supervise_repo(), past the evidence-writing code --
    both locks still released correctly (both are in `finally`), but zero
    evidence was ever written for that attempt."""

    def test_planner_llm_failure_still_writes_a_complete_evidence_bundle(self, project):
        class _RaisingPlannerClient:
            def plan(self, messages, tools):
                raise LLMError("simulated gateway failure")

        result = supervise_repo(
            ORG_REPO,
            planner_client=_RaisingPlannerClient(),
            write_evidence_bundle=True,
        )
        assert result.status == "BLOCKED"
        assert result.blocked_reason is not None
        assert result.blocked_reason.startswith("planner_llm_failure")
        assert result.evidence_dir is not None
        for name in (
            "specialist_results.json",
            "task_graph.json",
            "decisions.json",
            "manifest.json",
        ):
            assert (result.evidence_dir / name).exists()


class TestMaxTurns:
    def test_a_planner_that_never_stops_is_blocked_as_repair_exhausted_not_silently_capped(
        self, project
    ):
        """AGT-004: the bound fires as a labeled BLOCKED reason, not a
        silent stop -- and it takes real, distinct proposals to reach it
        (SUPERSEDED dedup would otherwise short-circuit a naive repeat)."""
        capability_ids = [
            "inspect_repository",
            "detect_readme_gaps",
            "check_install_path",
            "profile_repository",
        ]
        turns = [
            PlannerTurn(
                tool_call=_tool_call(
                    f"c{i}",
                    capability_ids[i % len(capability_ids)] + "_never_matches",
                    {"org_repo": ORG_REPO},
                ),
                meta=LLMResponseMeta(),
            )
            for i in range(20)
        ]
        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient(turns),
            write_evidence_bundle=False,
            max_turns=3,
        )
        assert result.status == "BLOCKED"

    def test_known_specialist_failure_precedes_repair_exhaustion(self, project, monkeypatch):
        from readme_agent.supervisor import loop
        from readme_agent.supervisor.specialist_tier import SpecialistTierResult

        specialist_error = DomainStateV1(
            domain="readme_presentation",
            accepted_status="ERROR:verification_rejected:controlled",
        )
        monkeypatch.setattr(
            loop,
            "run_specialist_tier",
            lambda **kwargs: SpecialistTierResult(
                domains=["readme_presentation"],
                results={"readme_presentation": specialist_error},
                unrecorded_failures={},
                escalation_alerts=[],
                retry_alerts=[],
            ),
        )

        result = supervise_repo(
            ORG_REPO,
            planner_client=FixturePlannerClient([]),
            write_evidence_bundle=False,
            max_turns=1,
        )

        assert result.status == "BLOCKED"
        assert result.blocked_reason == (
            "specialist_failed:readme_presentation:ERROR:verification_rejected:controlled"
        )


class TestWriteCapableModeGate:
    """Decision #40's safety companion: supervise_repo()'s entry gate moved
    to require_listed() (mode is irrelevant for reads), so it no longer
    implies mode == "full" the way require_permitted() used to.
    dispatch_and_record() is the one place left that must still refuse to
    dispatch a local_write/remote_write capability against a repo whose push
    access hasn't been verified -- proven directly here since no real
    write-capable capability is registered yet to exercise it end to end."""

    def test_write_capable_capability_blocked_when_mode_not_full(self, project, monkeypatch):
        from readme_agent.capabilities.schema import CapabilityManifest
        from readme_agent.supervisor.action_dispatch import dispatch_and_record
        from readme_agent.supervisor.task import Task, TaskGraph

        products_path = project / "data" / "products.json"
        products = json.loads(products_path.read_text(encoding="utf-8"))
        products[0]["mode"] = "disabled"
        products_path.write_text(json.dumps(products), encoding="utf-8")

        fake_manifest = CapabilityManifest(
            capability_id="fake_write_capability",
            version="1",
            name="Fake write capability",
            purpose="test fixture",
            category="test",
            owner="tests",
            execution_type="deterministic_tool",
            side_effect_class="local_write",
        )
        monkeypatch.setattr(registry, "get", lambda capability_id: fake_manifest)

        graph = TaskGraph()
        task = graph.add_task(
            Task(capability_id="fake_write_capability", arguments={"org_repo": ORG_REPO})
        )

        result = dispatch_and_record(
            graph, task, backend=None, org_repo=ORG_REPO, decisions=[], turn=1
        )

        assert result.state == "BLOCKED"
        assert "mode" in result.blocked_reason

    def test_write_capable_capability_not_mode_blocked_when_mode_full(self, project, monkeypatch):
        """Control case: mode == "full" is unaffected -- the new mode check
        itself does not fire for a repo whose push access is verified.
        (backend=None here means dispatch_gated_effect() is never reached
        either way -- that branch is pre-existing, unchanged behavior, not
        what decision #40 touched; this isolates just the new check.)"""
        from readme_agent.capabilities.dispatcher import DispatchResult
        from readme_agent.capabilities.schema import CapabilityManifest
        from readme_agent.supervisor.action_dispatch import dispatch_and_record
        from readme_agent.supervisor.task import Task, TaskGraph

        products_path = project / "data" / "products.json"
        products = json.loads(products_path.read_text(encoding="utf-8"))
        products[0]["mode"] = "full"
        products_path.write_text(json.dumps(products), encoding="utf-8")

        fake_manifest = CapabilityManifest(
            capability_id="fake_write_capability",
            version="1",
            name="Fake write capability",
            purpose="test fixture",
            category="test",
            owner="tests",
            execution_type="deterministic_tool",
            side_effect_class="local_write",
        )
        monkeypatch.setattr(registry, "get", lambda capability_id: fake_manifest)
        monkeypatch.setattr(
            "readme_agent.capabilities.dispatcher.dispatch_tool_call",
            lambda tool_call, permissions, extra_kwargs=None, state_backend=None: DispatchResult(
                outcome="executed", result={}
            ),
        )

        graph = TaskGraph()
        task = graph.add_task(
            Task(capability_id="fake_write_capability", arguments={"org_repo": ORG_REPO})
        )

        result = dispatch_and_record(
            graph, task, backend=None, org_repo=ORG_REPO, decisions=[], turn=1
        )

        assert result.state == "PASSED"
