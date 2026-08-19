# README optimizer owner-side forensic audit

Started: 2026-08-19

This workspace is an independent, read-only investigation of the current README optimizer and its
Aspose.org calibration evidence. It exists so the ChatGPT coordinator can establish the next
repair sequence without waiting for the VS Code implementation and PSD evidence lanes.

## Pinned starting state

- Optimizer GitHub repository: `babar-raza/foss-readme-optimizer`
- Latest GitHub `main` commit observed at audit start:
  `6d112bbf88bc54f7ef3367b16ef8e9b769bdfb51`
- Aspose evidence source snapshot:
  `6297b36f99f88e98c034f6e53c4e33cd79e98c78`, with the supplied bundle's dirty-tree caveat
- Optimizer context archive:
  `../foss-readme-optimizer-context-bundle-2026-08-19`
- Aspose README-refresh archive:
  `../readme-refresh-complete-bundle-20260819-174412`

## Parallel lanes

1. `source_knowledge_truth/`
   - Pinned actual FOSS repositories versus imported registries and merged knowledge.
2. `knowledge_to_candidate/`
   - Imported knowledge through facts, Qwen inputs, plans, candidate bytes, and provenance.
3. `acceptance_runner/`
   - Reconciliation, deterministic checks, review/repair, caching, portfolio, and runner fitness.
4. `sealed_replay_quality/`
   - Sealed pre-refresh inputs versus historical optimizer output, Aspose output, and published
     output; identifies the smallest gates that distinguish generation quality from preservation.
5. `portfolio_input_matrix/`
   - Current source shape, knowledge freshness, manifest/dependency coverage, and first honest
     blocker for every one of the 33 registry entries.
6. `defect_gate_map/`
   - Known false claims and process failures traced through their exact fact, render, check,
     review, acceptance, and cache owners, with failing-before regression specifications.
7. `aspose_candidate_rubric/`
   - Cross-candidate metrics and a measurable 30-point calibration rubric derived from the
     supplied Aspose corpus without treating length or brand copying as quality.
8. `qwen_context_budget/`
   - Real author/reviewer payload sizes, truncation and fallback control flow, required coverage,
     and bounded per-stage call/token budgets for Qwen3 Next.

Each lane must provide a narrative report, structured evidence, reproduction notes, and checksums.
The coordinator will reconcile disagreements and package the accepted evidence only after all lanes
finish. These files are not optimizer repository changes and authorize no publication or target
write.

## Current repository tip

The latest GitHub `main` observed during consolidation is
`91d9479b1e1fa12a9af41c1692b6f8f421db5f76`. Commit `05ef1e5...` closes the
specific unsafe SEO-provenance defect and gives one imported editorial field a bounded visible
consumer; it reports 4,214 passed, 1 skipped, 1 xfailed, 0 failed. Commit `91d9479...` is a
read-only acquisition-boundary evidence commit and records the setup.py dependency silent-empty
gap. Neither closes the remaining knowledge, validation, review, replay, PSD, or runner gates.

## How to use this package

1. Read `RECONCILED_FINDINGS.md` for the owner-approved current truth.
2. Use `PRIORITIZED_IMPLEMENTATION_SEQUENCE.md` to select the next atomic implementation gate.
3. Open a lane's narrative report for the supporting evidence and its structured JSON for machine
   checks or regression-fixture construction.
4. Follow each lane's reproduction notes before relying on a calculated result.
5. Verify `SHA256SUMS` before moving or uploading the package.

Do not run `acceptance_runner/NEXT_ACTION_PROMPT.md` verbatim while another optimizer writer is
active. It was prepared at an older audit pin and is supporting material; the reconciled sequence
is the governing owner plan.
