"""TC-08 (`PRL-001/002/004/007/008`): the one real `remote_write` capability
this project registers. Opens a branch + PR against the real target repo
proposing the already-rendered, already-independently-verified README
candidate -- never merges, never approves. The human reviewing the PR on
GitHub is the sole approval authority (`PR-merge-as-approval`, decision #46)
-- this is how `GOV-018`'s per-instance human confirmation is satisfied for
an autonomous write, not a live blocking prompt.

Pairs with the read-only `render_readme_candidate` and the local-only
`commit_readme_write`, exactly the way those two already pair with each
other: the caller supplies this capability's `final_text`/`facts_hash`/
`fresh_fingerprint`/`verification_verdict`/`verification_nonce` directly
from that same run's own completed output -- this capability never
re-renders and never re-verifies, so it can never risk a second LLM call or
a `final_text` that silently drifts from what was actually rendered and
independently accepted.

**Deliberately not wired into any specialist's automatic dispatch path this
pass** (TC-08's own scope: build and prove the capability, not decide when
the autonomous loop should call it). Reachable today only via a direct,
explicit `caller_domain=README_PRESENTATION` dispatch -- see
`scripts/retrofits/prove_open_presentation_pr_live.py` for the one real,
human-confirmed live proof this project has run.

**`PRL-007` (structurally separate clone/remote path)**: uses
`paths.pr_work_dir()`/`gitsafety.clone.create_pr_clone()`, never
`paths.work_dir()`/`create_work_clone()` -- the one clone in this codebase
that is deliberately never neutered. Never reads or writes any other
capability's work clone.

**`PRL-001`/`PRL-002` (duplicate-PR prevention + state shape)**: the branch
name is deterministic (`readme-agent/presentation-update-{facts_hash[:12]}`)
so a rerun for identical content finds the same branch/PR instead of
opening a second one -- checked via `find_open_pr()` before ever cloning or
pushing anything. `reconciliation_check()` below answers the effect
ledger's own "did this already land" question the same way, for the
`EFF-001` pending/applied lifecycle.

**`idempotency_inputs` includes `final_text`** (Wave 9.6, `EFF-006`) in
addition to `fresh_fingerprint`: `effect_ledger.py::idempotency_key()`
hashes it via a typed `EffectIdentityV1` (`effect_identity.py`) rather than
`fresh_fingerprint` alone, which is only the pre-render upstream baseline
and cannot distinguish two different rendered candidates against the same
unchanged upstream -- the confirmed bug this fixes. This makes the ledger
itself correctly attempt a fresh `execute()` call for a second, differing
candidate rather than silently returning a stale cached result. **Named
honestly, not oversold**: `find_open_pr()`'s own branch-name dedup
immediately above still keys on `facts_hash` alone (unchanged by this fix),
so that second `execute()` attempt still finds the first candidate's
still-open PR and returns `already_open` without pushing the new content --
a separate, pre-existing gap this fix exposed but does not itself close
(`PRL-009`).

**`PRL-004` (write model)**: direct branch push, confirmed live (decision
#46, `gh api` against the 3 confirmed pilots: `push=true`/`admin=true`) --
no fork-and-PR fallback exists or is needed for those repos.

**`PRL-008` (lock revalidation)**: inherited for free -- `dispatch_gated_
effect()` (`EFF-005`) already revalidates lock holder identity before its
own terminal `applied` write, for every `remote_write`/`local_write`
capability alike; nothing here needs to duplicate that.

**`AUTH-004`/`AUTH-005` (Wave 13.3, authorization enforcement cutover)**:
declares `effect_classes=["PR_BRANCH_PUSH", "PR_CREATE_OR_UPDATE"]` -- the
one real remote-write capability this project has, and the first (and, as
of this wave, only) capability wired to `authorization.registry.
authorized_for()`. `dispatch_gated_effect()` checks this *in addition to*
`mode != 'full'` above, not instead of, until the two are proven
equivalent. **No repo has a real authorization record filed yet** (a
deliberate, human-confirmed choice, not an oversight -- see decision #69):
granting one is a human-authored, asynchronously-reviewed act, and self-
authoring it under this same commit authority would collapse the two-layer
design back into one layer the agent alone controls, exactly the "infers
authorization from `mode == 'full'` alone" failure `AUTH-004` exists to
close. The practical consequence: this capability is now blocked
(`blocked_pending_authorization`) for every repo, including
`aspose-cells-foss/Aspose.Cells-FOSS-for-Java` (the one repo with a real
merged-precedent PR) -- correct, not a regression, until a human files a
real record for it."""

