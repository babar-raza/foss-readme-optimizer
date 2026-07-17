"""Mechanical enforcement of the facts<->prompt coupling (Consistency &
Determinism Tier 1 SS2). Two things are asserted, deliberately:

1. build_prompt's signature is exactly (facts, policy) -- no ambient reads, no
   side-channel parameters. A future contributor adding a third parameter (a
   silent side-channel) trips this immediately.
2. Every RepositoryFacts field that's supposed to influence the prompt
   actually does, when mutated in isolation. This converts the realistic
   failure mode -- "added a fact to the prompt, forgot the hash" -- from
   silent to a loud test failure, though it can't catch a determined
   implementation that reads ambient state some other way.
"""

import inspect
from pathlib import Path

from readme_agent.llm.prompts import build_prompt
from readme_agent.readme.facts import GapReportFacts, RepositoryFacts
from readme_agent.readme.gap_detector import GapReport
from readme_agent.registry.loader import load_policy

REPO_ROOT = Path(__file__).resolve().parents[2]


def _policy():
    return load_policy("aspose-3d-foss", REPO_ROOT / "config" / "policies")


def _facts(**overrides) -> RepositoryFacts:
    defaults = dict(
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Java",
        commit_sha="abc123",
        manifest={"artifact_id": "aspose-3d-foss", "name": "Aspose.3D FOSS"},
        detected_license="MIT",
        gap_report=GapReportFacts.from_gap_report(
            GapReport(
                license_mentioned=False,
                products_org_link=False,
                products_com_link=False,
                relationship_explained=False,
            )
        ),
        policy_content_hash="policyhash123",
    )
    defaults.update(overrides)
    return RepositoryFacts(**defaults)


def _prompt_text(facts: RepositoryFacts) -> str:
    return " ".join(m["content"] for m in build_prompt(facts, _policy()))


class TestSignatureStaysNarrow:
    def test_build_prompt_takes_only_facts_and_policy(self):
        params = list(inspect.signature(build_prompt).parameters)
        assert params == ["facts", "policy"], (
            "build_prompt grew a new parameter -- this is exactly the kind of "
            "silent side-channel the coupling contract exists to prevent. If "
            "this is intentional, the new parameter also needs to become part "
            "of RepositoryFacts so it flows through facts_hash."
        )


class TestFieldsThatMustChangeThePrompt:
    """Each of these fields is used to shape the prompt text -- mutating it in
    isolation must change what's asked of the LLM."""

    def test_org_repo_changes_the_prompt(self):
        base = _prompt_text(_facts())
        mutated = _prompt_text(_facts(org_repo="aspose-cells-foss/Aspose.Cells-FOSS-for-Java"))
        assert base != mutated

    def test_detected_license_changes_the_prompt(self):
        base = _prompt_text(_facts())
        mutated = _prompt_text(_facts(detected_license="Apache-2.0"))
        assert base != mutated

    def test_manifest_name_changes_the_prompt(self):
        base = _prompt_text(_facts())
        mutated = _prompt_text(_facts(manifest={"artifact_id": "x", "name": "Totally Different"}))
        assert base != mutated


class TestFieldsDeliberatelyNotUsedInThePrompt:
    """Not every RepositoryFacts field needs to shape the prompt -- only the
    ones that influence what the LLM is asked to write. commit_sha and
    policy_content_hash matter for *idempotency* (they're in the facts hash)
    but don't change the wording of the request itself. Documented here so
    it's a deliberate choice, not an unexamined gap."""

    def test_commit_sha_does_not_change_the_prompt(self):
        base = _prompt_text(_facts())
        mutated = _prompt_text(_facts(commit_sha="some-other-sha"))
        assert base == mutated
