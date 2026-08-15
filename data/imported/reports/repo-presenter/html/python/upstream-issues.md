# Upstream issues — Aspose.HTML FOSS for Python

Verified: 2026-08-02 against https://github.com/aspose-html-foss/Aspose.HTML-FOSS-for-Python

## No `pip install` variant succeeds — broken build-backend name
- **Severity**: BLOCKING
- **Evidence**: `pyproject.toml`'s `[build-system]` table declares
  `build-backend = "setuptools.backends.legacy:build"` — this module doesn't exist in any version
  of setuptools (the real legacy backend name is `setuptools.build_meta:__legacy__`; confirmed
  directly against the real `pyproject.toml` in the clone cache, 2026-08-04, not assumed from an
  earlier note).
- **Independently re-verified 2026-08-04, three ways, each in a fresh disposable venv** (re-checked
  on request rather than trusted from the earlier 2026-08-02 finding):
  1. `pip install -e <clone-path>` → `pip._vendor.pyproject_hooks._impl.BackendUnavailable` →
     `ModuleNotFoundError: No module named 'setuptools.backends'`.
  2. `pip install <clone-path>` (non-editable, same clone) → identical `ModuleNotFoundError`.
  3. `pip install git+https://github.com/aspose-html-foss/Aspose.HTML-FOSS-for-Python.git` (a
     genuinely separate clone via pip's own git-fetch, not the local clone cache) → identical
     `ModuleNotFoundError`.
  All three fail the same way because pip reads and invokes the same `[build-system]` table
  regardless of install source (local path, local non-editable, or a fresh git fetch) — installing
  "from the repo" via any `pip install` invocation does not avoid this defect; it is not specific
  to editable installs or to using the local clone cache.
- **Real, tested workaround** (this is what the README's Installation and Development-and-testing
  sections now document, in place of any `pip install` of the package itself): `pip install
  "skia-python>=87.0,<145"` (the package's one real runtime dependency, from `pyproject.toml`'s
  `[project].dependencies`) plus adding `src/` directly to `PYTHONPATH`, bypassing pip's build step
  entirely — this is the same mechanism the repo's own `pyproject.toml` already uses for pytest
  (`[tool.pytest.ini_options]` sets `pythonpath = ["src"]`, so the test suite already runs without
  the package being pip-installed). Verified end-to-end in a fresh venv: `import aspose_html`
  succeeds, and this README's own Quick start example (`HTMLDocument.parse` → DOM edit →
  `serialise`) runs and produces correct output through this exact workaround, not just an import
  smoke-check.
- **Impact**: every real user following any `pip install` command — regardless of source — cannot
  install the package via pip at all, until upstream fixes the build-backend string.
- **Not fixable here because**: the broken build-backend name is in the upstream repo's own
  `pyproject.toml`; a README cannot change another file's contents. The `PYTHONPATH` workaround
  above is a real, durable install method (not a verification-only shortcut) and is now documented
  as this product's actual install path until the upstream fix lands.

## Broken test-infra reference (not exercised by any README example)
- **Severity**: INFORMATIONAL
- **Evidence**: `tests/test_css/test_w3c_fixture_loader.py` imports `tests.test_css.w3c`, a directory that doesn't exist anywhere in the repo (no `.gitmodules` either).
- **Impact**: none for documented README examples; a pre-existing gap in the upstream test suite.
- **Not fixable here because**: it's the upstream repo's own test infrastructure.

## [js] extra fails to build on Windows
- **Severity**: INFORMATIONAL
- **Evidence**: the `[js]` extra's `quickjs` dependency fails to build on Windows because its own `setup.py` bakes in a GCC-only compiler flag that MSVC rejects.
- **Impact**: none for documented README examples (no block uses `JSContext`); only affects a user who separately installs `.[js]` on Windows.
- **Not fixable here because**: it's a third-party dependency's own Windows-compile gap, not this repo or README.
