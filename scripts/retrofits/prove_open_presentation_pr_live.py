"""TC-08 live proof: render -> verify -> open_presentation_pr against a real
registry pilot, ending in one real, open, reviewable pull request on GitHub.

Deliberately NOT wired into `supervisor/loop.py`'s automatic dispatch path
(see `capabilities/open_presentation_pr.py`'s own module docstring) -- this
script is, today, the only caller that ever reaches this capability, and it
requires an explicit `--confirm-real-pr` flag on top of whatever human
confirmation gated running it at all (`GOV-018`): this script WILL push a
real branch and open a real PR against a real, public GitHub repository if
allowed to proceed.

Reuses the real, imported (never reimplemented) `render_readme_candidate`/
`verify_readme_candidate`/`open_presentation_pr` capability executors and
`compute_verification_token()` -- the exact same token-computation shape
`specialists/readme_presentation.py::_verify_node` uses internally, so this
script's own accept path cannot be satisfied by anything the real specialist
graph would reject.

Uses the real `GitStateBackend` (this project's own remote state ref, not
an in-memory fake) so the effect ledger's pending/applied bookkeeping for
this dispatch is durable and inspectable afterward, exactly like a real
`supervise` run's dispatch would be.

Kept after use as the executable record of this verification -- see
plans/GOVERNANCE.md, "Repository layout", placement rule 5.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent.capabilities import (  # noqa: E402
    open_presentation_pr,
    render_readme_candidate,
    verify_readme_candidate,
)
from readme_agent.capabilities.dispatcher import DispatchResult  # noqa: E402
from readme_agent.capabilities.domains import README_PRESENTATION  # noqa: E402
from readme_agent.capabilities.effect_ledger import dispatch_gated_effect  # noqa: E402
from readme_agent.registry.loader import require_listed  # noqa: E402
from readme_agent.state.git_backend import GitStateBackend  # noqa: E402
from readme_agent.verification.checks import compute_verification_token  # noqa: E402


def main() -> None:
    if "--confirm-real-pr" not in sys.argv:
        print(
            "Refusing to run: this script pushes a real branch and opens a real PR "
            "against a real GitHub repository. Re-run with --confirm-real-pr if that is "
            "genuinely intended.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    org_repo = positional[0] if positional else "aspose-3d-foss/Aspose.3D-FOSS-for-Java"

    entry = require_listed(org_repo)
    if entry.mode != "full":
        print(f"Refusing: {org_repo} is mode={entry.mode!r}, not 'full'.", file=sys.stderr)
        raise SystemExit(1)

    print(f"Pilot: {org_repo} (mode={entry.mode})")
    print("Step 1/3: render_readme_candidate (live LLM, force_regenerate=True)...")
    render_result = render_readme_candidate.execute(
        org_repo, force_regenerate=True, llm_mode="live"
    )
    print(
        f"  status={render_result['status']!r} needs_write={render_result['needs_write']!r} "
        f"facts_hash={render_result['facts_hash'][:12]}..."
    )

    if not render_result["needs_write"]:
        print(
            "Nothing to propose: the live render produced content identical to what's "
            "already on disk. No PR will be opened -- this is a real, honest outcome, "
            "not a script failure.",
        )
        return

    print("Step 2/3: verify_readme_candidate (independent re-derivation)...")
    verification = verify_readme_candidate.execute(
        org_repo,
        facts_hash=render_result["facts_hash"],
        fresh_fingerprint=render_result["fresh_fingerprint"],
        status=render_result["status"],
        needs_write=render_result["needs_write"],
        final_text=render_result["final_text"],
    )
    print(f"  verdict={verification['verdict']!r}")
    if verification["verdict"] != "accept":
        print(f"Verification rejected: {verification.get('reason')}", file=sys.stderr)
        raise SystemExit(1)

    nonce = f"prove-open-presentation-pr-live-{org_repo}"
    token = compute_verification_token(
        org_repo, render_result["facts_hash"], render_result["fresh_fingerprint"], nonce
    )

    print("Step 3/3: open_presentation_pr (real branch push + real PR create)...")
    tool_call = {
        "function": {
            "name": open_presentation_pr.CAPABILITY_ID,
            "arguments": {
                "org_repo": org_repo,
                "facts_hash": render_result["facts_hash"],
                "fresh_fingerprint": render_result["fresh_fingerprint"],
                "final_text": render_result["final_text"],
                "verification_verdict": token,
                "verification_nonce": nonce,
            },
        }
    }
    backend = GitStateBackend()
    gated = dispatch_gated_effect(
        tool_call, {"remote_write"}, backend, org_repo, caller_domain=README_PRESENTATION
    )

    print(f"  ledger outcome: {gated.outcome}")
    dispatch: DispatchResult | None = gated.dispatch
    if dispatch is not None:
        print(f"  dispatch outcome: {dispatch.outcome}")
        if dispatch.result:
            print(f"  result: {dispatch.result}")
        if dispatch.error:
            print(f"  error: {dispatch.error}", file=sys.stderr)
    if gated.cached_result:
        print(f"  cached_result: {gated.cached_result}")

    print("\n=== Verdict ===")
    result = (dispatch.result if dispatch else None) or gated.cached_result
    if result and result.get("opened"):
        print(f"Opened: {result['pr_url']}")
    elif result and result.get("already_open"):
        print(f"Already open: {result['pr_url']}")
    else:
        print("No PR was opened -- see the outcome/error above.")


if __name__ == "__main__":
    main()
