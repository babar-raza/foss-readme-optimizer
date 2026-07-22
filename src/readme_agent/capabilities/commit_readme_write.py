"""The one real mutating capability this project registers (Wave 7g,
`EFF-001`). Wraps `orchestrator.commit_generated_readme()` -- the actual
write plus, only when `mode == "full"` and `status == "GENERATED"`, one real
local git commit into the local work clone, never pushed (`docs/safety-
model.md`). Pairs with the read-only `render_readme_candidate`: the caller
(`specialists/readme_presentation.py`) supplies this capability's
`final_text`/`facts_hash`/`fresh_fingerprint`/`status`/`needs_write` directly
from that capability's own completed output for this same run -- this
capability never re-renders, so it can never risk a second LLM call or a
`final_text` that silently drifts from what was actually rendered and
validated.

**The `mode == "full"` gate lives here, inside `execute()`, not in
`supervisor/loop.py::_dispatch_and_record()`.** That function's own
write-capable mode check (`clever-splashing-peach`, decision #40) only ever
runs for the general planner's dispatch path -- and this capability is
domain-scoped (`allowed_domains=[README_PRESENTATION]`), so the general
planner (`caller_domain=None`) can never legally reach it in the first
place; `_dispatch_and_record()`'s check is dead code for this specific
capability's real call path, which is always the `readme_presentation`
specialist calling `dispatch_gated_effect()` directly. Verified against the
actual current code, not assumed from the plan's own text (which claimed
this gate was "inherited for free" -- true for a hypothetical *unscoped*
write-capable capability, not true for this one). `commit_generated_readme()`
checks `mode` itself so every real caller, present and future, gets the
same protection regardless of dispatch path.

Deliberately stateless (decision #26(b)): does not read or write
`RunStateV1.accepted_facts_hash`/`accepted_status` itself -- unifying that
ledger with the CLI path's is `specialists/readme_presentation.py`'s own
`record` node's job (it already has the durable backend via
`config["configurable"]`), exactly matching every other specialist's own
`record` node being the sole owner of durable writes.

**`verification_verdict` (Wave 8b, `VER-001`)**: a required input, not
optional -- there is no legitimate way to dispatch this capability without
it. The real enforcement is `specialists/readme_presentation.py::
_verify_node`'s own `"ERROR:"`-prefixed status, which short-circuits
`_commit_node` before this capability is ever dispatched at all on a
reject; `precheck()` below is pure belt-and-braces for a hypothetical future
bug in that wiring, checked *before* the effect ledger writes any pending
entry (not a bare `assert` inside `execute()` -- found by adversarial
review: writing the pending entry first, then failing, has the exact same
signature as a genuine crash-mid-effect and would permanently jam this
idempotency key behind `blocked_pending_reconciliation`, since `reconciliation_
check()` below can only confirm "did it land," never "should this have been
attempted at all." A bare `assert` is additionally its own hazard --
Python's `-O` flag strips assertions, the wrong mechanism for an
externally-reachable safety check).

**`verification_nonce` (TC-28, decision #46's own deferred scope from
TC-15)**: paired with `verification_verdict` -- `_verify_node` mints one
fresh nonce per specialist `run()` invocation and folds it into both. Without
it, a token computed for a given `facts_hash`/`fresh_fingerprint` in one run
would still be accepted if replayed into a *later*, separate run whose
content happened to hash identically -- `compute_verification_token()`'s own
docstring states this precisely. Deliberately excluded from
`idempotency_inputs` below: it is per-run, not per-content, and must never
affect the idempotency key (that would break retries of the *same* pending
effect across a lock-reclaim, EFF-005's whole point).

**`idempotency_inputs` includes `fresh_fingerprint`** alongside `org_repo`/
`facts_hash`: `facts_hash` deliberately excludes README content (decision
#11) and can legitimately stay identical across two calls that produce a
*different* `final_text` under `force_regenerate=True` combined with
ordinary LLM sampling variance in the `relationship_explained` paragraph --
without this, the second, newly-verified candidate would be silently
discarded by the ledger's `already_applied` cache hit in favor of the first,
stale one. `fresh_fingerprint` is already computed by `render_readme_
candidate` for an unrelated Wave 7 drift-detection purpose; reused here
rather than inventing a new hash."""

from pathlib import Path

from readme_agent import paths
from readme_agent.capabilities.domains import README_PRESENTATION
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.gitsafety._git import run_git
from readme_agent.inspection import file_inventory
from readme_agent.orchestrator import commit_generated_readme, require_permitted
from readme_agent.readme.markers import find_span
from readme_agent.registry.loader import find_entry
from readme_agent.verification.checks import compute_verification_token

