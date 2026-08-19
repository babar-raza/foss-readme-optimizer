# PSD evidence: owner reconciliation

Date: 2026-08-20 (Asia/Karachi)

## Evidence identity and integrity

- Supplied archive: `readme-refresh-psd-evidence-20260819T180405Z.zip`
- Archive SHA-256: `59d2d9bf7e7e6d2fcd47107efb4f5281ceb2071bdad6207c637f7aafccaaa2ca`
- ZIP integrity: passed (`unzip -t`)
- Embedded `MANIFEST.sha256`: all listed files passed.
- Aspose.org working tree was dirty and changed from `6297b36f99f88e98c034f6e53c4e33cd79e98c78` to `fc28d32b9c5a4effc3d32bd85170299149d543c8` while the evidence was collected. Treat the archive as a bounded forensic snapshot, not a clean, single-commit reproduction bundle.

## What the bundle proves

The Aspose.org README-refresh system did **not** process Aspose.PSD and does not contain a whole-README, no-source fallback:

- `psd` is absent from Aspose.org's FOSS `data/products.json` and package registry.
- There is no PSD clone cache, merged knowledge, candidate, published state, or README-refresh run.
- The state-machine entry point rejects an unregistered family/platform before a run is created.
- The dependency extractor/check contract blocks absent or unreliable extraction rather than authoring dependency prose from memory.
- The only automated FOSS-adjacent trace is an unpromoted Python discovery candidate (`confidence: 0.6`, `action: investigate`, `registry_applied: false`).

Therefore, Aspose.org is **not** an execution oracle for PSD. Its strong candidates for launched products remain useful calibration, but the optimizer must implement README-only behavior explicitly and prove it itself.

## What exists outside that pipeline

Aspose.org contains separate marketing/SEO/reference material for the commercial Aspose.PSD family:

- family display and ordering;
- planned descriptions for Python, .NET, Java, and C++;
- localized commercial capability descriptions;
- commercial product/docs/reference/KB backlink targets;
- a products.aspose.org family-root page whose overview says the FOSS library is “coming soon.”

This material can support brand identity, approved link selection, and editorial vocabulary. It cannot prove that either FOSS repository implements a package, API, format, feature, dependency, example, or license.

## Corrections and limitations in the supplied narrative

1. The 32-character value `e3b0c44298fc1c149afbf4c8996fb924` is the first 32 hexadecimal characters of SHA-256(empty), not MD5(empty). The file alone does not prove why the value was truncated, so it must not be used as implementation evidence.
2. The disposable portfolio audit did not complete. `exit_code.txt` says `EXIT=127`, while `run_log.txt` says exit code 2; stdout and stderr are empty; the synthesis says a later heavy run was stopped. No portfolio-cleanliness claim may be derived from it.
3. Several reports read uncommitted Aspose.org working-tree state. Absence findings are well corroborated by independent registries and paths, but line-number/code claims should remain pinned to this bundle rather than described as present-day Aspose.org main.
4. Marketing text contains current-tense capability and MIT-license claims alongside a future-tense “coming soon” overview. That contradiction makes the whole page unsafe as FOSS technical truth.

## Current optimizer and live-repository reconciliation

Optimizer GitHub `main` was rechecked at `91d9479b1e1fa12a9af41c1692b6f8f421db5f76` while `OPT-FAST-PATH-R8-R12` was still running.

The optimizer already registers both PSD repositories as active but `mode: disabled`, with read-only analysis permitted:

- `aspose-psd-foss/Aspose.PSD-FOSS-for-Python`
- `aspose-psd-foss/Aspose.PSD-FOSS-for-.NET`

Both policy profiles contain an explicit unresolved license placeholder and commercial relationship talking points. Those values are policy/configuration, not repository facts, and must not become technical claims.

The live repository trees were independently checked through GitHub:

- Python tip `2f6c746a8a3ebfaf686a7053e34abfad3a2fd8b3`: exactly one root file, `README.md`; source text says only “FOSS version of Aspose.PSD for Python.”
- .NET tip `1fe2c6dc8014f26de3b79acbee25b15a8d26e903`: exactly one root file, `README.md`; source text says only “FOSS version of Aspose.PSD for .NET.”

The optimizer cannot currently accept these repositories honestly:

- `README_TRUTH_FIELDS` universally requires audience, problems, capabilities, formats, acquisition, example, license, and commercial/FOSS relationship.
- the presentation template universally requires At a Glance, Key Capabilities, Installation, Quick Start, Scope and Limitations, and License;
- the PSD policies deliberately lack `product_truth`, and the source trees cannot verify the universal fields;
- dependency snapshots can state `applicable=False`, but that alone does not create a truthful whole-document contract.

This is a modeling gap, not a missing PSD knowledge-import problem.

## Governing truth for README-only repositories

At the inspected revisions, the source can prove only:

- repository identity and platform;
- public repository existence and immutable revision/tree;
- that the owner describes it as the FOSS version of Aspose.PSD for that platform;
- that no implementation, package manifest, LICENSE, examples, or other tracked files are present.

Absence of code is positive evidence about repository state, but it is **not** evidence that the future product has no dependencies or that advertised commercial capabilities are implemented.

The correct candidate is a concise repository-status README. It should say that implementation/package/API/license information is not present at the inspected revision, preserve the two original source lines semantically, provide useful repository/contact/watch guidance, and label any commercial Aspose.PSD link as external product context. It must omit installation, dependency lists, API reference, examples, capability diagrams, feature/format claims, and license claims.

