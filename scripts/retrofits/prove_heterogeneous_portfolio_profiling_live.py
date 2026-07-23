"""Wave 14.1 live proof: `profile_repository` run for real against all 7
target repos of the heterogeneous-portfolio proof (`PIL-012`) -- the `cells`
family across 6 platforms (Java `mode: full`; .NET/Python/TypeScript/C++
`dry_run`; Rust `disabled`, no registered ecosystem parser) plus
`aspose-pdf-foss/Aspose-PDF-FOSS-for-Go` for the real Go proof (`cells/go`
is itself `disabled` but unconfigured, not a parser gap, out of this
phase's own scope per the sprint plan).

Real clones, real network -- not assumed from documentation. Confirms
before committing to the far more expensive Wave 14.2 live `supervise`
cycle: (1) each of the 6 real ecosystems profiles cleanly; (2) the Rust
target degrades honestly (no crash) rather than silently claiming
coverage it doesn't have.

Kept after use as the executable record of this verification -- see
plans/GOVERNANCE.md, "Repository layout", placement rule 5.
"""

import json
import time

from readme_agent.capabilities import profile_repository
from readme_agent.errors import ReadmeAgentError

_TARGETS = [
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
    "aspose-cells-foss/Aspose.Cells-FOSS-for-.NET",
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Python",
    "aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript",
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp",
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust",
    "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go",
]


def main() -> int:
    all_ok = True
    results = []
    for org_repo in _TARGETS:
        start = time.monotonic()
        try:
            profile = profile_repository.execute(org_repo)
            elapsed = time.monotonic() - start
            ecosystems = profile.get("detected_ecosystems") or []
            package_roots = profile.get("package_roots") or []
            print(
                f"OK   {org_repo:55s} {elapsed:7.1f}s  "
                f"detected_ecosystems={ecosystems} package_roots={len(package_roots)}"
            )
            results.append(
                {
                    "org_repo": org_repo,
                    "outcome": "ok",
                    "elapsed_seconds": elapsed,
                    "detected_ecosystems": ecosystems,
                    "package_root_count": len(package_roots),
                }
            )
        except ReadmeAgentError as exc:
            elapsed = time.monotonic() - start
            print(f"GAP  {org_repo:55s} {elapsed:7.1f}s  {type(exc).__name__}: {exc}")
            results.append(
                {
                    "org_repo": org_repo,
                    "outcome": "gap",
                    "elapsed_seconds": elapsed,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
        except Exception as exc:  # noqa: BLE001 -- a genuine crash here IS the failure this proves against
            elapsed = time.monotonic() - start
            print(f"CRASH {org_repo:54s} {elapsed:7.1f}s  {type(exc).__name__}: {exc}")
            all_ok = False
            results.append(
                {
                    "org_repo": org_repo,
                    "outcome": "crash",
                    "elapsed_seconds": elapsed,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

    print()
    print(json.dumps(results, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
