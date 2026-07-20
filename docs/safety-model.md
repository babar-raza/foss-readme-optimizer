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

`data/products.json` is the **only** list of repos this tool is ever permitted to touch.
`registry/loader.py`'s `is_permitted(org_repo)` returns the entry only if it exists **and** its
`mode` isn't `"disabled"`. Every entry point that accepts a repo argument calls this *before* any
network or git operation — not found, or disabled, is a hard `NotAllowlistedError`
(`BLOCKED_NOT_ALLOWLISTED`), with no clone attempted.

This is a named safety property on par with push-blocking, not an incidental consequence of what
happens to be configured: push-blocking stops a write on a repo we're allowed to touch;
the allow-list stops us from ever touching a repo we weren't told to. The base registry is copied
verbatim from Aspose's own real, 25-entry FOSS repo list — every real Aspose FOSS repo is present
in the file, but only 3 have a non-`disabled` mode today. Expanding coverage means flipping
`mode` + adding `ecosystem`/`policy_profile` for an existing entry, never a new file format or a
re-discovery exercise.

## What's NOT a safety control (by design)

- **Preflight** (`preflight/`) is a *quality* gate (don't start work if GitHub/LLM connectivity is
  broken), not a safety gate — it doesn't prevent a write, the two controls above do.
- **Validation** (`validation/`) governs whether a *rendered block* is acceptable content, not
  whether the tool is allowed to touch the repo at all — that's the allow-list's job, checked
  first, separately.
