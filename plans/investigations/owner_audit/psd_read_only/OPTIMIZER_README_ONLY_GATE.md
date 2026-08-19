# Next optimizer gate: source-honest README-only foundation

## Decision

After the currently running `OPT-FAST-PATH-R8-R12` lane stops and its commits are reviewed, implement one bounded gate named `OPT-P0-README-ONLY-FOUNDATION`. Do not run it concurrently with another optimizer writer.

This gate is deliberately earlier than PSD publication and independent of the imported-claim polarity repairs for code-bearing products. PSD has no imported technical corpus to select, so waiting for those repairs would not improve its source truth.

## Required behavior

Reuse the current snapshot, fact, acceptance, template, reconciliation, validation, and evidence machinery. Add a repository-shape projection and shape-aware contracts; do not build a second pipeline.

1. Derive a content-addressed repository shape from the already-pinned Git tree. For this gate, `README_ONLY_PLACEHOLDER` must be exact and fail closed: a tracked README exists and there are no other tracked implementation, manifest, license, example, documentation, or build files. Store the qualifying paths/tree hash and reason. Do not infer the shape only from a missing manifest.
2. Make repository shape part of the fact-acceptance contract hash and cache invalidation boundary. Adding any implementation/manifest/license file must stop using the README-only contract on the next run.
3. Produce accepted, repository-owned facts for identity, repository state, and the narrow source-stated FOSS relationship. Do not promote marketing descriptions, planned descriptions, policy TODOs, or commercial product capabilities to technical truth.
4. Add a sparse presentation contract/profile inside the existing presentation machinery. It must describe repository status and next-user actions, not force capability, installation, example, API, dependency, diagram, or license sections.
5. Express code-dependent checks as typed `not_applicable` with the repository-shape fact ID and reason. A skipped or errored applicable blocking check must still fail. “No manifest/code exists” must never become “zero dependencies.”
6. Reconcile every original README content unit. The title and “FOSS version” line must be preserved or deliberately reframed with exact causal lineage. No unexplained omission is allowed, and reconciliation errors must block acceptance.
7. Generate deterministic local candidates for both PSD repositories. Stop at local `CANDIDATE_GENERATED`/deterministic validation; do not enable registry write mode, commit to target repos, push, or open PRs.

## Candidate content contract

Required concepts, with wording allowed to vary only when evidence remains exact:

- Correct product/repository title and platform.
- Clear status: at the pinned revision the repository contains only its placeholder README; implementation/package artifacts are not present here yet.
- Honest unavailable-information statement: installation, API, supported formats/features, dependencies, examples, and license cannot be documented from this repository yet.
- Narrow relationship: the source README identifies this as the FOSS version of Aspose.PSD for the platform. Do not claim parity with or derivation from the commercial product.
- Useful next actions: watch the repository, use its issue tracker for repository questions, and optionally follow a clearly labeled commercial Aspose.PSD link for separate product information.

Forbidden:

- MIT or any license name while no LICENSE file exists;
- package coordinates/import roots/install commands;
- PSD/PSB/AI support, layer manipulation, conversion, rendering, or any other capability;
- dependency-free/no-dependency claims;
- API/class/method names or code examples;
- Mermaid capability diagram;
- “full-featured,” “Enterprise Edition,” upgrade-path claims, or assertions that the FOSS implementation is equivalent to commercial Aspose.PSD;
- process narration, evidence IDs, internal gate names, hashes, or audit language in visitor prose.

## Proof required in the atomic implementation commit

- Unit tests for exact shape classification and automatic reclassification after adding one code, manifest, or LICENSE file.
- Unit tests proving current universal truth/template contracts remain byte/behavior unchanged for code-bearing fixtures.
- Candidate tests for both exact PSD source READMEs.
- A negative vocabulary/section test covering every forbidden category above.
- Claim-map test: every material claim binds only to accepted repository/policy facts; commercial links are supporting context, not technical evidence.
- Dependency/check test: explicit shape-backed N/A, never silent skip and never empty-as-zero.
- Preservation/reconciliation test: both source units accounted for; any reconciliation error blocks advancement.
- Repeatability test: two runs with identical source/config/model fixtures produce identical candidate bytes, fact hash, plan hash, claim map, and reconciliation result.
- Mutation test: add a source/manifest/license file and prove prior README-only cache/evidence is rejected.
- Local dry-run evidence bundles for both exact live PSD revisions, with candidate hash, checks, claim map, dispositions, reconciliation, and contract/component hashes.
- Score each candidate 30/30 on a committed README-only rubric whose points reward correct abstention, usefulness, preservation, and evidence—not nonexistent features.
- Full official test suite: zero failures; ruff, format check, and mypy clean.

## Stop conditions

Stop without committing if the implementation weakens the normal code-bearing contract, treats missing evidence as an empty fact, emits any forbidden claim, permits reconciliation/check errors to pass, or cannot produce both candidates without live model improvisation. Report the exact boundary and smallest repair.

On success, make one atomic commit and stop. Publication authorization remains a separate later decision.

