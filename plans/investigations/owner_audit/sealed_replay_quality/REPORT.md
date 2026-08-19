# Sealed replay and quality-transformation audit

## Executive finding

The current optimizer has not yet demonstrated the same operation that produced the Aspose
READMEs. Its strongest recent evidence is preservation/no-op evidence over READMEs that Aspose had
already refreshed. The clean historical optimizer evidence from 2026-07-25 shows a different
failure mode: it reproduced each old README almost byte-for-byte, added a presentation marker,
table of contents, and six `None` placeholders, and still failed its own independent review. On
Note/Python it additionally fabricated a Java/Maven/JDK installation path.

Aspose's quality came from reconciling old content against the complete source/package truth,
discovering facts not present in the old README, curating a new information architecture, running
product-specific semantic checks, and keeping an auditable disposition for every old content
unit. Reusing the imported knowledge helps, but does not replace those behaviors.

## Evidence identities (do not collapse these)

| Identity | 3D/Python | Note/Python | Barcode/Python |
|---|---|---|---|
| Sealed pre-refresh tree | `ab1a2267a0ba6302311d0c7c4ad01494974c7d76` | `6d97a522a9ed24708687911f1aabb76e2dea2da7` | `53f2c3350b8171f2c8275e7b1a178f218695ac45` |
| Pre-refresh README blob | `c952868888c0bd91688ad4fa2ddad8ddf8a04563` | `629a9706aabf7f20919abebda16b4a975e687490` | `069205725fdbd5b0fa8ae45087cb44d2908381d8` |
| Published refreshed tip | `ee05c1ba9153ef5916b7a108406c794f2e464d01` | `41de2e8ab478b5aeff3663f7f7cbf83b19fdf676` | `06eca5c01e13ed6d59a640f1cf330c1c5a57d151` |
| Published README blob | `4e4a264298dcf5099919d314834672653d1fed4f` | `ad1e4a5fb65f0394aa78ad9c703a346e032822fb` | `03445fbc7b846b51c500a4a5e3d956c14a57b149` |
| Imported knowledge `repo_sha` | post-refresh `ee05c1ba…` | sealed `6d97a522…` | sealed `53f2c335…` |
| Historical optimizer evidence | commit `89acfd172fd7caf5f89224c9a55262cedccd7847`, all three `verified=false` | same | same |

The exact commit pages are:

- 3D sealed input: <https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/commit/ab1a2267a0ba6302311d0c7c4ad01494974c7d76>; refresh merge: <https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/commit/62fb89f3ca76dc0afa9b2dfb983b9a1fa3f74fba>; presentation fix: <https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/commit/ee05c1ba9153ef5916b7a108406c794f2e464d01>.
- Note sealed input: <https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python/commit/6d97a522a9ed24708687911f1aabb76e2dea2da7>; refresh: <https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python/commit/41de2e8ab478b5aeff3663f7f7cbf83b19fdf676>.
- Barcode sealed input: <https://github.com/aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python/commit/53f2c3350b8171f2c8275e7b1a178f218695ac45>; refresh: <https://github.com/aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python/commit/06eca5c01e13ed6d59a640f1cf330c1c5a57d151>.
- Historical optimizer evidence commit: <https://github.com/babar-raza/foss-readme-optimizer/commit/89acfd172fd7caf5f89224c9a55262cedccd7847>.

## What Aspose actually transformed

### 3D/Python

The old README was 189 lines with two examples and no limitations section. The published Aspose
README is 435 lines with eleven examples, a capability diagram, exact API/import guidance, and
source-derived limitations. The later canonical candidate expands this to a 307-row table-rich API
surface. The important delta is semantic, not length:

- It corrected the package-acquisition statement: the old README advertised
  `pip install aspose-3d-foss`; the refreshed README says it is not published and gives a source
  checkout path.
- It distinguished working OBJ/STL/glTF/3MF flows from COLLADA import-only and experimental FBX.
- It found defects impossible to infer from the old prose: top-level option-class shadowing,
  missing `collada/__init__.py`, an unset glTF save-option format, FBX exporter methods that
  immediately raise, and a dispatcher ordering bug that blocks the real COLLADA exporter.
- It restored the real animation subsystem, built a module-grouped API reference, and verified
  examples against actual behavior.

Aspose reconciled 71 old content units: 11 were merged/reframed and 60 excluded; 48 had direct
source verification. Exclusion was deliberate—marketing, redundancy, or contradicted claims—not
silent loss.

The historical optimizer candidate added 24 lines but no real examples, diagram, API detail, or
limitation reasoning. Its `At a glance` said `Runtime: Java unknown+` and all semantic fields were
`None`. Independent review recorded seven missing semantic facts, an unaccepted cited fact, and an
invalid candidate.

### Note/Python

The old README was already rich (478 lines and 22 code blocks), making this the clearest proof that
Aspose is not a generic rewrite. It preserved the useful material, relocated and curated examples,
and reconciled 148 content units: 120 merged/reframed, 28 excluded, 122 verified against source.
It added the presentation system, dependency buckets, grouped API tables, and precise limitations.

Source inspection added information the old README did not contain: `Document.FileFormat` always
returns `OneNote2010`; licensing methods are silent no-ops; `DetectLayoutChanges()` is a stub; the
base `AsposeNoteError` is not top-level-exported; and old GitHub links targeted the wrong org. The
pushed Aspose run `rr-20260815T191258Z-2545f6e86187` pinned the sealed SHA, ran 93 named checks (59
hard; zero hard findings), recorded 20 example blocks, required approval, and emitted a push
receipt. The stored verification runner nevertheless marks every example `BLOCKED-WITH-REASON:
TOOLCHAIN-UNAVAILABLE`; therefore those records prove governed disclosure, not runtime execution.

