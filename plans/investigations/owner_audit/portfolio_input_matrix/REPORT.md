# Portfolio Input and Readiness Audit

## Decision summary

The 33-row optimizer registry is source-accessible, but the portfolio is not input-ready for a trustworthy autonomous 33/33 run. All 33 repositories were reachable through the GitHub connector, including the two PSD repositories. The blocker is evidence quality and coverage, not repository access.

- Registry: 33 active rows; modes are 2 `full`, 29 `dry_run`, and 2 `disabled` (both PSD).
- Source shape: 31 code-and-docs repositories and 2 README-only PSD repositories.
- Imported knowledge: 31/33 present, 9/31 at the observed live tip, 22/31 stale, 2 absent. The imported index marks every one of its 31 products `stale=false`, so that index flag is not live-tip truth.
- Bundle integrity: 18/31 imported bundles contain `bundle_manifest.json`; d71 adds the aggregate `data/imported/knowledge_manifest.json` covering all imported files, but a per-bundle manifest remains absent for 13 bundles.
- Circularity: 3d/python is confirmed post-refresh/circular for sealed replay. Seven more exact-tip bundles were generated from tips whose latest commit is the shipped README refresh and therefore remain circular-risk until replayed from a pre-refresh source revision. Exact SHA freshness is necessary, not independent quality evidence.
- Dependency evidence: parsers exist only for Python and Rust. They are actually applicable to 12/33 roots (11 `pyproject.toml`, 1 `Cargo.toml`). The setup.py-only 3d/python repository, both README-only PSD repositories, and all Java/.NET/C++/Go/TypeScript entries lack a production dependency snapshot.
- Aspose reference evidence: 31 canonical candidate files exist; the active audit calibration is 30 because `cells/typescript` is an extra candidate excluded by the archived portfolio audit. PSD has no Aspose candidate in the bundle.
- Optimizer evidence: 10 historical finalized Python candidates exist. They predate the current knowledge-application contract, and their own index says 10/32, a stale denominator. None is current 33-row acceptance proof.

The first portfolio-wide sequence is therefore: seal/rebuild truth, then complete manifest/dependency inputs, then run current-contract candidate and review proof. Generating more prose before these gates would repeat the same false-confidence pattern.

## Identity separation

Each matrix row keeps seven identities separate: registry row, current GitHub source tip/tree, known pre-refresh fixture, imported knowledge revision/content, current published README, Aspose candidate, and optimizer evidence. A matching hash between any two is recorded; it is never treated as proof that the identities are interchangeable.

## Per-product compact matrix

| Product | Registry mode | Source shape | Live tip | Knowledge | Bundle manifest | Dependency snapshot | Aspose candidate | Optimizer candidate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3d/java | full | code_and_docs | e308de588886 | current | yes | ecosystem_parser_not_implemented | yes | none |
| 3d/net | dry_run | code_and_docs | 042a1e5f731d | stale | yes | ecosystem_parser_not_implemented | yes | none |
| 3d/python | dry_run | code_and_docs | ee05c1ba9153 | current | yes | parser_exists_but_supported_root_manifest_absent | yes | historical |
| 3d/typescript | dry_run | code_and_docs | 7b959706f2ad | current | yes | ecosystem_parser_not_implemented | yes | none |
| barcode/python | dry_run | code_and_docs | 06eca5c01e13 | stale | no | implemented_and_manifest_present | yes | historical |
| cells/cpp | dry_run | code_and_docs | 9f852d0ff1cf | current | yes | ecosystem_parser_not_implemented | yes | none |
| cells/go | dry_run | code_and_docs | 9f0a4033b59e | current | yes | ecosystem_parser_not_implemented | yes | none |
| cells/java | full | code_and_docs | 779c9640ee38 | current | yes | ecosystem_parser_not_implemented | yes | none |
| cells/net | dry_run | code_and_docs | 6ee32c08a609 | current | yes | ecosystem_parser_not_implemented | yes | none |
| cells/python | dry_run | code_and_docs | 26c3bd1633e8 | current | yes | implemented_and_manifest_present | yes | historical |
| cells/rust | dry_run | code_and_docs | 1a6004af47b1 | stale | no | implemented_and_manifest_present | yes | none |
| cells/typescript | dry_run | code_and_docs | fc186507e5b7 | stale | no | ecosystem_parser_not_implemented | yes | none |
| email/cpp | dry_run | code_and_docs | fef9c934c3ad | stale | no | ecosystem_parser_not_implemented | yes | none |
| email/net | dry_run | code_and_docs | 59125b4732df | stale | no | ecosystem_parser_not_implemented | yes | none |
| email/python | dry_run | code_and_docs | 10a906b48c0c | stale | no | implemented_and_manifest_present | yes | historical |
| font/python | dry_run | code_and_docs | 797188096414 | stale | yes | implemented_and_manifest_present | yes | historical |
| html/python | dry_run | code_and_docs | 912f0ae078b5 | stale | no | implemented_and_manifest_present | yes | none |
| note/python | dry_run | code_and_docs | 41de2e8ab478 | stale | no | implemented_and_manifest_present | yes | historical |
| page/python | dry_run | code_and_docs | ca4fb3d76f9a | stale | yes | implemented_and_manifest_present | yes | historical |
| pdf/cpp | dry_run | code_and_docs | 888700a8e361 | stale | no | ecosystem_parser_not_implemented | yes | none |
| pdf/go | dry_run | code_and_docs | 2306eeb06216 | stale | yes | ecosystem_parser_not_implemented | yes | none |
| pdf/java | dry_run | code_and_docs | ea62b3819934 | stale | yes | ecosystem_parser_not_implemented | yes | none |
| pdf/net | dry_run | code_and_docs | 663783d18ec1 | stale | no | ecosystem_parser_not_implemented | yes | none |
| pdf/python | dry_run | code_and_docs | 3dfe9f86cc81 | stale | yes | implemented_and_manifest_present | yes | historical |
| psd/net | disabled | README_ONLY | 1fe2c6dc8014 | absent | no | ecosystem_parser_not_implemented | no | none |
| psd/python | disabled | README_ONLY | 2f6c746a8a3e | absent | no | parser_exists_but_supported_root_manifest_absent | no | none |
| slides/cpp | dry_run | code_and_docs | ecc2baf8cc3e | stale | no | ecosystem_parser_not_implemented | yes | none |
| slides/java | dry_run | code_and_docs | 5d76f44cdd52 | stale | yes | ecosystem_parser_not_implemented | yes | none |
| slides/net | dry_run | code_and_docs | 6c650e96d079 | stale | no | ecosystem_parser_not_implemented | yes | none |
| slides/python | dry_run | code_and_docs | 90e523b90b91 | stale | yes | implemented_and_manifest_present | yes | historical |
| tex/python | dry_run | code_and_docs | 2f4bfab3863e | current | no | implemented_and_manifest_present | yes | none |
| words/net | dry_run | code_and_docs | 68d56fdaf7fc | stale | yes | ecosystem_parser_not_implemented | yes | none |
| words/python | dry_run | code_and_docs | 2d2efee2787c | stale | yes | implemented_and_manifest_present | yes | historical |

