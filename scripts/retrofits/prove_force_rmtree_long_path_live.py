"""SCL-010 live proof: `force_rmtree()`'s `WinError 145` ("directory not
empty") fix, against the exact real repository that reproduced it.

Found live 2026-07-25 (twice, reproducibly) running the Level-5 portfolio-
wide local-proposal pipeline (`plans/investigations/tools/
collect_portfolio_readme_proposal_evidence.py`) against `aspose-words-foss/
Aspose.Words-FOSS-for-.NET` (~15,522 files -- the same outlier repo `SCL-009`
already documents): a path like `runs/baseline/aspose-words-foss__
Aspose.Words-FOSS-for-.NET/Aspose.Foundation/Aspose.Foundation/Generated/
Aspose.EnumExtensionsGenerator/Aspose.EnumExtensionsGenerator.
EnumExtensionsGenerator` is 254 chars for the directory alone, well past the
260-char Windows `MAX_PATH` limit once files inside are counted. Unit tests
(`tests/unit/test_gitsafety.py::TestForceRmtree`) prove the new handler logic
in isolation via monkeypatched `os.rmdir` failures; this script is the real-
filesystem confirmation the taskcard requires, since this bug was specifically
about real Windows filesystem behavior mocks can miss.

Deliberately narrower than a full portfolio re-run (which would also pay the
LLM-driven facts/rendering pipeline's cost for all ~28 repos): clones only
this one repository via the real `clone_baseline()`/`force_rmtree()`
primitives this fix touches, directly, into the exact same real, cwd-
relative `runs/baseline/...` path the original bug hit (`paths.baseline_dir`
is `Path.cwd() / "runs" / "baseline" / f"{org}__{repo}"` -- this script must
run with the repo root as cwd for that path to match).

Exercises BOTH of the two real call shapes that could have hit the bug:
  1. `clone_baseline()` called a second time (after `reset_clone_memo()`)
     against an already-populated baseline path -- this is what
     `clone_baseline()` itself does internally before every re-clone
     (`if baseline_path.exists(): force_rmtree(baseline_path)`), and is very
     plausibly how the original bug surfaced given the evidence-collector
     script leaves `runs/baseline/...` populated across separate process
     invocations (the requirements.md row notes this was hit "twice").
  2. A direct, standalone `force_rmtree()` call afterward, matching
     `orchestrator.py`'s own post-profile cleanup reuse of the same
     primitive.

Cleans up after itself either way (a real ~15,522-file clone must not be left
behind in the working tree) -- the final cleanup call is itself proof #2
above, not a separate teardown step.

Kept after use as the executable record of this verification -- see
plans/GOVERNANCE.md, "Repository layout", placement rule 5.
"""

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent import paths  # noqa: E402
from readme_agent.gitsafety.clone import (  # noqa: E402
    clone_baseline,
    force_rmtree,
    reset_clone_memo,
)
from readme_agent.registry.loader import find_entry  # noqa: E402

ORG_REPO = "aspose-words-foss/Aspose.Words-FOSS-for-.NET"


def _deepest_path_stats(root: Path) -> tuple[int, str]:
    """Longest absolute path under `root`, to confirm this run's real clone
    actually contains a near/over-MAX_PATH path -- not just "some clone that
    happened not to hit the bug this time"."""
    longest = 0
    longest_path = ""
    for candidate in root.rglob("*"):
        length = len(str(candidate))
        if length > longest:
            longest = length
            longest_path = str(candidate)
    return longest, longest_path


def main() -> int:
    entry = find_entry(ORG_REPO)
    if entry is None:
        print(f"FAIL: {ORG_REPO} not found in the registry", file=sys.stderr)
        return 1

    baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
    print(f"baseline_path = {baseline_path}")
    print(f"baseline_path length = {len(str(baseline_path.resolve()))} chars")

    if baseline_path.exists():
        print(
            "baseline_path already exists from a prior run -- clearing it first "
            "via force_rmtree() so this proof starts from a clean, known state."
        )
        force_rmtree(baseline_path)

    print("\n=== step 1: first clone_baseline() (real network clone) ===", flush=True)
    start = time.monotonic()
    clone_baseline(entry, baseline_path)
    print(f"  cloned in {time.monotonic() - start:.1f}s")

    longest, longest_path = _deepest_path_stats(baseline_path)
    print(f"  deepest path under baseline: {longest} chars")
    print(f"  {longest_path}")
    if longest < 260:
        print(
            "  WARNING: no path over 260 chars found -- this run may not actually "
            "exercise the MAX_PATH condition the bug needs.",
            file=sys.stderr,
        )

    print(
        "\n=== step 2: reset_clone_memo() + clone_baseline() again -- this is the "
        "exact internal path (force_rmtree(baseline_path) before re-clone) that "
        "originally raised an uncaught WinError 145 ===",
        flush=True,
    )
    reset_clone_memo()
    start = time.monotonic()
    clone_baseline(entry, baseline_path)
    print(f"  re-cloned in {time.monotonic() - start:.1f}s -- no WinError 145 raised")

    print(
        "\n=== step 3: standalone force_rmtree() (matches orchestrator.py's own "
        "post-profile cleanup reuse) ===",
        flush=True,
    )
    start = time.monotonic()
    force_rmtree(baseline_path)
    print(f"  removed in {time.monotonic() - start:.1f}s -- no WinError 145 raised")

    assert not baseline_path.exists(), "cleanup did not actually remove the directory"

    print(
        "\nPASS: zero WinError 145 across both the internal re-clone cleanup path "
        "and a standalone force_rmtree() call, against the real repository that "
        "originally reproduced SCL-010."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
