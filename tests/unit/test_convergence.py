"""`AGT-004`: stop only on defined convergence, missing-permission, or
genuine-blocker conditions -- never an arbitrary global iteration limit."""

from pathlib import Path

from readme_agent.capabilities.schema import CapabilityGap
from readme_agent.supervisor.convergence import (
    check_repair_exhausted,
    compute_control_plane_fingerprint,
    final_status,
    is_fresh,
)
from readme_agent.supervisor.task import Task, TaskGraph

REPO_ROOT = Path(__file__).resolve().parents[2]

_POLICY_YAML_A = """schema_version: 2
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

_POLICY_YAML_B = _POLICY_YAML_A.replace(
    'prohibited_terms: ["guarantee"]', 'prohibited_terms: ["guarantee", "promise"]'
)


def _setup_project_root(tmp_path, policy_yaml: str):
    (tmp_path / "config" / "policies").mkdir(parents=True)
    (tmp_path / "config" / "policies" / "test-profile.yml").write_text(
        policy_yaml, encoding="utf-8"
    )
    # Wave 8.5: llm.prompts.prompt_content_hash() reads
    # prompts/generation/relationship_explained.yaml fresh, cwd-relative, on
    # every call -- staged here so it doesn't raise after monkeypatch.chdir().
    # build_prompt()/the supervisor's own prompt are read from the eagerly
    # import-time-cached prompt_registry instead, unaffected by cwd, so no
    # other prompt file needs staging here.
    prompt_dir = tmp_path / "prompts" / "generation"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "relationship_explained.yaml").write_text(
        (REPO_ROOT / "prompts" / "generation" / "relationship_explained.yaml").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )


class TestIsFresh:
    def test_matching_revisions_is_fresh(self):
        assert is_fresh("abc123", "abc123")

    def test_different_revisions_is_not_fresh(self):
        assert not is_fresh("abc123", "def456")

    def test_none_recorded_is_not_fresh(self):
        assert not is_fresh(None, "abc123")

    def test_none_current_is_not_fresh(self):
        assert not is_fresh("abc123", None)


class TestControlPlaneFingerprint:
    """Wave 8 (production-reliability pass, external-review triage
    2026-07-21): `is_fresh()` alone was blind to a control-plane change
    (policy/prompt/capability-version) with no new upstream commit -- both
    dimensions proven here: `is_fresh()`'s own extended contract, and
    `compute_control_plane_fingerprint()`'s real sensitivity to a policy
    change."""

    def test_unchanged_fingerprint_still_short_circuits_exactly_as_before(self):
        assert is_fresh(
            "abc123",
            "abc123",
            recorded_control_plane_fingerprint="fp1",
            current_control_plane_fingerprint="fp1",
        )

    def test_changed_fingerprint_with_unchanged_revision_is_not_fresh(self):
        """The exact gap this fix closes: upstream unchanged, but the
        control plane moved -- must NOT short-circuit."""
        assert not is_fresh(
            "abc123",
            "abc123",
            recorded_control_plane_fingerprint="fp1",
            current_control_plane_fingerprint="fp2",
        )

    def test_no_recorded_fingerprint_forces_one_honest_revalidation(self):
        """A record written before this field existed (`None`) must never
        be trusted as a match against a real current fingerprint."""
        assert not is_fresh(
            "abc123",
            "abc123",
            recorded_control_plane_fingerprint=None,
            current_control_plane_fingerprint="fp2",
        )

    def test_omitting_the_fingerprint_args_entirely_preserves_old_behavior(self):
        """Backward compatible: every pre-Wave-8 caller of is_fresh() that
        never passes these new keyword args gets the exact old behavior."""
        assert is_fresh("abc123", "abc123")

    def test_same_policy_produces_the_same_fingerprint(self, tmp_path, monkeypatch):
        _setup_project_root(tmp_path, _POLICY_YAML_A)
        monkeypatch.chdir(tmp_path)

        first = compute_control_plane_fingerprint("test-profile")
        second = compute_control_plane_fingerprint("test-profile")

        assert first == second

    def test_a_changed_policy_changes_the_fingerprint(self, tmp_path, monkeypatch):
        _setup_project_root(tmp_path, _POLICY_YAML_A)
        monkeypatch.chdir(tmp_path)
        before = compute_control_plane_fingerprint("test-profile")

        (tmp_path / "config" / "policies" / "test-profile.yml").write_text(
            _POLICY_YAML_B, encoding="utf-8"
        )
        after = compute_control_plane_fingerprint("test-profile")

        assert before != after

    def test_no_policy_profile_still_produces_a_real_fingerprint(self, tmp_path, monkeypatch):
        _setup_project_root(tmp_path, _POLICY_YAML_A)
        monkeypatch.chdir(tmp_path)

        fingerprint = compute_control_plane_fingerprint(None)

        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64  # sha256 hex digest

    def test_a_capability_version_change_changes_the_fingerprint(self, tmp_path, monkeypatch):
        from readme_agent.capabilities import registry

        _setup_project_root(tmp_path, _POLICY_YAML_A)
        monkeypatch.chdir(tmp_path)
        before = compute_control_plane_fingerprint(None)

        original = registry.list_all()
        bumped = [m.model_copy(update={"version": m.version + "-bumped"}) for m in original]
        monkeypatch.setattr(registry, "list_all", lambda: bumped)
        after = compute_control_plane_fingerprint(None)

        assert before != after

    def test_a_validation_ruleset_version_change_changes_the_fingerprint(
        self, tmp_path, monkeypatch
    ):
        """`VER-004`: without this, a rule-code change with no new upstream
        commit would leave `is_fresh()`'s own coarse shortcut still firing,
        so the specialist tier (and `orchestrator.py`'s own `durable_skip`
        check inside it) would never get a chance to notice the rule
        change at all -- the exact gap that would have made VER-004's fix
        ineffective for every `supervise`-driven repo."""
        from readme_agent import validation

        _setup_project_root(tmp_path, _POLICY_YAML_A)
        monkeypatch.chdir(tmp_path)
        before = compute_control_plane_fingerprint(None)

        monkeypatch.setattr(validation.registry, "VALIDATION_RULESET_VERSION", "999")
        after = compute_control_plane_fingerprint(None)

        assert before != after


class TestDomainCoverageComplete:
    """`VER-005` (found live, Wave 8e full-registry pass, 2026-07-21): a
    prior run's upstream revision and control-plane fingerprint can both
    match, yet its `domain_states` coverage was left incomplete by a crash
    or a lost race -- `is_fresh()` must not trust that as a genuine
    convergence. `check_domain_coverage` is opt-in (default `False`) so
    every existing, unconverted caller is unaffected."""

    def test_not_checking_domain_coverage_preserves_old_behavior(self):
        """Default `check_domain_coverage=False`: an unset/incomplete
        recorded value must not force a full run for a caller that never
        asked for this check -- the exact backward-compatibility bar
        `current_control_plane_fingerprint`'s own opt-in already set."""
        assert is_fresh(
            "abc123",
            "abc123",
            recorded_domain_coverage_complete=None,
        )

    def test_incomplete_coverage_is_not_fresh_when_checked(self):
        """The exact gap this fix closes: revision and control-plane both
        match, but coverage was incomplete -- must not short-circuit."""
        assert not is_fresh(
            "abc123",
            "abc123",
            recorded_domain_coverage_complete=False,
            check_domain_coverage=True,
        )

    def test_no_recorded_coverage_value_forces_one_honest_revalidation(self):
        """A record written before this field existed (`None`) must never
        be trusted as complete -- same self-healing pattern as a `None`
        control-plane fingerprint."""
        assert not is_fresh(
            "abc123",
            "abc123",
            recorded_domain_coverage_complete=None,
            check_domain_coverage=True,
        )

    def test_complete_coverage_still_short_circuits_exactly_as_before(self):
        """The explicit non-regression proof: a healthy prior run (complete
        coverage) must still hit the fast path -- this check must never
        force a full run on every single call for every repo, forever."""
        assert is_fresh(
            "abc123",
            "abc123",
            recorded_domain_coverage_complete=True,
            check_domain_coverage=True,
        )

    def test_combines_correctly_with_the_control_plane_fingerprint_check(self):
        """Both new dimensions (Wave 8a's fingerprint, this fix's coverage
        flag) must compose -- a mismatch in either one alone must break the
        shortcut, not just when both are wrong simultaneously."""
        assert not is_fresh(
            "abc123",
            "abc123",
            recorded_control_plane_fingerprint="fp1",
            current_control_plane_fingerprint="fp1",
            recorded_domain_coverage_complete=False,
            check_domain_coverage=True,
        )
        assert is_fresh(
            "abc123",
            "abc123",
            recorded_control_plane_fingerprint="fp1",
            current_control_plane_fingerprint="fp1",
            recorded_domain_coverage_complete=True,
            check_domain_coverage=True,
        )


