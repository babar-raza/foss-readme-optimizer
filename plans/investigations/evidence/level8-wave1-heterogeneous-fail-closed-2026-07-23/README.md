# Wave 1 heterogeneous fail-closed proof

This evidence bundle verifies the Level-8 Wave 1 terminal-classification and unsupported-ecosystem
gates against real registered repositories on 2026-07-23. Every live run used the production
`readme-agent supervise` entry point. No target repository was written or pushed.

## Results

| Repository | Ecosystem | Observation |
|---|---|---|
| `aspose-cells-foss/Aspose.Cells-FOSS-for-.NET` | .NET | Live run returned `BLOCKED`; the exact unresolved `readme_presentation` verification failure became the terminal reason. |
| `aspose-cells-foss/Aspose.Cells-FOSS-for-Python` | Python | Live control returned `CONVERGED_NO_CHANGE` because this run had no unresolved specialist error. The earlier real error is replayed below and now returns `BLOCKED`. |
| `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp` | C++ | The first live run exposed an ordering defect: `repair_exhausted` hid the more specific specialist failure. The classifier was corrected and the second live run returned `BLOCKED` with the exact specialist failure. Both runs are retained. |
| `aspose-pdf-foss/Aspose-PDF-FOSS-for-Go` | Go | Live run returned `BLOCKED`; the exact unresolved prose-verification failure became the terminal reason. |
| `aspose-cells-foss/Aspose.Cells-FOSS-for-Rust` | Rust | Live run returned explicit `BLOCKED (unsupported_ecosystem:rust)` and process exit code 1. |

`historical-false-success-classification-replay.json` extracts the actual unresolved specialist
statuses from the earlier heterogeneous run that incorrectly returned
`CONVERGED_NO_CHANGE`/exit 0. It passes all four historical .NET, Python, C++, and Go statuses
through the current `final_status()` classifier and verifies exact `BLOCKED` results and reasons.
The source log's SHA-256 is embedded in the replay record.

The `*-terminal-evidence/` directories are immutable copies of the corresponding runtime
`RunManifestV2`, decisions, specialist results, and task graph. The C++ precedence-gap bundle is
retained as failure-discovery evidence rather than overwritten by the corrected rerun.

After the typed-contract and registry-construction hardening was complete, the .NET case was run
again from the final source. `cells-dotnet-final-source-supervisor.log` and its separate
`cells-dotnet-final-source-exit-code.txt` record the exact `BLOCKED` result and exit code 1;
`cells-dotnet-final-source-terminal-evidence/` contains that run's evidence.

`canonical-mutation-path-audit.json` parses the final source tree and proves the local commit,
product-branch push, and pull-request creation primitives are referenced only by their registered
capabilities. It also proves compatibility command handlers call `supervise_repo()` and contain
no legacy orchestrator or commit call. `sha256sums.txt` covers every other file in this bundle.