## Direct production-consumed knowledge

At d71, the optimizer directly consumes `merged/claims.json` for bounded selection, `merged/model.yaml` for provenance and repo-SHA freshness, `merged/api_surface.json` for structured public-surface facts, and `keywords/{family}.json` for SEO relevance. The aggregate `data/imported/knowledge_manifest.json` is part of the acceptance-contract hash. Files such as `formats.md`, `limitations.md`, `install.md`, `class_graph.json`, and `coverage_matrix.json` are present in most bundles but are not direct product-specific renderer inputs in the optimizer's integrated path; their mere presence must not be counted as applied knowledge.

## Decisive gaps

1. **Knowledge freshness is a portfolio gate, not a warning.** Twenty-two bundles do not match the live source tip. Stale/unknown claims may be selected only after current repository corroboration, but current corroboration is still too shallow to replace a rebuilt semantic bundle. Rebuild or semantically revalidate per product.
2. **Exact-tip knowledge can still be circular.** For README-refresh tips, using the refreshed README as knowledge evidence makes the output grade itself. Sealed replay must pin a true pre-refresh commit and exclude refreshed README prose from authoritative evidence.
3. **Dependency truth is incomplete by ecosystem.** Only Python/Rust parsers exist, and only 12 rows supply their supported root manifest. The remaining 21 rows cannot drive dependency-sensitive checks honestly.
4. **PSD is a distinct source shape, not an inferred product implementation.** Both repos contain only README.md, are registry-disabled, have no imported product bundle, and have no Aspose candidate in this evidence package. The first gate is a generic, source-honest README_ONLY profile based on actual PSD evidence—not fabricated language or assumed behavior.
5. **Historical optimizer candidates are not reusable approvals.** The 10 committed Python bundles prove that machinery ran on older revisions, not that current knowledge affects current candidate bytes or that present reviewer/check coverage is sufficient.

## Pin and later-state rule

The authoritative optimizer pin at audit start is GitHub main `d71f38b6a050b5282f0ada314f9ee4de35950426`. The available local checkout `56a5f09c80f57581d977d77142ed8809ed1ede9d` is older and is an ancestor of d71; it was used only to inspect unchanged imported knowledge bytes and committed historical evidence. No coordination-only or later source change is allowed to retroactively change source-tree observations without a new audit pin.

After the pin, GitHub main advanced to `05ef1e532ae34bea07fefe951543a43f41ca55c4` (`fix(presentation): make SEO knowledge shape capability titles safely`). That commit gives the relevant-SEO-keywords field one real, grounded title-shaping consumer and leaves the other five imported claim fields unconsumed. It does not change registry membership, target-repository tips/tree shapes, knowledge `repo_sha` freshness, bundle presence, or dependency-parser coverage, so the portfolio input findings remain valid; renderer behavior must be re-pinned before a candidate-quality run.

Full per-row details, exact URLs, SHA values, manifests, byte counts, artifact families, and first gates are in `PORTFOLIO_MATRIX.json`.
