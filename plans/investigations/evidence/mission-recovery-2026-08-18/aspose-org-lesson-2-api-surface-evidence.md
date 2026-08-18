# Second aspose.org lesson: API-behavior claims verify against extracted facts, not raw text

## What was investigated

After landing the fixture-existence fix (lesson 1: `testfiles/SimpleTable.one`), continued
directly investigating aspose.org's `content-dispositions.json` for barcode-python, targeting
the EXACT claim still blocking our pipeline: `source:claim:2626:54e67ed0a47ae8af` — "Select any
symbology by name — canonical or alias — through the generic `generate()` entry point,
independent of the dedicated per-symbology helpers."

## What aspose.org does (unit_id u0017, `content-dispositions.json`)

```json
{
  "classification": "2_mechanism_explanation",
  "disposition": "merged_verbatim",
  "verification": {
    "status": "verified_against_source",
    "evidence_type": "clone_cache_path",
    "evidence_ref": "src/aspose_barcode_foss/api.py",
    "evidence_note": "generate(symbology, data, *, encode=None, render=None) confirmed public."
  }
}
```

**No `evidence_quote` field at all.** Instead, `evidence_note` is a human-readable confirmation
that a specific, real function signature (`generate(symbology, data, *, encode=None,
render=None)`) genuinely exists and is public. This is a THIRD verification shape, distinct
from both patterns already implemented this session:

| Shape | What's checked | Where it applies |
|---|---|---|
| Text-quote match | exact substring in a real text file | prose claims backed by literal source/doc text |
| Existence-only | named file genuinely exists (lesson 1, landed) | claims naming a real binary/data fixture |
| **API-shape match** | a described member's real, extracted signature/kind confirms the claim | claims that are EDITORIAL PARAPHRASE of a real API member's behavior (this lesson) |

## Why our current mechanisms structurally can't do this

- `_covered_by_fact_variants` (the mechanical gate) demands every substantive character of the
  claim reconstruct from pre-extracted fact PHRASES — but "canonical or alias" and "generic
  entry point" are the ORIGINAL AUTHOR'S EDITORIAL FRAMING of the fact "`generate` is a public,
  symbology-agnostic entry point," not a phrase that exists verbatim anywhere in extracted data.
  Root-caused precisely in `claim-accountability-blocking-analysis.md` earlier this session.
- The `verified_against_source` LLM path (even after lesson 1's fix) requires either a literal
  text quote from a file, or — now — existence of a NAMED FILE. Neither fits "this paraphrase
  accurately describes a real function's real signature," which is a STRUCTURED fact match
  (does `generate` exist, is it public, does its parameter shape match what's implied), not a
  textual one.
- **Crucially, we already extract exactly the structured fact aspose.org's `evidence_note`
  encodes**: `src/readme_agent/facts/aspose_detectors.py::ApiSurfaceMemberV1` carries a real
  `signature: str` field (e.g. `generate(symbology, data, *, encode=None, render=None)`) per
  public member. The gap is not missing data — it is that `claim_disposition_check`'s
  corroboration path has no way to consult it.

## Proposed fourth evidence path (design, not yet implemented — scoped for delegation)

A new `evidence_type: "api_surface_member"` for `verified_against_source`:

- `evidence_ref` = the bare member name, copied verbatim as inline code from the claim text
  (mirrors the existing `unverifiable_fixture_dependency` predicate's "copy verbatim from the
  claim" safety pattern — the model cannot invent a name, only confirm one the claim already
  names).
- Corroboration (pure, deterministic, in `verification/claim_disposition.py`): the named
  member must appear as a real member of the extracted API-surface facts (reuse
  `ApiSurfaceMemberV1`/the same source `_source_mentioned_bare_names`-style bare-name matching
  already proven in `verified_template_api_method_index.py`), AND `evidence_quote` must be
  empty (this is a shape confirmation, not a text quote — same discipline as lesson 1).
- **Deliberately NOT** free-form "does this paraphrase accurately describe the signature" —
  that would require trusting the model's semantic judgment, exactly the failure mode this
  whole investigation has been fighting. The safe, minimal claim is narrower: "this claim is
  ABOUT a real, publicly-confirmed member" — which is enough to let claims like barcode's
  `u0017` through without accepting an unverifiable behavioral assertion riding along with it.
  A behavioral claim whose real signature contradicts what's asserted stays a separate,
  harder problem, out of scope for this pass.
- Needs `ProductFactsV2`/the API surface threaded into `corroborate_claim_disposition()` and
  its callers (`check_claim_disposition`, `llm_verified_claim_disposition`,
  `build_readme_claim_accountability_map`) — a real, multi-file signature change, comparable in
  scope to E5 slice 1.

## Disposition

Delegated to an isolated worktree lane (`mission-recovery/api-surface-evidence`), following the
exact rebase-review-gate-merge discipline established this session for graph-loader/E5/Lane-A-B/
lockfile. Canary target: barcode-python's `u0017`-equivalent claim
(`source:claim:2626:54e67ed0a47ae8af`).
