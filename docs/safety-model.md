# Safety model

Two independent, named safety properties. Neither depends on the other; both are proven, not
assumed.

## 1. Push-blocking

Even though `GH_TOKEN`/`GITHUB_PAT` are write-capable on every target repo, this tool never
issues a write verb. Defense in depth, two independent controls:

1. **Push-neutering** (`gitsafety/neuter.py`): `git remote set-url --push origin DISABLED` on
   every work clone. `DISABLED` is not a resolvable URL, so `git push` fails structurally, not by
   policy alone.
2. **Pre-push hook** (`gitsafety/hooks.py`): `.git/hooks/pre-push` unconditionally exits 1 with a
   loud message. Belt-and-suspenders in case the remote URL is ever restored by mistake.

`gitsafety/verify.py`'s `verify_push_blocked()` re-derives proof of both from `git remote -v`
output and the hook file's actual contents — **never by attempting a real push**. This is called
once right after setup (hard-abort if it fails) and recorded in every evidence manifest.

**Proven, not just asserted**: `tests/unit/test_gitsafety.py::TestHookActuallyBlocksARealPush`
performs a real `git push` against a real (local, disposable) bare repo and asserts it fails with
the hook's marker string — the automated equivalent of manually confirming this on a dev machine,
and it re-runs on every CI build, on every OS the test matrix covers.

On Windows, the hook's executable bit is meaningless (NTFS) and is recorded but explicitly
excluded from the pass/fail verdict — Git for Windows invokes hooks via its bundled shell
regardless of the bit, not silently assumed to pass.

**Any future exception is a human-confirmation gate, not a code toggle.** If a `gated_effector`
capability is ever built to make a real write, lifting push-blocking for it is never a silent
config flip: `GOV-018` (`plans/master.md` decision #33, `plans/GOVERNANCE.md` rule 10) requires an
explicit, per-instance user confirmation naming exactly what is being pushed, why, and where,
before that write happens — a standing or implied approval from earlier never substitutes.

## 2. The allow-list

`data/products.json` is the **only** list of repos this tool is ever permitted to touch. Not
being in that file is always a hard `NotAllowlistedError` (`BLOCKED_NOT_ALLOWLISTED`), with no
clone attempted, for any operation. Beyond that, the gate splits by intent (decision #40,
`plans/master.md`):

- **Read-only capabilities** (`profile_repository`, `get_product_facts`,
  `detect_readme_gaps`, `classify_upstream_change`, `inspect_repository`, and `supervise_repo()`'s
  own entry gate) call `registry/loader.py`'s `require_listed(org_repo)`, which only checks
  presence in the file — `mode` is irrelevant. `mode: "disabled"` means push access to that org
  hasn't been verified yet, not that the repo is off-limits to read; a disabled entry is cloned
  and profiled/inspected the same as any other.
- **Write/push-capable operations** — `orchestrator.py`'s `generate_repo()`/`run_repo()`
  render+commit pipeline, and any `local_write`/`remote_write` capability — still call
  `is_permitted(org_repo)`/`require_permitted(org_repo)`, which returns the entry only if it
  exists **and** its `mode` isn't `"disabled"`. A write-capable capability dispatched through the
  supervisor is independently re-checked against `mode == "full"` at dispatch time
  (`supervisor/loop.py::_dispatch_and_record()`), since the supervisor's own entry gate no longer
  implies it.

This is a named safety property on par with push-blocking, not an incidental consequence of what
happens to be configured: push-blocking stops a write on a repo we're allowed to touch;
the allow-list stops us from ever touching a repo we weren't told to at all, and from ever writing
to one we haven't been told is ready for that. The base registry is copied verbatim from Aspose's
own real, 25-entry FOSS repo list — every real Aspose FOSS repo is present in the file and can be
read/analyzed, but only 3 have a non-`disabled` mode today, so only those 3 can be written to.
Expanding write coverage means flipping `mode` + adding `ecosystem`/`policy_profile` for an
existing entry, never a new file format or a re-discovery exercise.

The allow-list stays current by two paths sharing one implementation
(`registry/discovery.py`): the weekly `update-products-registry.yml` cron, and the
supervise-time runtime self-heal (`registry/self_heal.py`, `CORE-034`, decision #47) that runs
before each `supervise` invocation's gates. Both can only **add `disabled` entries** and refresh
upstream-shaped fields — neither can enable, delete, or touch `mode`/`ecosystem`/
`policy_profile` on any existing entry, and the heal re-validates every merged entry against the
loader's schema before replacing the file. The one posture consequence, stated plainly: a
self-healed entry becomes *read*-eligible (`require_listed()`) immediately, without waiting for
PR review — bounded by the human-curated `data/families.json` org list and the FOSS naming
convention; the write surface is unchanged. In CI, a healed registry diff surfaces as a pull
request on the same branch as the weekly cron's — never a direct push to `main`.

## What's NOT a safety control (by design)

- **Preflight** (`preflight/`) is a *quality* gate (don't start work if GitHub/LLM connectivity is
  broken), not a safety gate — it doesn't prevent a write, the two controls above do.
- **Validation** (`validation/`) governs whether a *rendered block* is acceptable content, not
  whether the tool is allowed to touch the repo at all — that's the allow-list's job, checked
  first, separately.
