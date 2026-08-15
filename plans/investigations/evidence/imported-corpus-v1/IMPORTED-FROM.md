# Import provenance (T1B)

**Source**: `https://github.com/aspose/aspose.org`
**Source commit**: `7f72da4e1423546104b40fa8cebf5b9ae3ce9c91` (approximate anchor — source
worktree was dirty at import time; the per-file sha256 manifest is the exact reproducibility
record, not this commit alone)
**Import date**: 2026-08-15
**Authorization**: explicit, session-recorded grant — see
`plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md`
**File count**: 3,272 files, 113,867,779 bytes
**Manifest**: `import-snapshot-manifest.json` (source-side per-file sha256, reconstruction-verified
0 mismatches) and `import-provenance-manifest.json` (destination-side mapping, per-file
source↔dest sha256, byte-identity flag)

## Destination layout

- `src/readme_agent/vendored_asposeorg/scripts/pipeline/**` — the 4 vendored code modules
  (`readme_refresh_run.py`, `readme_refresh_checks.py`, `dependency_extract.py`,
  `backlink_targets.py`), each carrying a per-file `Adapted from aspose.org: <path> @ <sha>`
  header.
- `data/imported/data/*.json`, `data/imported/keywords/**`, `data/imported/knowledge/**`
  (excluding `_vectors/`, `scout/`), `data/imported/reports/repo-presenter/**` — provenance for
  these non-Python files lives at the manifest level (`import-provenance-manifest.json`), not as
  inline headers, since headers would corrupt JSON/Markdown syntax or alter accepted candidate
  bytes for the calibration corpus.

## Corrections applied during import

Three `.py` files contained a hardcoded local development-machine path
(`C:\Users\prora\.claude\plans\d-users-prora-onedrive-documents-github-humble-tome.md`, an
artifact of that repository's own prior development session, unrelated to this project) —
redacted during copy; see `import-provenance-manifest.json` for exactly which files.

## Scope note

This is first-party code from the same corporate entity operating this repository's git
identity, imported under an explicit session-recorded authorization (not inferred from
corporate relatedness — see the licensing-resolution-state.md record for what that means and
why it matters). No relicensing claim is made; the imported material carries exactly the terms
that authorization establishes.