class TestCheckRepairExhausted:
    def test_under_max_turns_returns_none(self):
        assert check_repair_exhausted(turns_taken=1, max_turns=8) is None

    def test_at_max_turns_is_blocked_as_a_bug_detector_not_a_normal_stop(self):
        outcome = check_repair_exhausted(turns_taken=8, max_turns=8)
        assert outcome is not None
        assert outcome.status == "BLOCKED"
        assert outcome.blocked_reason == "repair_exhausted"


class TestFinalStatus:
    def test_no_blocked_tasks_converges_no_change(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a"))
        graph.mark(t1.task_id, "PASSED")
        outcome = final_status(graph, applied_any_effect=False)
        assert outcome.status == "CONVERGED_NO_CHANGE"

    def test_applied_effect_converges_applied(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a"))
        graph.mark(t1.task_id, "PASSED")
        outcome = final_status(graph, applied_any_effect=True)
        assert outcome.status == "CONVERGED_APPLIED"

    def test_blocked_task_with_no_other_passed_work_is_blocked(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a"))
        graph.mark(t1.task_id, "BLOCKED", blocked_reason="rejected_permission_denied")
        outcome = final_status(graph, applied_any_effect=False)
        assert outcome.status == "BLOCKED"
        assert outcome.blocked_reason == "rejected_permission_denied"

    def test_blocked_gap_alongside_independent_passed_work_is_partial_with_gap(self):
        """GAP-001's 'continue independent supported work' + GAP-002's exact
        literal status string, proven together."""
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="a"))
        graph.mark(t1.task_id, "PASSED")
        t2 = graph.add_task(Task(capability_id="unknown"))
        graph.mark(
            t2.task_id,
            "BLOCKED",
            gap=CapabilityGap(requested_need="x", reason="no match"),
        )
        outcome = final_status(graph, applied_any_effect=False)
        assert outcome.status == "PARTIAL_WITH_CAPABILITY_GAP"

    def test_blocked_gap_with_no_independent_passed_work_is_plain_blocked(self):
        graph = TaskGraph()
        t1 = graph.add_task(Task(capability_id="unknown"))
        graph.mark(
            t1.task_id,
            "BLOCKED",
            gap=CapabilityGap(requested_need="x", reason="no match"),
        )
        outcome = final_status(graph, applied_any_effect=False)
        assert outcome.status == "BLOCKED"
