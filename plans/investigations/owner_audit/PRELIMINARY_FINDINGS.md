# Preliminary owner findings

These findings were established directly while the three deeper audit lanes were still running.
They are inputs to consolidation, not a substitute for the final matrices.

## Current target READMEs are not independent original inputs

The pinned default-branch tips for 3D, Note, and Barcode Python already contain Aspose.org-style
refreshed READMEs. Preservation and quality comparisons must recover the pre-refresh README from
history and keep it separate from the current published README, imported bundle, Aspose candidate,
and optimizer candidate. Otherwise the audit can incorrectly “prove” that generated content was
already present in the source.

Evidence: `repository_pins.md` and read-only GitHub commit/file results.

This also changes the meaning of optimizer's published `3/33 ... NO_OP_PROVEN` milestone. The
optimizer recorded 3D/Barcode/Cells Python no-op proof on 2026-08-19, after Aspose-style README
refreshes had already landed in the target repositories (3D by 2026-08-14; Barcode by
2026-08-15). Those runs can prove preservation, validation, and no-op behavior against an already
strong document; they do not prove the optimizer can compose equivalent quality from the
pre-refresh README. Generation-quality evidence must replay from a sealed pre-refresh commit or a
different unrefreshed repository.

## The current 3D import is partly circular with the refreshed README

The 3D bundle was regenerated at `2026-08-14T11:52:56Z` from repository SHA
`ee05c1ba...`, after the Aspose README refresh had landed on 2026-08-04 and after the final
Mermaid-only repair at that exact SHA on 2026-08-14 09:56Z. Its own delta declares the transition
from pre-refresh SHA `ab1a2267...` to refreshed SHA `ee05c1ba...` and adds 165 claims.

Direct reconciliation of `knowledge_delta.json` with `claims.json` shows:

- 35 of those 165 new claims cite `README.md` as evidence;
- 32 of the 35 use the refreshed README as their only evidence;
- examples include the newly documented COLLADA limitation and the refreshed document's exact
  capability language.

This means the current 3D knowledge corpus is useful operational context but is not an independent
oracle for evaluating whether the optimizer can recreate Aspose-quality prose. Generation-quality
calibration must exclude post-refresh README-derived claims or rebuild the knowledge snapshot from
the sealed pre-refresh source tree. Source-code corroboration can still validate a claim later, but
the target README must never be accepted as its own upstream evidence.

## Imported 3D/Python knowledge is fresh by SHA but internally contradictory

`data/imported/knowledge/3d/python/merged/model.yaml` records
`repo_sha: ee05c1ba9153ef5916b7a108406c794f2e464d01`, exactly matching the current target tip.
Consequently the optimizer classifies the bundle as `current`.

The same imported bundle simultaneously contains:

- `formats.md`: `FBX | Yes | Yes`;
- enriched feature claim `ERC-3d-python-338c230c`: a “unified API” for FBX through
  `FbxImporter`/`FbxExporter`;
- enriched feature claim `ERC-3d-python-8e9815fe`: FBX save controls;
- scout limitation claims `CLM-3d-f966ea` and `CLM-3d-31f56e`: both FBX exporter methods raise
  `NotImplementedError`;
- `limitations.md`: the exact exporter failures;
- `model.yaml`: `has_conflicts: false`.

The current published README correctly warns that FBX export is unimplemented/experimental, so
the structured imported format assertion is weaker than the published document it is supposed to
support.

This proves that SHA freshness is not semantic consistency and that imported positive capability
claims require polarity/conflict reconciliation with limitations and executable evidence.

## Aspose's format gate contains valuable incident learning but is not a semantic oracle

The packaged Aspose check deliberately distrusts `formats.md` and requires 2 of 3 signals for a
diagram import/export label: the formats table, candidate prose, and a source-name signal. That is
useful, incident-hardened behavior and should inform the optimizer.

However, two signals are weaker than their names imply:

- candidate prose is written by the same composition pass as the diagram, so it is consistency,
  not independent truth;
- source evidence is lexical: a class/file name containing the format plus an import/export suffix
  is enough, without checking whether the method body is implemented or raises a stub exception.

For 3D/Python FBX, a table row plus `FbxExporter`'s existence can therefore corroborate an export
claim even though its methods raise `NotImplementedError`. The published README is correct because
the expert composition/review process noticed the limitation, not because this gate makes the
error impossible. The optimizer should reuse the multi-signal intent while strengthening source
evidence with implementation/polarity checks and preventing candidate prose from counting as an
independent fact.

## Fact-level verification can launder unverified claim items

At optimizer commit `6d112bbf`, `aspose_knowledge_selection.py`:

1. treats a current-bundle, uncorroborated claim as output-eligible with item state `unverified`;
2. groups up to eight selected items into one `FactRecordV2` per field;
3. marks the whole fact record `verified` when **any** selected disposition in that field is
   verified (`verified_any`);
4. stores no per-item verification state in the fact value—only claim ID, kind, text, confidence.

Therefore one file-existence-corroborated item can make a mixed fact record mechanically appear
verified even when other selected items are unverified. Downstream consumers that authorize by
fact ID cannot recover the lost item-level distinction.

This is potentially publication-blocking. The deeper lane must quantify whether it occurs in real
3D/Note/Barcode selections and trace whether candidate provenance authorizes all items through the
single fact ID.