from readme_agent import env, paths
from readme_agent.capabilities.domains import README_PRESENTATION
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.errors import GitSafetyError, NotAllowlistedError
from readme_agent.github_api.client import repo_summary
from readme_agent.github_api.write_client import create_pull_request, find_open_pr
from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.clone import clone_baseline, create_pr_clone, push_branch
from readme_agent.inspection import file_inventory
from readme_agent.orchestrator import require_permitted
from readme_agent.verification.checks import compute_verification_token

CAPABILITY_ID = "open_presentation_pr"

_BRANCH_PREFIX = "readme-agent/presentation-update-"

_PR_BODY_TEMPLATE = (
    "Automated repository-presentation update proposed by readme-agent.\n\n"
    "This PR is never auto-merged by the agent -- review the diff and merge it "
    "manually if it looks correct, or close it if it does not.\n\n"
    "<!-- readme-agent:facts_hash={facts_hash} -->"
)

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Open presentation PR",
    purpose="The one real remote write: pushes the already-rendered, already-independently-"
    "verified README candidate to a new branch on the real target repo and opens a PR "
    "proposing it -- never merges, never approves. Requires the same prior independent "
    "accept (verification_verdict/verification_nonce) commit_readme_write requires, from "
    "the independent_verification domain (VER-001). Never re-renders, never re-verifies.",
    category="readme_presentation",
    owner="readme_agent.orchestrator",
    execution_type="gated_effector",
    required_inputs={
        "org_repo": "string",
        "facts_hash": "string",
        "fresh_fingerprint": "string",
        "final_text": "string",
        "verification_verdict": "string",
        "verification_nonce": "string",
    },
    produced_outputs={
        "opened": "boolean",
        "already_open": "boolean",
        "pr_number": "integer",
        "pr_url": "string",
        "branch_name": "string",
    },
    preconditions=[
        "org_repo must be listed in data/products.json with mode == 'full'",
        "final_text/facts_hash/fresh_fingerprint must be exactly render_readme_candidate's "
        "own output for this same run -- never independently recomputed here",
        "verification_verdict must be the exact token compute_verification_token() produces "
        "for these inputs, from a real dispatch of verify_readme_candidate under "
        "caller_domain=independent_verification (VER-001)",
        "a GH_TOKEN/GITHUB_PAT with real write access to org_repo must be configured -- this "
        "capability never attempts a fork-based fallback",
    ],
    required_permissions=["remote_write"],
    side_effect_class="remote_write",
    allowed_domains=[README_PRESENTATION],
    effect_classes=["PR_BRANCH_PUSH", "PR_CREATE_OR_UPDATE"],
    idempotency_inputs=["org_repo", "facts_hash", "fresh_fingerprint", "final_text"],
    retry_policy="idempotent_only",
    evidence_outputs=["opened", "already_open", "pr_number", "pr_url", "branch_name"],
    tools_used=[
        "gitsafety.clone.create_pr_clone",
        "gitsafety.clone.push_branch",
        "github_api.write_client.create_pull_request",
    ],
    failure_modes=[
        "NotAllowlistedError if org_repo is not permitted or mode != 'full'",
        "GitSafetyError if no GH token is configured, or any git/GitHub API step fails",
    ],
    rollback_behavior="closing the PR (and optionally deleting the branch) on GitHub reverses "
    "this entirely -- nothing here is ever merged automatically, so there is no local state "
    "to roll back",
    tests=["tests/unit/test_open_presentation_pr.py"],
    requirement_ids=["PRL-001", "PRL-002", "PRL-004", "PRL-007", "PRL-008", "EFF-001", "VER-001"],
)


