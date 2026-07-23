"""Wave 12.1 (`RDM-024`): scans EXISTING README text for an install-command
claim naming a specific package coordinate, and cross-checks it against
Wave 11.3's `ProductFactsV1.package_coordinates` (populated from Wave
11.2's live `verify_package_acquisition` outcomes). This is the concrete
mechanism the real `aspose-cells-foss/Aspose.Cells-FOSS-for-Java#1` PR
failure names as missing: `readme/renderer.py::render_missing_elements()`
is a pure function of a 4-boolean `GapReport` that never reads the rest of
the README, so a known-false Maven coordinate
(`<groupId>org.aspose</groupId><artifactId>aspose-cells-foss</artifactId>`,
confirmed live 2026-07-23 to still be the real README's own text, and
confirmed via `PKG-005`'s `verify_package_acquisition` to resolve to
`NOT_PUBLISHED` on Maven Central) can ship untouched even though the
system already possesses the evidence proving it false.

**Read-only, produces evidence-backed findings -- deliberately NOT wired
into `orchestrator.prepare_readme_candidate()`'s render/skip pipeline this
pass.** Two real, verified reasons, not a deferral for effort:

1. `readme/facts.py::compute_facts_hash()` deliberately excludes both
   README content and `gap_report` (decision #11: "it's *derived from*
   README content this tool itself rewrites... an output of rendering,
   not an independent input fact"). A conflict finding here depends on
   *live network state* (a resolver result), which can change with zero
   local file change and zero `facts_hash` change -- exactly the class of
   blind spot Wave 9.7's `state/freshness_contract.py` had to solve at the
   *supervisor* level for non-git surfaces. No render-level equivalent
   exists yet; wiring this into the render/skip decision without one would
   either force a live network call on every single render (a real,
   unmeasured cost/architecture change to a pipeline that is deliberately
   100% offline today) or silently miss a conflict whenever the skip path
   fires.
2. `prepare_readme_candidate()` is one of this project's most heavily
   load-bearing functions (idempotency, durable-skip, span-stripped
   re-detection, hash exclusions all precisely balanced, per its own
   docstring) -- correctly integrating a new signal into it is real,
   separate design work, not a drop-in addition.

Both are logged honestly as `RDM-025` (`BACKLOG`), not silently absorbed
into this row's own scope."""

import re
from dataclasses import dataclass

from readme_agent.facts.schema import ProductFactsV1

_MAVEN_DEP_RE = re.compile(
    r"<groupId>\s*([\w.\-]+)\s*</groupId>\s*<artifactId>\s*([\w.\-]+)\s*</artifactId>",
    re.IGNORECASE | re.DOTALL,
)
_PIP_INSTALL_RE = re.compile(r"pip install\s+([A-Za-z0-9_.\-]+)", re.IGNORECASE)
_NPM_INSTALL_RE = re.compile(r"npm install\s+([A-Za-z0-9_@/.\-]+)", re.IGNORECASE)
_NUGET_INSTALL_RE = re.compile(
    r"(?:dotnet add package|Install-Package)\s+([A-Za-z0-9_.\-]+)", re.IGNORECASE
)


@dataclass
class ClaimConflictFinding:
    """One README-text install claim that live-verified recon evidence
    (`PKG-005`) positively contradicts -- never raised for `CAPABILITY_GAP`/
    `BLOCKED_NETWORK` (couldn't check), only for a real, confirmed
    `NOT_PUBLISHED` result."""

    package_root_path: str
    ecosystem: str
    claimed_coordinate: str
    verification_outcome: str
    verification_detail: str
    readme_excerpt: str


def _claimed_coordinates(readme_text: str, ecosystem: str) -> list[tuple[str, str]]:
    """(claimed_coordinate, matched_excerpt) pairs found in the README text,
    using each ecosystem's own conventional install-command shape."""
    if ecosystem == "java":
        return [
            (f"{m.group(1)}:{m.group(2)}", m.group(0)) for m in _MAVEN_DEP_RE.finditer(readme_text)
        ]
    if ecosystem == "python":
        return [(m.group(1), m.group(0)) for m in _PIP_INSTALL_RE.finditer(readme_text)]
    if ecosystem == "typescript":
        return [(m.group(1), m.group(0)) for m in _NPM_INSTALL_RE.finditer(readme_text)]
    if ecosystem == "net":
        return [(m.group(1), m.group(0)) for m in _NUGET_INSTALL_RE.finditer(readme_text)]
    return []


def find_claim_conflicts(readme_text: str, facts: ProductFactsV1) -> list[ClaimConflictFinding]:
    """Cross-checks every `NOT_PUBLISHED` package-coordinate fact against
    what the README text itself claims for that same ecosystem. A
    coordinate whose `verification_outcome` is `REGISTRY_VERIFIED`/
    `CAPABILITY_GAP`/`BLOCKED_NETWORK`/`None` never produces a finding --
    only a positively-confirmed false claim does."""
    findings = []
    for coord in facts.package_coordinates:
        if coord.verification_outcome != "NOT_PUBLISHED":
            continue
        for claimed, excerpt in _claimed_coordinates(readme_text, coord.ecosystem):
            findings.append(
                ClaimConflictFinding(
                    package_root_path=coord.path,
                    ecosystem=coord.ecosystem,
                    claimed_coordinate=claimed,
                    verification_outcome=coord.verification_outcome,
                    verification_detail=coord.verification_detail or "",
                    readme_excerpt=excerpt,
                )
            )
    return findings
