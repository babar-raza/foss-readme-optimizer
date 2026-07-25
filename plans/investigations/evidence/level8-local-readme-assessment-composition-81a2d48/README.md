# Level-8 Local README Assessment and Composition Proof

This directory is the corrected evidence bundle for
`L8-LOCAL-README-ASSESSMENT-COMPOSITION`. It supersedes
`level8-local-readme-assessment-composition-b2679e4`, whose acceptance
manifest and representative plan files came from different proof executions.

The proof ran from clean control-repository commit
`81a2d48d4475219e61bb8c20c7f4099ce472344e`. A later test-only reconciliation
commit does not alter the runtime artifacts recorded here.

## Result

- Seven representative ecosystems completed: C++, Go, Java, .NET, Python,
  Rust, and TypeScript.
- Every representative produced a source-bound assessment, an agentic
  composition plan, bounded document operations, a native patch, literal
  selected-fact claim bindings, and an independently reconstructed bundle.
- Every patch applied and every deterministic document validation passed.
- The prompt-injection negative control remained untrusted data.
- Cross-file canonical plan hashes agree for every representative.
- The control tree remained clean and stable for the complete proof.
- Remote write count was zero.

The authoritative machine-readable result is
`acceptance-manifest.json`. Every acceptance flag is `true`; `failures` is
empty. `sha256sums.txt` covers every other file in this directory.

## Reproduction

From a fresh checkout with the repository virtual environment and the same
locally available product-truth prerequisites:

```powershell
.venv/Scripts/python plans/investigations/tools/prove_local_readme_assessment_composition_representatives.py `
  --output-dir runs/reproduce-level8-local-readme-assessment-composition-81a2d48
```

The proof publisher refuses to overwrite an existing output directory and
uses a process-safe publication lock, preventing two executions from
interleaving files into one evidence root.