def execute(
    org_repo: str,
    facts_hash: str,
    fresh_fingerprint: str,
    final_text: str,
    verification_verdict: str,
    verification_nonce: str,
) -> dict:
    entry = require_permitted(org_repo)
    if entry.mode != "full":
        raise NotAllowlistedError(
            f"{org_repo} is mode={entry.mode!r}, not 'full' -- open_presentation_pr only runs "
            "for entries with real write authorization"
        )

    token = env.gh_token()
    if not token:
        raise GitSafetyError(
            f"no GH_TOKEN/GITHUB_PAT configured -- cannot open a PR for {org_repo}"
        )

    branch_name = f"{_BRANCH_PREFIX}{facts_hash[:12]}"

    existing = find_open_pr(org_repo, branch_name, token)
    if existing is not None:
        return {
            "opened": False,
            "already_open": True,
            "pr_number": existing["number"],
            "pr_url": existing["html_url"],
            "branch_name": branch_name,
        }

    baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
    pr_work_path = paths.pr_work_dir(entry.org, entry.repo_name)
    clone_baseline(entry, baseline_path)
    create_pr_clone(entry, baseline_path, pr_work_path)

    inventory = file_inventory.scan(pr_work_path)
    readme_path = inventory.readme_path or (pr_work_path / "README.md")
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text(final_text, encoding="utf-8")

    checkout = run_git(["checkout", "-b", branch_name], cwd=pr_work_path)
    if checkout.returncode != 0:
        raise GitSafetyError(f"branch creation failed for {org_repo}: {checkout.stderr}")

    add = run_git(["add", "-A"], cwd=pr_work_path)
    if add.returncode != 0:
        raise GitSafetyError(f"git add failed for {org_repo}: {add.stderr}")

    commit = run_git(
        ["commit", "-m", f"readme-agent: refresh repository presentation ({facts_hash[:12]})"],
        cwd=pr_work_path,
    )
    if commit.returncode != 0:
        raise GitSafetyError(f"commit failed for {org_repo}: {commit.stderr}")

    push = push_branch(pr_work_path, branch_name, token)
    if push.returncode != 0:
        raise GitSafetyError(f"push failed for {org_repo}: {push.stderr}")

    default_branch = repo_summary(org_repo, token)["default_branch"]
    pr = create_pull_request(
        org_repo,
        head=branch_name,
        base=default_branch,
        title="docs: refresh repository presentation",
        body=_PR_BODY_TEMPLATE.format(facts_hash=facts_hash),
        token=token,
    )

    return {
        "opened": True,
        "already_open": False,
        "pr_number": pr["number"],
        "pr_url": pr["html_url"],
        "branch_name": branch_name,
    }


def precheck(arguments: dict) -> str | None:
    """Identical hardening to `commit_readme_write.py::precheck()`
    (TC-15/TC-28, decision #46/#48/#50): `verification_verdict` must be the
    exact, re-derivable token `compute_verification_token()` produces for
    THIS call's own `org_repo`/`facts_hash`/`fresh_fingerprint`/
    `verification_nonce` -- never a hardcoded literal, never a token minted
    for different content or a different run."""
    verdict = arguments.get("verification_verdict")
    expected = compute_verification_token(
        arguments.get("org_repo", ""),
        arguments.get("facts_hash", ""),
        arguments.get("fresh_fingerprint", ""),
        arguments.get("verification_nonce", ""),
    )
    if verdict != expected:
        return "verification_verdict does not match the expected verification token"
    return None


def reconciliation_check(arguments: dict) -> dict | None:
    """`EFF-001`'s remaining gap, closed the same way `commit_readme_write`'s
    own version is: re-queries the actual external system (here, GitHub's
    own PR list, via `find_open_pr()`) rather than trusting the ledger's own
    possibly-stale `pending` record. A match means a prior attempt's push +
    PR-create landed before it crashed (mid-PR-create or mid-ledger-write) --
    the stale `pending` record backfills to `applied` instead of staying
    stuck forever."""
    org_repo = arguments.get("org_repo")
    facts_hash = arguments.get("facts_hash")
    if not org_repo or not facts_hash:
        return None

    token = env.gh_token()
    if not token:
        return None

    branch_name = f"{_BRANCH_PREFIX}{facts_hash[:12]}"
    existing = find_open_pr(org_repo, branch_name, token)
    if existing is None:
        return None
    return {
        "opened": True,
        "already_open": True,
        "pr_number": existing["number"],
        "pr_url": existing["html_url"],
        "branch_name": branch_name,
    }