CAPABILITY_ID = "commit_readme_write"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Commit README write",
    purpose="The one real write: persists the already-rendered README candidate to the local "
    "work clone (never pushed) and, only when mode == 'full' and status == 'GENERATED', makes "
    "one real local git commit. Never re-renders -- the caller supplies render_readme_candidate's "
    "own completed output for this run directly. Requires a prior independent accept "
    "(verification_verdict) from the independent_verification domain (VER-001).",
    category="readme_presentation",
    owner="readme_agent.orchestrator",
    execution_type="gated_effector",
    required_inputs={
        "org_repo": "string",
        "facts_hash": "string",
        "fresh_fingerprint": "string",
        "status": "string",
        "needs_write": "boolean",
        "final_text": "string",
        "verification_verdict": "string",
        "verification_nonce": "string",
    },
    produced_outputs={
        "written": "boolean",
        "committed": "boolean",
    },
    preconditions=[
        "org_repo must be listed in data/products.json with a non-disabled mode",
        "final_text/facts_hash/status/needs_write must be exactly render_readme_candidate's own "
        "output for this same run -- never independently recomputed here",
        "verification_verdict must be 'accept', from a real dispatch of verify_readme_candidate "
        "under caller_domain=independent_verification (VER-001)",
        "a real local git commit only happens when mode == 'full' and status == 'GENERATED' -- "
        "any other mode still writes the file (if needed) but never commits",
    ],
    required_permissions=["local_write"],
    side_effect_class="local_write",
    allowed_domains=[README_PRESENTATION],
    idempotency_inputs=["org_repo", "facts_hash", "fresh_fingerprint"],
    retry_policy="idempotent_only",
    tools_used=["orchestrator.commit_generated_readme"],
    failure_modes=["NotAllowlistedError if org_repo is not permitted with an enabled mode"],
    rollback_behavior="local git commit only, never pushed -- reversible via git reset in the "
    "local work clone; no remote effect exists to roll back",
    tests=["tests/unit/test_capabilities.py"],
    # Wave 8c (requirement mapping): the one real write, now gated by the
    # independent verifier before it can ever dispatch (VER-001).
    requirement_ids=["EFF-001", "VER-001"],
)


def execute(
    org_repo: str,
    facts_hash: str,
    fresh_fingerprint: str,
    status: str,
    needs_write: bool,
    final_text: str,
    verification_verdict: str,
    # Validated by precheck() (called separately, before this ever runs) --
    # accepted here only so **arguments dispatch doesn't raise on the
    # manifest's own declared required input.
    verification_nonce: str = "",
) -> dict:
    entry = require_permitted(org_repo)
    work_path = paths.work_dir(entry.org, entry.repo_name)

    written = False
    if needs_write:
        inventory = file_inventory.scan(work_path)
        readme_path = inventory.readme_path or (work_path / "README.md")
        readme_path.parent.mkdir(parents=True, exist_ok=True)
        readme_path.write_text(final_text, encoding="utf-8")
        written = True

    committed = commit_generated_readme(work_path, facts_hash, status, mode=entry.mode)

    return {"written": written, "committed": committed}


def precheck(arguments: dict) -> str | None:
    """Wave 8b (`VER-001`); hardened Wave 8.6+ (TC-15, decision #46, `F3`):
    checked by `effect_ledger.py::dispatch_gated_effect()` before any
    pending ledger entry is written -- see this module's own docstring for
    why a rejection here must never reach the ledger. The primary gate is
    still `specialists/readme_presentation.py::_verify_node`'s own
    `"ERROR:"` short-circuit (this capability is never dispatched at all on
    a real reject); this check is no longer a plain string comparison
    against the literal `"accept"`, which any caller -- including a future
    wiring bug that skips `_verify_node` entirely -- could satisfy by typing
    the same four characters. `verification_verdict` must now be the exact
    token `verification.checks.compute_verification_token()` produces from
    THIS call's own `org_repo`/`facts_hash`/`fresh_fingerprint`/
    `verification_nonce` -- a value only `_verify_node` can correctly
    produce, and only after a real accept for this exact candidate in this
    exact run. `compute_verification_token()`'s own docstring states plainly
    what this does and does not defend against."""
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
    """`EFF-001`'s remaining gap, closed for real (Wave 7g): re-reads the
    work clone's *current* README content and compares its embedded
    `resources`-span `facts_hash` (`markers.py::find_span`) against the
    pending record's target `facts_hash` -- a match means a prior attempt's
    write landed before it crashed (mid-commit or mid-ledger-write), so the
    stale `pending` record backfills to `applied` instead of staying stuck
    forever. `committed` is reported conservatively: `True` only when the
    work clone's current HEAD commit message itself carries this exact
    `facts_hash` prefix (the same message `commit_generated_readme()`
    writes) -- a clean-but-uncommitted write (e.g. `mode != "full"`, or a
    crash between file write and git commit) correctly reports `committed:
    False` here, matching reality rather than assuming the best case."""
    org_repo = arguments.get("org_repo")
    facts_hash = arguments.get("facts_hash")
    if not org_repo or not facts_hash:
        return None

    entry = find_entry(org_repo)
    if entry is None:
        return None

    work_path = paths.work_dir(entry.org, entry.repo_name)
    if not (work_path / ".git").exists():
        return None

    inventory = file_inventory.scan(work_path)
    if inventory.readme_path is None or not inventory.readme_path.exists():
        return None

    text = inventory.readme_path.read_text(encoding="utf-8")
    span = find_span(text, "resources")
    if span is None or span.facts_hash != facts_hash:
        return None

    committed = _head_commit_matches(work_path, facts_hash)
    return {"written": True, "committed": committed}


def _head_commit_matches(work_path: Path, facts_hash: str) -> bool:
    result = run_git(["log", "-1", "--format=%s"], cwd=work_path)
    if result.returncode != 0:
        return False
    return facts_hash[:12] in result.stdout
