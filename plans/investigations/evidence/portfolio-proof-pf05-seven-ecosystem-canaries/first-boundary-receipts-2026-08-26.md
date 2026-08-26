# PF05 first-boundary receipts (real, 2026-08-26)

Collected under the current fact-acceptance contract on real bounded canaries.
These supersede `runs/pf05-seven-canaries/first-boundaries.json`, whose
`elapsed_seconds` figures are hand-written literals (`EVID-006`) rather than
measured telemetry.

| Ecosystem | Repository | Outcome | First boundary |
| --- | --- | --- | --- |
| python | `aspose-3d-foss/Aspose.3D-FOSS-for-Python` | `NO_OP_PROVEN` | none |
| net | `aspose-3d-foss/Aspose.3D-FOSS-for-.NET` | `NO_OP_PROVEN` | none |
| cpp | `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp` | `BLOCKED` | duplicate capability inventory (`RDM-027`) + `CORE-038` DateTime false positive |
| java | `aspose-cells-foss/Aspose.Cells-FOSS-for-Java` | `BLOCKED` | 1 blocking claim, `claim:10247:2463e5708e818a52` |
| typescript | `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript` | not yet collected | |
| rust | `aspose-cells-foss/Aspose.Cells-FOSS-for-Rust` | not yet collected | |
| go | `aspose-pdf-foss/Aspose-PDF-FOSS-for-Go` | not yet collected | |

## Causal reduction so far: no single shared cause

Four receipts, four different results. The blocked pair do **not** share a cause:

- **cpp** — the source README's `## Key Capabilities` bullet titles collide with
  the authored cluster, so both render in one section. Depends on source README
  shape; `.NET`'s source has no such collision and passed first time.
- **java** — `claim:10247:2463e5708e818a52` classifies as
  `mandatory_fact_resolution` with **`obligation_id: None`**: an
  otherwise-unclassified product claim, which "requires claim-specific evidence
  or an authoritative owner; generic product-overview substitution is
  prohibited." The claim is a repository-layout statement:

  > The public API lives under `src/main/java/org/aspose/cells_foss/`, with
  > integration tests, unit tests, and generated Javadoc alongside it at the
  > repository root:

  That is neither a `development_commands` claim nor a capability duplicate.

The working hypothesis that Java would reproduce the C++ `development_commands`
gap in a Maven/Gradle form is therefore **refuted** by evidence, not merely
unconfirmed. The C++ repair (`curated_cmake_development.py`) removed a genuine
cross-ecosystem gap, but it is not the cause blocking Java.

## Consequence for sequencing

Nothing here yet justifies another shared-machinery repair. Two of four
ecosystems already reach `NO_OP_PROVEN` with no repair at all, which indicates
the pipeline is sound and the remaining failures are repository-specific or
narrowly-scoped. Collect the typescript, rust, and go receipts before grouping
causes, per the taskcard's `FIRST_BOUNDARY_ALL_7 -> REDUCE_REAL_RECEIPTS ->
REPAIR_SHARED_ONCE` order.
