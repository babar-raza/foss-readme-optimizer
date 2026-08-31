"""Vendored aspose.org unqualified-dependency-claim check: `self-contained
<noun>` must be recognized as describing example code, not the product."""

from __future__ import annotations

import sys

sys.path.insert(0, "src/readme_agent/vendored_asposeorg/scripts/pipeline")
sys.path.insert(0, "src/readme_agent/vendored_asposeorg/scripts/pipeline/lib")
sys.path.insert(0, "src/readme_agent/vendored_asposeorg/scripts/pipeline/commands/foss")
import readme_refresh_checks as vendored  # noqa: E402


def _phrases(text: str) -> list[str]:
    return [item["phrase"] for item in vendored._unqualified_dependency_claim_findings(text)]


def test_self_contained_illustration_is_not_flagged() -> None:
    """PF05-DEPCHECK-001: `aspose-cells-foss/Aspose.Cells-FOSS-for-Python`'s real
    candidate reads "self-contained illustration of introductory public API usage
    in Python." -- describing the example code, not asserting a dependency claim.
    The original exclusion list only covered example/snippet/sample/version."""

    assert _phrases("This is a self-contained illustration of the public API.") == []


def test_other_example_synonyms_are_also_not_flagged() -> None:
    for noun in ("demo", "demonstration", "walkthrough", "showcase", "script"):
        text = f"This is a self-contained {noun} of the public API."
        assert _phrases(text) == [], f"unexpectedly flagged for {noun!r}"


def test_self_contained_pattern_is_not_flagged() -> None:
    """PWD-040: `aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET`'s real candidate reads
    "It provides the minimal, self-contained pattern for getting started with
    Aspose.PDF FOSS for Net." in its Quick Start section -- describing the example
    code, not asserting a product-wide dependency claim. "pattern" was not yet in
    the exclusion list."""

    assert _phrases("It provides the minimal, self-contained pattern for getting started.") == []


def test_self_contained_product_claim_is_still_flagged() -> None:
    """Negative control: a real unqualified dependency-absence claim about the
    product itself must still fire -- the fix only widens the noun exclusion
    list, it does not weaken the check."""

    assert _phrases("This is a fully self-contained crate.") == ["self-contained"]


def test_other_absolute_dependency_claims_are_unaffected() -> None:
    assert _phrases("This library is dependency-free.") == ["dependency-free"]
    assert _phrases("The crate has zero dependencies.") == ["zero dependencies"]
    assert _phrases(
        "Requires a recent stable Rust toolchain (2021 edition) -- no external "
        "runtime or Microsoft Office installation is needed."
    ) == ["no external runtime"]
