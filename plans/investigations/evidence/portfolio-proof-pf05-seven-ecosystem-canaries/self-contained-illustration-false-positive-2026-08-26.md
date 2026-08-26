# PF05-DEPCHECK-001 — "self-contained illustration" false-flagged as a dependency-absence claim

## Status

Root-caused with an exact reproduction. Not repaired: the offending file is
inside the `aspose_checks` fact-acceptance component
(`facts/acceptance_contract.py::_COMPONENT_FILES`), so the fix batches with the
other contract-affecting repairs found this session rather than landing mid-run.

## Symptom

`aspose-cells-foss/Aspose.Cells-FOSS-for-Python` blocks with
`check_unqualified_dependency_claims[document]: unqualified absolute
dependency-absence claim` from the vendored aspose.org check battery.

## Reproduction

```python
from readme_agent.validation import aspose_checks
aspose_checks._ensure_vendored_on_path()
import readme_refresh_checks as rrc
rrc._unqualified_dependency_claim_findings(candidate_text)
# -> {'phrase': 'self-contained',
#     'context': 'self-contained illustration of introductory public API usage in Python.', ...}
```

## Root cause

`readme_refresh_checks.py`'s own pattern already exists to allow exactly this
kind of phrase:

```python
r"\bself[- ]contained\b(?!\s+(?:example|snippet|sample|version))",
```

The negative lookahead excludes "self-contained example/snippet/sample/version"
-- but the candidate uses **"illustration"**, a synonym not in that list, so the
exclusion never engages and "self-contained" is flagged as an absolute
dependency-absence claim. The sentence is describing the example code
(self-contained, i.e. runnable without external setup), not asserting anything
about the product's dependencies at all -- a real false positive, not a
borderline case.

## Repair direction

Add "illustration" (and any other synonyms actually produced by the composer --
"demo", "demonstration", "walkthrough") to the exclusion list on line 8626 of
`readme_refresh_checks.py`. Narrow, in keeping with the file's own established
pattern of fixing exactly the phrase found against real content (its comments
document several such fixes already, e.g. the cells/rust "no external runtime"
case).

## Why it was not fixed here

The file is one of `_COMPONENT_FILES["aspose_checks"]` in
`facts/acceptance_contract.py`, so editing it changes that component's
acceptance-contract hash. A fleet pass was in flight when this was found; the
fix batches with PF05-APIREF-BACKTICK-001 (already landed) and any other
queued contract-affecting repairs for the next full re-run.