## Non-license “corroboration” does not corroborate claim meaning

The current selector calls a non-license claim corroborated when any `evidence[].file` still
exists. It does not check the cited line, symbol, snippet, implementation body, polarity, or whether
the file supports the claim.

Additionally, enriched claims commonly use `evidence[].source_file`, whereas the selector reads
only `evidence[].file`. Those enriched claims are therefore treated as uncorroborated even when
they carry source evidence. Current-bundle freshness can still make them output-eligible, creating
an inconsistent trust path.

## Imported bundle freshness differs across the calibration trio

- 3D/Python imported `repo_sha` matches current target tip exactly.
- Note/Python imported `repo_sha` is `6d97a522...`, while current target tip is `41de2e8a...`.
- Barcode/Python imported `repo_sha` is `53f2c335...`, while current target tip is `06eca5c0...`.

The trio therefore exercises both current and stale selection paths. This is useful, but results
must not be combined without reporting freshness and corroboration separately.

## The imported corpus structurally excludes both admitted PSD repositories

The optimizer registry contains 33 family/platform entries. The imported Aspose product registry
and knowledge tree contain 31. The exact optimizer-only pairs are `psd/net` and `psd/python`.

At current `aspose_knowledge_claims.py`, a product/platform absent from the imported corpus's own
registry is reported as `product_platform_not_in_imported_corpus` with `agent_fixable=False`.
That is truthful about the historical import, but it is not sufficient for the optimizer's 33/33
goal: the two admitted README-only PSD repositories then have neither source-derived code facts nor
imported product knowledge. A first-class README-only mode cannot be proven until the PSD lane
supplies/imports an authoritative corpus or a governed equivalent and the absence is treated as a
portfolio coverage gap rather than a harmless non-applicability.

## The latest optimizer commit changes coordination, not README quality

During this audit, optimizer main advanced from `6d112bbf...` to `d71f38b6...`. The intervening
commits install/repair a control-repository `post-commit` auto-push hook and restore a green
hermetic test baseline. They do not alter facts, composition, review, validation, reconciliation,
caching, or hosted candidate execution, so the quality findings pinned to `6d112bbf...` remain
valid. The current reported suite is 4,207 passed, 1 skipped, 1 xfailed, 0 failed.

Two operational limits should remain explicit: the hook checks only that `origin` is not the exact
neuter marker rather than allowlisting the expected control-repository identity, and a post-commit
push rejection is reported but not stored as durable retry work. This is not a reason to stop the
quality campaign, but the commit must not be counted as progress toward 33/33.

## The existing Qwen fallback does not cover the observed failure

At current main, the canonical merged reviewer is fixed at 4,000 completion tokens and one
transport/response attempt. `execute_merged_readme_review` does contain an isolated blind-review
fallback, but it is reached only after a successfully parsed merged response whose quality facet
then fails grounding. If the merged call itself ends in truncated/malformed tool arguments, or if
the top-level `quality`/`factual` object is invalid, execution raises before that fallback. The
factual facet has no separated fallback at all.

Therefore the existing fallback cannot recover the exact committed Qwen failure
(`finish_reason='length'` with truncated JSON). The smallest repair is to catch merged transport,
parse, and top-level schema failure and invoke the already-existing separate blind and factual
clients, preserving the same deterministic reducer and bounded repair loop.

## A historical AGENT_APPROVED/NO_OP_PROVEN candidate contains a false approval

The committed finalized 3D/Python optimizer evidence is not merely older than the knowledge layer;
it demonstrates that the review contract can approve an overgrown and materially inaccurate
candidate:

- source revision `62fb89f3...` is already the merge of Aspose's refresh, not an unrefreshed input;
- optimizer candidate `5735c3f6...` is 76,093 bytes with 380 Markdown table rows, versus the
  18,087-byte already-refreshed source README at that run and the 41,441-byte Aspose canonical
  candidate in the supplied bundle;
- the merged blind reviewer records only two supporting quality findings, both structural;
- the factual reviewer records only two supporting factual findings, then declares all material
  claims supported;
- the candidate's API table says `NurbsSurface` supports converting content to mesh even though
  its source method raises `NotImplementedError`;
- the evidence still records `AGENT_APPROVED` and later `NO_OP_PROVEN`.

This is direct proof that no-op means reproducibility of the optimizer's accepted bytes, not quality
parity or factual completeness. Reviewer acceptance must be coverage-bound: every material claim
or claim group needs an inspected disposition, and comparison against the Aspose candidate must be
part of calibration before the status can support a 30/30 or 33/33 quality statement.

## Knowledge-application evidence currently proves selection, not output use

`product_truth.py` writes `knowledge-application.json` during fact preparation and calls
`build_knowledge_application_report` without a document plan. Consequently the artifact's
`sections_influenced` and `rendered_output_spans` are necessarily empty. The evidence module's
docstring claims `readme/idea_candidate.py` writes it again after rendering, but current main has no
such call.

Even adding that call verbatim would not cover the verified-template route: its broad compile
operation has no knowledge fact IDs, while its useful lineage lives in candidate-content
provenance. The repair should therefore produce one post-render report from the actual candidate,
document plan, and candidate-content provenance; it must account for each selected item as
rendered, preserved-equivalent, superseded, or omitted-with-verified-reason. A pre-render report may
remain as planning evidence, but must not be presented as proof of visible influence.
