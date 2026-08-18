# S1 residue closure map — every blocked claim, literal text, and its fix lane (2026-08-18)

Extracted by byte-offset + hash verification from the live blocked-decision records against the
real source READMEs. 13 distinct claims across 6 repos. The classification flips E5's strategy:
most of the residue closes DETERMINISTICALLY; the LLM disposition path is the tail, not the
main road.

## Lane A — render aspose.org's full four-H3 Dependencies contract (~5 claims)

aspose.org's `## Dependencies` always carries four fixed H3s (Required Package / Optional /
Native and System Requirements / Development). Ours renders a data-only fragment (and nothing
at all when empty). Rendering the full contract from VERIFIED facts makes these survive
mechanically, zero LLM:

- `7ff54c1da64deecb` (page; also in note/email sources): "No required third-party package
  dependencies." → Required H3, verified-empty statement (prepared-change spec already filed).
- `c5ac180c4dd86b4f` (barcode): "`pytest` >=8.0 and `ruff` >=0.15.7 — used only by the test
  suite…" → Development H3.
- `705af7d28e6bee27` (slides): "`pytest` — the test framework used by this project's own test
  suite." → Development H3.
- `487872b120b8b7f7` (email): "Ships as pure Python source with no compiled extensions… no
  native/system libraries" → Native and System Requirements H3.
- `f76ee53ac612c3f9` (font): "No native system libraries: WOFF2's Brotli… vendored pure-Python
  codec" → Native and System Requirements H3 (vendored-codec fact must be verifiable from the
  source tree — it is: `aspose_font._brotli`).

## Lane B — richer Key Capabilities composition from the already-complete fact set (~6 claims)

All are dense capability bullets from the aspose-refreshed originals; the facts to back them
are already extracted (the Q2 verdict proved the fact set is complete). Composition currently
selects the shortest passing claims (Q1); selecting these makes them survive:

- barcode `54e67ed0a47ae8af` (symbology-by-name via `generate()`)
- font `3523960e3ec2b571` (TTF/OTF/CFF/Type1/WOFF/WOFF2/EOT load surface),
  `1fd567b607a0b92d` (`font.convert()` / `FontConverter.convert`)
- slides `2bc98aaeabb4169c` (`Presentation` context manager), `54d82973f22d7ad3`
  (`SlideCollection` operations), `f50f4fa850bc06b9` (57 `TransitionType`s),
  `21eb063fe20e3f46` (`Theme` via `prs.master_theme` — ALSO cleared by the api_method_index
  property fix, see slides triage)

## Lane C — E5 disposition path (the true tail, ~2 claims)

- note `0d4d28fef68b38fd`: the fixture-dependent Quick Start code block
  (`Document("SimpleTable.one")`) → `unverifiable_fixture_dependency` exclusion or verified
  replacement (E5 slice 1, in flight on the worktree branch).
- Anything Lane A/B leaves over after their canaries.

## Sequencing

Lane A (one renderer change) → Lane B (composition selection) → Lane C mops up. Canaries per
lane: page (A), font (B), note (C). Each lane's success is measurable as specific claim ids
disappearing from blocked-decision records with zero disposition provider calls.

## Lane A CONFIRMED LIVE: page-python fully unblocked (2026-08-18, post-merge canary)

Re-ran the page-python canary against merged main: `source:claim:4538:7ff54c1da64deecb` (the
empty-Dependencies boilerplate sentence) no longer blocks at all. page-python advanced straight
through to **`CONVERGED_PROPOSAL_READY` / `AGENT_APPROVED`** — the independently-reviewed local
README boundary — with only 2 provider calls total (no `claim_disposition_check` needed; the
claim now survives mechanically via the rendered Dependencies section). This is the clearest
positive proof point of the whole recovery: a repository that was blocked at session start is
now fully approved, closed by a purely deterministic rendering fix with zero LLM involvement in
closing that specific claim.

Portfolio effect: page-python should register a fourth `AGENT_APPROVED`/candidate-ready
repository on the next portfolio pass (pending its own NO_OP_PROVEN re-verification).
