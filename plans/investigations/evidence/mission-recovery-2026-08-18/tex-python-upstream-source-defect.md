# tex-python: upstream sources are syntactically invalid at the pinned revision (2026-08-18)

## Verdict: GENUINE EXTERNAL BLOCKER (upstream repository defect; no push access)

At upstream `aspose-tex-foss/Aspose.TeX-FOSS-for-Python` revision
`2f4bfab3863e66ef32868f5464685eb4c2d36911` (commit subject "Release 26.5"; the repository's
whole history is now just 2 commits — `311455e Initial commit`, `2f4bfab Release 26.5` — i.e. a
history replacement), **35 of the 45 Python files under `src/aspose_tex/` fail `ast.parse`**
with IndentationError: all leading indentation has been collapsed to a single space (verified
against the *committed* bytes via `git show HEAD:src/aspose_tex/_input/catcode.py`, not just the
working copy; clone worktree is clean). The package cannot even be imported:

```
File "/workspace/.readme-agent-installed/aspose_tex/_input/catcode.py", line 66
    table[c] = Catcode.LETTER
IndentationError: expected an indented block after 'for' statement on line 65
```

## What this proves and supersedes

- The 46ed34630 root cause ("missing product_truth policy block") was real but is no longer the
  binding constraint: the policy block was authored this session (commit `9879f02ff`), the
  cached-facts invalidation gap it exposed was fixed (same commit), the supervised canary
  recollected facts (manifest now carries `product_truth_policy_hash`), `product.capabilities`
  reached `verified`, and the isolated source-build verification genuinely ran — failing on the
  real upstream syntax defect above. Nothing on our side can make an unpublished package with
  unparseable sources verify.
- This also explains the "evidence regression" recorded in commit `2597ff90f`: the earlier
  "TeX DELIVERED clean (12/12)" state was against a previous upstream history that no longer
  exists after the history replacement.

## Correct handling

- Blocked category is genuinely `infra_external` (upstream defect), not `agent_fixable` — same
  class as html-python's `build-backend = "setuptools.backends.legacy:build"` defect, but wider.
- The blocked-decision record (new skip cache) pins this outcome to `source_revision=2f4bfab…`;
  the repository is retried automatically only when upstream publishes a new revision.
- Working-condition presentation lane (Decision #101): a candidate for tex-python may present
  only what is verifiable; with sources unparseable, acquisition/example claims cannot be
  presented. Requires product-owner review for the exception lane.
- Upstream fix needed (for whoever owns the upstream repo): restore properly indented sources
  (the previous working history evidently had them; `run_hello.py` and the tests cannot run
  against the current bytes).
