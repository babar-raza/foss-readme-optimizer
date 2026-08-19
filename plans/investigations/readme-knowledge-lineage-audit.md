# README Knowledge Lineage Audit — continuous, boundary-by-boundary forensics

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)`
> artifact_role: analysis_or_evidence_only · execution_authority: false
> method: read-only investigation subagents (`Explore` tool) per boundary, verified by the
> coordinating session before commit; evidence pinned to explicit repository SHAs, never a moving
> branch after pinning.

## Why this exists

A parallel, non-blocking investigation lane requested alongside the `OPT-FAST-PATH-R8-R12`
recovery session: trace how real repository information and imported Aspose knowledge actually
travel through the optimizer, one transformation boundary at a time —

```
actual FOSS repository + registries + imported Aspose corpus
    -> pinned repository snapshot
    -> detected records
    -> accepted ProductFactsV2/fact graph
    -> Qwen author context and section plan
    -> rendered candidate bytes and provenance
    -> source reconciliation
    -> deterministic checks
    -> independent review/repair
    -> cache/no-op/promotion evidence
```

Each boundary must show what the input contained, what code read it, what the output contained,
what was filtered/transformed/rejected/lost and why, and whether validators could catch loss or
fabrication. This report accumulates one dated section per completed boundary; evidence artifacts
live in `plans/investigations/evidence/readme-knowledge-lineage-audit/`.

Method notes: investigation runs entirely read-only against `gh api`/local files; the coordinating
session independently verifies material findings before committing evidence (e.g. re-derived
`python_dependency_acquisition.py`'s reported guard directly via `grep` before trusting it). No
mission action, target write, or product-repository effect occurs in this lane.

## Reference repository and pin

Primary subject: `aspose-3d-foss/Aspose.3D-FOSS-for-Python`, pinned at
`ee05c1ba9153ef5916b7a108406c794f2e464d01` (branch `master`, committed 2026-08-14T09:56:03Z) —
recorded once, at the start of this audit, and reused for every boundary until the audit
deliberately moves to a contrast-set repository (planned: `aspose-note-foss/Aspose.Note-FOSS-for-Python`
for simple/golden behavior, `aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python` for
independent-reproof sensitivity — not yet started).

## 2026-08-19 — Boundary A: registry and acquisition truth

Evidence: [`repository-intake-lineage.json`](evidence/readme-knowledge-lineage-audit/repository-intake-lineage.json).

**Scope.** Actual FOSS repository + registries -> pinned `RepositorySnapshotV1`. Is the
`data/products.json` row for this product correct and consistent with the real repository? Does
acquisition capture everything downstream fact-extraction needs? Are README-only / monorepo /
generated-source / LFS / submodule / missing-manifest conditions represented truthfully rather than
silently inferred as "no capability"? Is every snapshot input content-addressed and reproducible?

**Findings.**

- `data/products.json`'s row (`family=3d, platform=python, ...`) matches the real repository exactly
  on every checkable field: GitHub `repository_id`/`node_id`, exact org/repo casing, MIT license,
  default branch `master`. A second, older copy of this row exists in
  `data/imported/data/products.json` (schema-v0, no `provider_identity`/`mode`) — confirmed **inert**
  by grep (`registry/loader.py`/`discovery.py` hardcode the live `data/products.json` path; nothing
  reads the imported copy) — a stale archival duplicate, not a live risk.
- Acquisition is a real full `git clone --depth 1` of the working tree
  (`gitsafety/clone.py::clone_baseline()`), not a selective API fetch, so every file in the real repo
  is reachable by any stage reading `snapshot.root_path` directly — not only the fields formally
  captured on `RepositorySnapshotV1` (which stores only `readme_path`/`readme_sha256`,
  `inventory_sha256`, and `package_roots`; LICENSE is detected but not itself a named, individually
  hashed snapshot field, only indirectly covered by the aggregate `inventory_sha256`).
- This repository is genuinely not README-only, not a monorepo, not generated-source, has no LFS
  pointers and no submodules — confirmed against the real GitHub tree at the pinned SHA, not
  inferred. Its manifest is legacy `setup.py` (no `pyproject.toml`); `dependency_snapshot.py`'s
  `_python_snapshot()` correctly reports `applicable=False, not_applicable_reason="no pyproject.toml
  at the repository root"` for it — a truthful gap, not a fabricated "zero dependencies" (this
  module's own docstring cites a real prior incident, MT041, for exactly this failure mode).
- **Confirmed, independently re-verified defect (repository-specific-benign today, systemic risk
  untested elsewhere):** `src/readme_agent/facts/python_dependency_acquisition.py:46-58` and `:61-73`
  (`declared_python_runtime_dependencies` / `declared_python_build_dependencies`) guard on
  `manifest.name != "pyproject.toml"` and return a bare `[]` — no error, no gap flag, no
  `not_applicable_reason` — for any setup.py/setup.cfg-only Python repository, indistinguishable
  from "this manifest genuinely declares zero dependencies." For this specific repository the result
  happens to be correct by coincidence (its real `setup.py` has `install_requires=[]`, confirmed via
  `gh api .../contents/setup.py`), so nothing is visibly wrong today — but this is a second,
  parallel "what are this repo's dependencies" consumer that disagrees in honesty with
  `dependency_snapshot.py`'s explicit `applicable=False` gate for the identical condition. Queued to
  the knowledge-gap backlog (below); not fixed in this boundary (out of scope — a fix belongs to
  whichever fast-path stage owns dependency-evidence truthfulness, not this read-only lane).
- Hashing is real but partial: `readme_sha256` individually hashes the README; the rest of the tree
  (LICENSE, manifest, source) is covered only by one aggregate `inventory_sha256`
  (`sha256(git ls-tree -r --full-tree HEAD)`), which does transitively content-address every tracked
  file but exposes no per-file breakdown. `captured_at` (a real timestamp) is the only field that
  keeps the *serialized snapshot object* from being byte-reproducible across two acquisitions at the
  same SHA — expected, not a defect.

**Verification.** The dependency-acquisition guard was independently re-derived by the coordinating
session via direct `grep` of `python_dependency_acquisition.py` before being trusted (see this
report's own audit trail; not merely accepted from the subagent's quote).

**Knowledge-gap backlog entries opened:** `KGAP-001` (below).

## Knowledge gap backlog

See [`knowledge-gap-backlog.json`](evidence/readme-knowledge-lineage-audit/knowledge-gap-backlog.json).
