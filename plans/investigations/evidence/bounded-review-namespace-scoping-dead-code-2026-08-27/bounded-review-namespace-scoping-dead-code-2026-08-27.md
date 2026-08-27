# Bounded review's namespace-scoping fallback is dead code, causing hard structural failures on large APIs

## Status

Root-caused with a direct, live reproduction. Not fixed: the correct repair
needs a real design decision on how to reliably recover a table unit's owning
namespace (the current signal -- regex-searching the table's own rendered
text -- structurally can never work, as explained below), not a one-line
patch. Unlike RDM-029/RDM-030, this file is **not** contract-bound
(`bounded_review_packers.py` matches none of `document_templates.py`'s
`DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS`/`_GLOBS`), so a fix here would carry
no portfolio-wide cache-invalidation cost -- a lower-risk, cheaper fix to
schedule than RDM-029's.

## Symptom

`aspose-3d-foss/Aspose.3D-FOSS-for-.NET` fails identically across at least
two independent fleet passes on 2026-08-27 (`fleet-post-rdm030-20260827.log`,
`fleet-post-heal-20260827.log`), both after the RDM-030 fix had already
landed and was confirmed unrelated:

```
specialist_failed:readme_presentation:ERROR:independent_review_exception:
RuntimeError: bounded review is structurally blocked:
('unpacketizable-oversized-factual-unit-0048-table',)
```

## Root cause

`_build_factual_packets()`
(`src/readme_agent/specialists/bounded_review_packers.py:206-360`) tries to
avoid busting its `budget_chars` (120,000, `DEFAULT_BOUNDED_PACKET_BUDGET_CHARS`
in `bounded_review_contracts.py`) on a namespace table's cited
`api.public_surface` fact by narrowing that fact's `classes`/`modules` down to
just the one namespace the table belongs to
(`_bounded_fact_payloads()`, lines 70-155). It detects which namespace via:

```python
namespace_match = _API_NAMESPACE.search(unit_text)  # r"Namespace \(`([^`]+)`\)"
if namespace_match is None:
    return [_compact_bounded_review_fact(payload) for payload in payloads]  # UNSCOPED, full fact
```

`unit_text` here is the table unit's *own* rendered text only. Confirmed via
`bounded_review_structure.py:127-145`: a `kind="table"` unit's `char_start`
begins at the table's own header row (`| Type | Description |`); the
preceding `### X Namespace (\`Y\`)` markdown heading is a **separate**,
earlier unit. A namespace table's own body therefore never contains the
literal string `Namespace (`...`)` the regex is searching for, so
`namespace_match` is **always** `None` for every namespace table in every
repository -- the scoping optimization is dead code, silently falling back to
the complete, unscoped `api.public_surface` fact every time.

This has been invisible until now because most repositories' complete
`api.public_surface` fact, even unscoped, stays under the 120,000-char
budget by coincidence. Confirmed live for the affected repository: the
complete fact serializes to **1,251,842 characters** (over 10x the budget),
while the *actually rendered* API reference table across all three real
namespaces (Core API, Enumerations, Interfaces) is only 26,438 characters
total (292 rows, longest single description 121 chars) -- the entire
oversized-unit failure is caused by the unscoped fallback, not by the table's
real rendered content.

**Ruled out**: this is unrelated to RDM-030. The RDM-030 disambiguation fix
(`verified_template_api_reference.py`) never fires for this repository at
all -- confirmed directly (`api_reference_markdown()` for this repo's facts
contains zero `Declares` clauses, meaning no description collisions exist
here).

## Attempted fix (2026-08-27, reverted -- makes the symptom worse)

Implemented direction 1 above (threaded the section's raw heading-unit text
through `_bounded_fact_payloads` as a `heading_text` fallback for
`_API_NAMESPACE`, wired through both call sites in `_build_factual_packets`).
Unit tests passed (20/20 in `test_bounded_review_packets.py`, including a new
regression test proving the regex now matches against a realistic
heading-separate-from-table `unit_text`). But a **live retry against the real
failing repository made it worse**: `aspose-3d-foss/Aspose.3D-FOSS-for-.NET`
went from one oversized unit (`unpacketizable-oversized-factual-unit-0048-table`)
to two (`'unpacketizable-oversized-factual-unit-0040-table',
'unpacketizable-oversized-factual-unit-0048-table'`), and unit 0048 still
failed even with scoping now working.

Root cause of the regression: `composition_fact_payloads()` already runs
every fact through `compact_prompt_fact_value()`
(`readme/agentic_composition_inputs.py:126-166`) before the namespace-scoping
logic ever runs -- for `api.public_surface` this is a deliberately lossy,
capped summary (`_MAX_PROMPT_API_ITEMS`-sliced module/export/class lists),
independent of which namespace the table belongs to. Measured directly: for
this repository's `api.public_surface` fact, that generic capped summary
serializes to only ~3,572 characters -- small, because it's an
already-bounded *sample* across the whole API, not a per-namespace listing.
The namespace-scoped projection this fix enables, by contrast, returns
*every* class and *every* summary member for the one real namespace with no
cap -- measured at ~45,622 characters for the "Core API" namespace alone.
Making the scoping regex actually match did what it was designed to do
(swap the generic capped sample for a complete, namespace-accurate listing),
but for a namespace this large, "complete and accurate" is bigger than
"capped and generic" -- the literal opposite of what the scoping is there to
achieve (fitting inside the budget).

Reverted immediately (`git checkout` before committing) rather than ship a
regression. The correct fix must not treat "namespace match found" as
unconditionally better: it needs to fall back to the generic capped summary
whenever the namespace-scoped projection would be larger, not only when the
namespace can't be identified at all. This still needs a design decision
(cap classes/members within the namespace projection too? compare both
payload sizes and take the smaller? something else?) and a new/updated
regression test that asserts using neither payload alone regresses size for
a large synthetic namespace -- not attempted further in this pass.

## Correct repair direction

`_MutableUnit` already tracks `section_path` (a slugified heading-ancestry
string built via `heading_identity(title)` in
`bounded_review_structure.py:68-88`, e.g. the observed real packet ID
`pkt-factual-0014-api-reference-core-api-namespace-core-api-2aaff4e6bc26`
shows the slug does carry the namespace name through, just in slugified,
not raw, form). Two compatible directions:

1. Thread the table unit's owning section's *raw* heading title (not just its
   slug) through to `_bounded_fact_payloads`, so the existing `_API_NAMESPACE`
   regex can run against the correct text (the heading, not the table body)
   instead of changing the regex itself.
2. Or: slugify each candidate `module` name from the fact's `modules` list the
   same way (`heading_identity`) and match it against `unit.section_path`'s
   last segment, without needing to recover raw title text at all.

Either way, this needs a design decision (which signal to standardize on,
whether to change `_MutableUnit`'s schema) and a real regression test proving
a large synthetic API surface no longer produces an oversized-unit failure --
not a one-line patch, and not attempted in this pass to avoid rushing a fix
into review-packetization logic without adequate test coverage.

## Traceability

Found while investigating a recurring "unpacketizable-oversized-factual-unit"
failure on `aspose-3d-foss/Aspose.3D-FOSS-for-.NET`, live during the 2026-08-27
post-RDM030 fleet passes.