The historical optimizer preserved the old README but inserted this invalid instruction before
the correct Python installation section:

```text
git checkout 6d97a522...
mvn clean install
This path requires JDK unknown+ and Maven.
```

Its own review is `verified=false` and explicitly reports the blocked acquisition, seven missing
semantic fields, unaccepted facts, and invalid validation. This is direct evidence that mechanical
reproducibility and hash integrity did not produce README quality.

### Barcode/Python

The old README was technically useful (215 lines, 13 examples, 19 table rows) but had only two
links, no visual hierarchy, no API-reference section, no dependency classification, and only a
brief PDF caveat. Aspose retained the correct mechanisms while adding brand/navigation/diagram,
curating examples, building an API surface, separating Pillow runtime from test tools, and
documenting the encode-only, PDF, ECI, and GS1 boundaries. Its canonical disposition reconciles
51 units: 40 merged verbatim, 11 excluded, 29 directly source-verified.

The optimizer candidate is 238 lines, but the only meaningful change is a marker, TOC, and the
same broken six-field placeholder (`Runtime: Java unknown+`). It neither extracted the missing
limitations nor composed a new API/dependency presentation. Independent review again says
`verified=false` with seven missing semantic fields.

The bundle's later canonical Barcode candidate is not byte-identical to the published GitHub
README. The published blob was fetched and pinned, but the bundle lacks a local exact copy. This
audit therefore uses the later bundle candidate for numeric presentation metrics and cites the
published blob separately; it does not pretend they are the same artifact.

## Imported knowledge: useful, but not clean by default

The imported corpus is substantial: 3D has 3,452 claims, Note 333, Barcode 375. However, SHA
alignment is not sufficient evidence quality.

The 3D bundle is contaminated for sealed replay. It declares the already-refreshed tip
`ee05c1ba…` and was generated at `2026-08-14T11:52:56Z`, after that tip's `09:56:03Z` commit.
Seventy claims cite `README.md`; their snippets are visibly carried from the old README even while
the model declares the new SHA. Examples:

- `ERC-3d-python-cb601cba` changes real `Vector2`/`Vector3`/`Vector4`/`Matrix4` names into
  nonexistent `FVector2`/`FVector3`/`FVector4`/`FMatrix4` using only an old README sentence.
- `ERC-3d-python-f14fb8f0` infers an STL material limitation from the generic phrase “for 3D
  printing,” which does not establish that fact.
- `ERC-3d-python-338c230c` and `ERC-3d-python-8e9815fe` present FBX exporter/API/options as working,
  while scout limitations `CLM-3d-f966ea` and `CLM-3d-31f56e` prove both exporter entry points
  raise `NotImplementedError`.

This is more serious than ordinary staleness: the imported 3D bundle combines a post-refresh
identity, retained pre-refresh README evidence, positive signature-level claims, and negative
method-body truth while `has_conflicts: false`. It cannot be an uncontaminated generation input.

Note is SHA-aligned and has no README-evidence claims, but is scout-only. Barcode is SHA-aligned,
but ten claims rely on the old README; those may support preservation, never independent discovery
or publication of a new claim. Every selected claim still needs evidence-path, symbol/content, and
polarity validation inside the sealed tree.

## Smallest gates that distinguish quality generation from no-op preservation

These are the minimum systemic gates; passing syntax/style checks is not enough.

1. **Sealed-input/non-contamination gate.** Full target tree and pre-README are pinned at the
   pre-refresh SHA. The reference README is unavailable until the candidate and evidence ledger
   are sealed. Knowledge `repo_sha` must equal the sealed SHA.
2. **Claim-level evidence and polarity gate.** Each published claim maps to a concrete file,
   symbol/line/content fingerprint at the sealed SHA. File existence is insufficient. Positive
   claims fail when limitation/stub/raise evidence exists; mixed records cannot inherit a single
   `verified` flag from one good item.
3. **Old-content accountability gate.** Every substantive old content unit is preserved,
   corrected, relocated, merged, or excluded with a reason and evidence. No silent drops or
   unchanged contradictions.
4. **Material-improvement gate.** A generation run must add or correct at least one independently
   verified capability, acquisition/dependency fact, API detail, limitation, or runnable example.
   Marker/TOC/layout-only changes cannot qualify as an improved candidate.
5. **Example execution gate.** Primary examples must run against the sealed tree/package in a
   disposable environment. `BLOCKED-WITH-REASON` remains visible and prevents a full-quality claim;
   it is not equivalent to a pass.
6. **Aspose-calibrated structural/semantic gate.** Required sections, diagram truth, dependency
   classification, API symbol existence, limitation/capability contradiction, link ownership, and
   product-specific checks must pass. A prose judge cannot waive a deterministic failure.
7. **Cross-candidate blind review gate.** Only after sealing, compare against the Aspose reference
   on coverage/correctness/usefulness/presentation; demand no critical omission and no unsupported
   claim. Then rerun the candidate as input to prove idempotence separately.

With these gates, already-refreshed no-op runs are still valuable—but only as the idempotence half
of the proof. The missing half is sealed generation from `ab1a2267…`, `6d97a522…`, and
`53f2c335…` without access to their post-refresh READMEs.

## Current optimizer status observed during this audit

The owner reported GitHub `main` advanced to `d71f38b6`; `eaf5eef6` repaired the five baseline
failures (4,207 passed, one skipped, one xfailed), and later commits were governance/auto-push
changes. Those changes improve baseline health but do not alter this sealed-replay conclusion.

Machine-readable details and exact hashes are in `MATRIX.json` and `REPLAY_FIXTURES.json`.
