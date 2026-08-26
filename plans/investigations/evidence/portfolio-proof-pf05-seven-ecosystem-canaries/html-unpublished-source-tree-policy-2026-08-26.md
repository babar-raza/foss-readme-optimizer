# PF05-ACQUISITION-POLICY-001 — an unpublished package with a broken build backend cannot pass acquisition ground truth, even when the fallback is honest and fully explained

## Status

Root-caused. Not repaired: this is a deliberate safety/trust policy, not an
obvious bug, and I am not confident enough about its intended strictness to
loosen it unilaterally.

## Symptom

`aspose-html-foss/Aspose.HTML-FOSS-for-Python` blocks:

```
bundle_verification_rejected: {'name': 'aspose-html-foss'} is NOT published
(PyPI: aspose-html-foss NOT FOUND (404)) but the bundle's facts record
method='source_tree' -- an unpublished package cannot be verified
```

## What actually happened, per the facts themselves

`installation.verified_acquisition` already records the full story, including
*why* `source_tree` was used instead of `source_build`:

```json
{
  "method": "source_tree",
  "outcome": "SOURCE_TREE_VERIFIED",
  "detail": "exact public Python imports/example executed from the immutable
             source tree; package installation is blocked by an invalid
             build backend"
}
```

This is not a facts-extraction defect. The collector correctly detected that
`pyproject.toml`'s build backend is broken, correctly could not produce a real
`source_build` (pip install) receipt, and correctly fell back to the weaker but
honest `source_tree` evidence tier -- with the reason recorded, not hidden.

## The actual gate

`verification/acquisition_ground_truth.py::verify_acquisition_ground_truth()`
re-resolves the package against the live PyPI registry and enforces: an
unpublished package (`result.found is False`) is accepted *only* when
`recorded_method == "source_build"`. `source_tree` is rejected unconditionally,
regardless of why `source_build` was unavailable.

That is a deliberate, real safety property -- distinguishing a genuine
sandboxed pip-install proof (`SourceBuildReceiptV1`: `network_mode="none"`,
`immutable_image`, `cleanup_complete`) from a weaker source-tree import check
(`SourceTreeReceiptV1`) that does not prove a real user's `pip install` would
work. Loosening it changes what installation claim the pipeline is willing to
publish. Not fixed here because I am not confident this is meant to have an
exception for "the build genuinely cannot succeed, and here is proof why" --
that is a product-policy judgment, not a code defect I should resolve
unilaterally mid-pass.

## Repair direction (for whoever owns this policy decision)

If an honest, fully-explained `source_tree` fallback should be an acceptable
final tier for a repository whose build backend is provably broken (as opposed
to one that simply never attempted `source_build`), `verify_acquisition_ground_truth()`
could accept `method == "source_tree"` specifically when `outcome ==
"SOURCE_TREE_VERIFIED"` and a `detail` naming a build-backend defect is present
-- and the resulting README should then also carry the upstream defect
explicitly (per the working-condition-presentation policy: show verified-working
functionality, log the unverifiable as an UPSTREAM-DEFECT), not silently soften
the installation story. If not, the intended remedy is fixing
aspose-html-foss's `pyproject.toml` build backend upstream so `source_build`
becomes achievable, which is out of scope for this pipeline.

## Why it was not fixed here

`acquisition_ground_truth.py` is not contract-bound, so a fix would not have
re-staled cached work. It was deferred anyway because this is a deliberate
trust/safety gate whose correct scope I am not certain of, not an
unambiguous defect like the other findings this session.
