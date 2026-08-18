# `local_poc` silently depends on live GitHub push/fetch for state, contrary to its own design intent

**FIXED 2026-08-18.** Found 2026-08-17 while investigating a transient `lock_held` block and a
`durable domain-state write-back failed` warning during a real portfolio run, both occurring even
after that day's preflight fix restored real repo/LLM access. Deliberately deferred that same day
("too large and load-bearing a change to make mid-run against an active verification pass"), then
its priority was raised the next day (see the "New concrete manifestation" addendum below) once it
started actively blocking `--bounded-verified-canary` re-verification of an unrelated fix, not just
degrading portfolio runs. Fixed in its own isolated pass: `commands_supervision.py` gained
`_state_backend_for_profile(profile)`, routing `local_poc` to the already-existing, already-tested
`default_local_poc_state_backend()` at both call sites that previously called
`_force_durable_state_backend()` unconditionally (`cmd_supervise`'s single-repo/canary path, and
`_cmd_supervise_registry`'s portfolio-fan-out path — the latter is unconditionally `local_poc` by
its own hard-coded contract, so it now calls `default_local_poc_state_backend()` directly, no
profile branch needed). Every other profile (`github_*`, `act_*`) is untouched — those still build
`default_state_backend()` exactly as before, and still genuinely need this repository's real
`origin` for cross-run coordination.

New regression coverage: `test_local_poc_backend_never_targets_origin` (`test_local_poc_
backend.py`) spies on every real `run_git` invocation a constructed `local_poc` backend makes
(load/lock/release) and asserts `"origin"` never appears as an argument, and that any `push`/
`fetch` targets only the isolated local bare remote — the exact regression this doc's own
"Recommended next step" asked for. `TestStateBackendForProfile` (`test_cli.py`, 5 tests) proves the
routing decision itself: `local_poc` never even constructs the real backend (a monkeypatched
`default_state_backend` that raises if called never fires), and every other profile (including
`None`) never touches the local-only backend. 17 pre-existing `test_cli.py` tests that stubbed only
`git_backend.default_state_backend` (an implicit assumption that stub covered every profile) needed
a companion `local_poc_backend.default_local_poc_state_backend` stub added
(`scripts/retrofits/add_local_poc_backend_test_patches.py`) — without it they silently fell through
to the real, now-correctly-used local backend and became 60-120s-slow real-subprocess tests instead
of fast in-memory-stubbed ones (diagnosed live via `faulthandler.dump_traceback_later`, not
guessed). Full unit suite and the two directly affected test files confirmed clean afterward.

## What's supposed to happen

`src/readme_agent/state/local_poc_backend.py` exists specifically to give the `local_poc`
execution profile a durable state backend that never touches the real GitHub remote:

> `default_local_poc_state_backend()`: "Build a durable backend that never defaults local POC
> state writes to `origin`."

