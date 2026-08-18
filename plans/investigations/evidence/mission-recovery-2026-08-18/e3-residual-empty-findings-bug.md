# E3 residual: `product_truth_blocked_category([])` silently defaults to `agent_fixable`

Live-verified 2026-08-18 (read-only investigation, no runtime edits — driver was active):
html-python's persisted `findings.json` for its latest fact bundle
(`912f0ae078b5418226a51de08539bc591547682e`) is an **empty list**, even though its
`installation.verified_acquisition` fact IS genuinely blocked with a `BUILD_FAILED`-shaped
value (verified directly against `product-facts.json`). Its blocked-decision record still
carries `blocked_category: agent_fixable` — the E3 fix (`17f8cc595`) is real and correct for
the case where a finding EXISTS, but a second, distinct defect means this particular bundle
never reached that finding-construction code at all in a way that populated it.

## Root cause (traced, not guessed)

`product_truth.py::product_truth_blocked_category`:
```python
def product_truth_blocked_category(findings: list[dict]) -> BlockedCategory:
    if findings and all(
        finding.get("blocked_category") == "infra_external" for finding in findings
    ):
        return "infra_external"
    return "agent_fixable"
```
`if findings and all(...)` — Python short-circuits on the empty list, so **an empty findings
list returns `agent_fixable` unconditionally**, the same as a genuinely-agent-fixable non-empty
list. There is no way to distinguish "no findings were ever computed" from "computed findings
say this is our fault" from the return value alone.

Separately, `findings` is populated in `prepare_local_product_truth` only when
`_facts_need_resolution(facts)` is True AND no salvage candidate exists
(`product_truth.py:419-440`) — a cached/salvaged bundle can legitimately carry zero findings
that were never (re)computed under the current classification logic, especially one whose
underlying fact bundle predates a classification fix.

## Disposition

Not fixed this session (runtime source; driver active; this is additive-only investigation).
Two-part fix for a future pass: (1) `product_truth_blocked_category` should distinguish
"no findings computed" from "findings say agent-fixable" — e.g. return a third state or require
callers to force finding recomputation before trusting the category; (2) verify whether
`load_prepared_product_truth`'s cache-reuse path should force-recompute findings when the
fact-acceptance contract or verifier-code fingerprint changed (it already invalidates the whole
bundle on those triggers per the existing gate — so this may resolve itself once html's bundle
is genuinely recomputed under current code; needs confirmation on the NEXT live derivation,
not assumed).

## Not urgent

This does not block portfolio progress (html is a documented genuine external blocker either
way — see `tex-python-upstream-source-defect.md` for the sibling case). It matters for
Decision-#101 working-condition-presentation triage, where the category determines whether a
repository routes to the human product-owner exception lane. Recorded so the next pass doesn't
re-discover it as a mystery.
