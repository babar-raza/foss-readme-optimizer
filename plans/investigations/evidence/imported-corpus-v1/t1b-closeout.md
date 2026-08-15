# T1B — staged import execution

**Status: COMPLETE**, 2026-08-15T19:35:00Z.

3,273 files copied from the T1A manifest (3,272 original + `api_table_dupes.py`, a transitive
import dependency of `readme_refresh_checks.py` discovered during T3 scoping and added with
full provenance) into:

- `src/readme_agent/vendored_asposeorg/scripts/pipeline/**` — 5 code modules, each with a
  per-file `Adapted from aspose.org: <path> @ <sha>` header; 3 files had a hardcoded local
  development-machine path scrubbed.
- `data/imported/**` (`data/*.json`, `keywords/`, `knowledge/` minus `_vectors/`/`scout/`,
  `reports/repo-presenter/`) — manifest-level provenance only (`import-provenance-manifest.json`),
  no inline headers (would corrupt JSON/Markdown syntax or alter accepted candidate bytes).

**Verification performed**:
- Content-level secret scan (API keys, AWS keys, GitHub tokens, OpenAI-style keys, PEM blocks)
  across the entire imported set: **clean, zero matches**.
- `ruff check .` / `ruff format --check .`: clean (vendored + imported paths excluded from this
  project's own style enforcement via `pyproject.toml` — third-party code, not restyled; see the
  exclusion comments there).
- `mypy src`: clean (684 files; vendored path excluded).
- Full governed suite re-run after import: see `full-pytest-output.txt` in this bundle.
- `readme_refresh_checks.py` now imports cleanly once `api_table_dupes.py` (its one missing
  transitive dependency) was added; introspection finds **89** `check_*` functions (not the
  historical "81" figure — exactly the point-in-time measurement this plan's own resolution 7
  anticipated: "81 is a point-in-time audit measurement, never a binding constant").

`IMPORTED-FROM.md` records full provenance. `T3` (adapting/classifying/testing this check
battery) may now begin.