It builds (or reuses) a purely local bare git repository at `runs/local-poc-state/state.git` as
the backend's "remote" — genuinely zero network dependency, matching `local_poc`'s own documented
profile contract (`execution_profile.py`: "the canonical, unattended full-registry local proof...
allowing only local effects").

## What actually happens

`commands_supervision.py` — the real, only call site that matters, the one every `supervise`
invocation actually runs through — never calls `default_local_poc_state_backend()`. Confirmed via
`grep -n "default_local_poc_state_backend\|default_state_backend()" commands_supervision.py`: the
only backend constructor called is `default_state_backend()` (line 988), which per
`git_backend.py:749` defaults to `remote="origin"` (this repository's own real GitHub remote)
unless the `README_AGENT_STATE_REMOTE` environment variable overrides it. `default_local_poc_
state_backend` appears to be dead code — a real, working, correctly-designed backend that nothing
in the real command path ever constructs.

## Consequence, confirmed live

Every `local_poc` run today — including every portfolio pass in this session, run before and after
today's preflight fix — has been silently depending on live `git push`/`git fetch` access to this
repository's real GitHub origin for domain-state and lock coordination, even though the profile's
own contract says it shouldn't need any network access beyond `read_only_network` for the *target*
repos, and explicitly never needs to write anywhere remote.

Two concrete symptoms traced to this, both non-fatal (the write-back failure is caught and
downgraded to a warning, so a run keeps going) but real:

- Today's earlier `StateBackendError: fetch of refs/readme-agent-state/{org}__{repo} failed: fatal:
  Cannot prompt because user interactivity has been disabled` mass-failures during the GitHub
  outage (runs 6/7, well before the preflight fix) — these were never about the target repos at
  all; they were `local_poc`'s own state coordination failing to reach *this* repo's GitHub remote.
- A transient `BLOCKED (lock_held; category=infra_external)` on `aspose-pdf-foss/Aspose-PDF-FOSS-
  for-Python` (previously a successful repo) during today's post-fix portfolio run, and a live
  `durable domain-state write-back failed... push of refs/readme-agent-state/locks/{org}__{repo}
  failed: fatal: Cannot prompt...` warning on `aspose-words-foss/Aspose.Words-FOSS-for-Python` in
  the same run — both are exactly what unreliable git-protocol access to `origin` (a separate
  concern from the REST-API preflight checks, which use `requests` against `api.github.com`
  directly, not `git push`/`fetch`) would produce.

## Why this wasn't caught by today's preflight fix

The preflight fix (commit `85cc71222`) only changed what `check_identity`/`check_repo` (plain
`requests.get` calls against `api.github.com`) are allowed to report as non-blocking. It has
nothing to do with `git push`/`git fetch` over the git smart-HTTP protocol, which is what
`git_backend.py`'s lock/state operations actually use. GitHub's REST API and its git-over-HTTPS
transport can degrade independently — today's `/user` outage recovering (or being correctly
bypassed) says nothing about whether `git push origin refs/readme-agent-state/...` is exercising a
healthy path.

## Why not fixed this session

Wiring `commands_supervision.py` to use `default_local_poc_state_backend()` for the `local_poc`
profile (and presumably `local_dry_run`/`local_inspect` too, though they don't currently persist
durable state at all per `execution_profile.py`) is exactly the kind of change today's own new
verification-workflow rule (AGENTS.md rule 15) exists to slow down: it touches how every `local_poc`
run persists lock/domain state, a load-bearing mechanism the entire portfolio pipeline depends on,
and doing it correctly needs its own isolated verification, not a patch applied while a real,
in-flight portfolio run (today's post-preflight-fix coverage measurement) is depending on the
current, unmodified behavior to finish cleanly.

## Recommended next step (DONE 2026-08-18, see the top of this doc)

~~Once the in-flight portfolio run is done: wire `_cmd_supervise_registry`/the portfolio-member loop
in `commands_supervision.py` to construct `default_local_poc_state_backend()` when `profile.name ==
"local_poc"` (mirroring `execution_profile.py`'s own `allowed_permission_classes` contract — no
`remote_write`, `read_only_network` only for the *target* repo, never this repo's own state), with
a regression test proving no `git push`/`fetch` against this repository's real `origin` occurs
during a `local_poc` run (e.g. by monkeypatching the git-command runner and asserting the remote
argument is always the local bare-repo path, never `origin`).~~ Done exactly as described, plus the
`local_dry_run`/`local_inspect` question this section left open was checked and confirmed moot:
neither profile persists durable state at all (`execution_profile.py`'s own `requires_durable_state
= False` for both), so `_state_backend_for_profile` is never even reached for them.

## New concrete manifestation, 2026-08-18: blocks bounded-verified-canary re-verification itself

Hit directly while trying to follow AGENTS.md rule 15 to verify the Dependencies-section template
fix (new `"dependencies"` slot, `template_version` 1.19.0 -> 1.20.0) against a real repo via
`readme-agent supervise --repo aspose-pdf-foss/Aspose-PDF-FOSS-for-Python --bounded-verified-canary
--execution-profile local_poc --mission-task-id L8-PORT-01-...`. Three consecutive canary attempts,
each preceded by an explicit `--mission-task-graph ... --mission-action claim --mission-observer
readme-agent-supervisor` (confirmed `exit 0`, clean status output, no error), still failed the very
next canary invocation with `error: task '...' is claimed by 'dependencies-section-fix-canary', not
observer 'readme-agent-supervisor'` — a claim owner from hours earlier in the same session that a
demonstrably-successful local reclaim never displaced.

Root cause, confirmed by direct code read: `commands_supervision.py::_force_durable_state_backend()`
(the function `--repo ... --bounded-verified-canary` actually calls) constructs
`default_state_backend()` — `git_backend.py`'s real-`origin`-backed backend — exactly the same
function this whole document is about. `--mission-task-graph ... --mission-action claim` is a
*different* code path (`mission_command.py`) that never touches this backend at all; it mutates the
task-graph's own local state independently. The two claim concepts are stored in unrelated places:
one purely local and always fresh, the other read through `origin` and only as fresh as this
session's last successful `git push`/`fetch` to its own state refs — which, since this session never
pushes (a standing, correctly-enforced safety rule), can silently keep serving whatever was fetched
hours ago no matter how many times the local-only claim path reports success.

**Consequence**: a single-repo canary re-verification of a real code fix — precisely the mechanism
AGENTS.md rule 15 exists to route agents *through*, instead of ad-hoc scripts — can be silently
blocked by this bug in a way indistinguishable, from the CLI's own output, from "someone else has
this task claimed." An agent following rule 15 correctly can still fail to get real end-to-end
proof, through no fault of the code fix being verified. This session did not attempt a workaround
(e.g. forcing the claim via a different mechanism, or bypassing the canary) — that would repeat
exactly the anti-pattern rule 15 exists to prevent. Instead it fell back to the next-most-rigorous
available verification: the real, non-mocked production functions (`build_verified_template_draft`,
`build_template_provenance`) exercised directly by the unit-test suite, including a new full-assembly
regression test and a new claim-accountability/structural-lineage regression test — genuine coverage
of the actual changed code paths, just not proof that the full governed CLI pipeline currently
produces the same result end-to-end for a live repo.

This raises the priority of the fix described above: until `commands_supervision.py` stops depending
on `origin` for `local_poc` state, **no session can reliably re-verify a fix via
`--bounded-verified-canary` after its mission claim has been touched by any earlier
`--mission-task-graph`-only action in the same session** — a real, now twice-independently-confirmed
gap between the two claim mechanisms, not a one-off flake.
