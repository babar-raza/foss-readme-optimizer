# Prepared change: complete Lane A — Development and Native-System-Requirements H3s

## Root cause (traced 2026-08-19, following the aspose.org two-gate finding)

Barcode-python's `pytest`/`ruff` claim (`source:claim:3930:c5ac180c4dd86b4f`) and font-python's
"no native system libraries: WOFF2's Brotli... vendored pure-Python codec" claim
(`f76ee53ac612c3f9`) both stayed genuinely blocking through the current pipeline. E5's
`excluded_with_reason` mechanism DID close the barcode claim at gate 1 (the LLM-assisted
presentation-plan check), but per `architectural-finding-two-gate-claim-accountability.md`,
gate 2 (`evaluate_candidate_factuality`) rebuilds the document plan without any LLM disposition
client — a claim accepted only through the LLM path will re-derive as unaccounted-for there,
every time. The only path to full closure is making the claim's assertion literally,
mechanically present in the rendered candidate — exactly what the already-merged Lane A fix did
for the "no required dependencies" empty case.

## What's missing (verified by reading the real extraction code)

`src/readme_agent/facts/curated_python_dependencies.py::python_distribution_evidence()` only
reads `pyproject.toml`'s `[project.dependencies]` — it never reads
`[project.optional-dependencies]` groups (`dev`, `test`, etc.) at all, and there is no
extraction anywhere for "native/system library requirements are vendored/pure-Python" facts.
This is a genuine, new fact-extraction gap, not merely a missing render.

## Scoped implementation (two independent sub-changes, either alone is real progress)

### A. Development Dependencies H3 (closes barcode's pytest/ruff-shaped claim class)

1. Extend `python_distribution_evidence()` to also capture
   `project["optional-dependencies"]` group names+specifiers whose group name matches a
   conventional dev/test marker (`dev`, `test`, `tests`, `lint`, `ci` — case-insensitive),
   storing them as a new `"development_dependencies"` list field on the `python.distribution`
   fact value (mirrors the existing `runtime_dependencies` shape exactly: list of exact
   `name>=version` strings, verified-empty vs absent distinguished the same way).
2. Extend `dependency_markdown()` (`verified_template_sections.py`) to render a
   "Development Dependencies" line/H3 when this new field is present and non-empty — same
   verified-empty-vs-unverified discipline as the existing Required H3.
3. Wire the new H3 into the template's four-H3 Dependencies contract
   (`templates/readme/section-registry-v2.json` / `repository-presentation-v1.json`) if not
   already structurally present — check the current template's section shape first; it may
   already support a nested H3 pattern the Lane A merge only partially used.

### B. Native and System Requirements H3 (closes font's vendored-codec-shaped claim class)

This one is HARDER to make general: "no native system libraries; vendored pure-Python codec"
is a narrative claim about the ABSENCE of a native dependency, evidenced by a specific vendored
module (`aspose_font._brotli` in font's case). A safe, general fact-extraction rule: detect
whether the package's `pyproject.toml`/`setup.py` declares NO native/C-extension build steps
(no `ext_modules`, no `cffi`/`cython` build-backend) AND whether `runtime_dependencies` (from
part A's existing extraction) is empty of known native-wrapping packages — if both hold, the
fact `python.distribution.native_system_requirements` can safely assert "no native system
libraries required" as a verified-empty fact, mirroring part A's own verified-empty pattern.
Do NOT attempt to name the SPECIFIC vendored module (e.g. "Brotli codec") generically — that
requires per-repo knowledge outside safe automatic extraction; render only the safely-general
"no native system libraries required" sentence when the general negative-evidence check holds,
and leave the specific technical detail (which vendored module implements what) to whatever
Key-Capabilities enrichment already covers the format-support surface.

## Acceptance (matching this session's established discipline)

- Test-first: verified-non-empty dev-deps renders; verified-empty dev-deps renders the
  standard sentence; unverified/absent dev-deps still omits the H3 entirely (fail-closed,
  matching the merged Required-H3 pattern exactly).
- Canary: barcode-python (part A) and font-python (part B).
- **Verify against BOTH gates** (the architectural finding from this session) — a canary that
  only shows gate-1 improvement is not sufficient; confirm the repository reaches
  `CONVERGED_PROPOSAL_READY`/`AGENT_APPROVED`, not merely a reduced blocking-claim count.
- No LLM involvement needed for either sub-change — pure deterministic fact extraction +
  rendering, matching aspose.org's own architecture (disposition IS the render).
