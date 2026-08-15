# T1A — import enumeration + snapshot manifest + reconstruction proof

**Status: COMPLETE**, 2026-08-15T19:20:00Z.

Source: `D:\onedrive\Documents\GitHub\aspose.org`, HEAD `7f72da4e1423546104b40fa8cebf5b9ae3ce9c91`
(APPROXIMATE anchor — worktree dirty; reproducibility comes from this manifest's per-file
sha256, not the commit alone). Enumerated: `scripts/pipeline/commands/foss/`,
`scripts/pipeline/lib/backlink_targets.py`, `data/*.json`, `keywords/`, `knowledge/` (excluding
`_vectors/`, `scout/`), `reports/repo-presenter/` — excluding `__pycache__/` and
`data/backlinks/workspace/`.

**Measured**: 3,272 files, 113,867,779 bytes (108.6 MiB) — within 1.5% of TD-01's earlier
108.5 MB/3,277-file estimate (the earlier figure was a directory-total approximation; this is
the exact enumerated count with a slightly different file-count due to the precise
`data/*.json`-only glob vs. all-files).

**Reconstruction verification**: every one of the 3,272 files copied from the manifest into a
fresh temp directory and re-hashed; **0 mismatches** — the manifest is a faithful, reproducible
snapshot. See `import-snapshot-manifest.json` for the complete file list with per-file sha256.

**Authorization**: `licensing-resolution-state.md` (granted 2026-08-15T19:13:44Z).

T1B may now proceed.
