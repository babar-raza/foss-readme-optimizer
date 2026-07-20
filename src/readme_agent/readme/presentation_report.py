"""Read-only diagnostic report on README presentation quality (Phase 21,
decision #9 as corrected by docs/presentation-standard.md). Distinct from
GapReport: gap_detector checks four specific promotional-link elements; this
checks the broader visitor-experience dimensions the presentation standard
defines. Never gates a run by itself -- see validation/rules/
product_first_opening.py and commercial_mention_discipline.py for the two
dimensions promoted to hard validator gates.

Scope, per the Phase 21 design record (only dimensions checkable from README
text + facts without a durable-state/drift system or an asset pipeline):
  1. opening explains the product with a concrete verb/phrase
  3. audience/ecosystem/format stated in the opening block
  5. install path resolves against the real package registry (optional live check)
  6. at least one runnable example beyond the install snippet
  7. section headings use consistent Markdown levels
Dimensions 2 and 9 (no promo before explanation; commercial-mention
discipline) are hard validator gates, not part of this report. Dimensions 4
(license recognition), 8 (visual usefulness), and 10 (no fact lost) belong to
Phases 23, 24, and 25 respectively.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field

_OPENING_WINDOW_LINES = 15

# Verified against the three real pilot READMEs before being finalized --
# "working with", "library for", and "implementation of" are how cells/java,
# pdf/java, and 3d/java actually phrase their opening sentence; a narrower
# verb-only list would false-negative on all three.
_CONCRETE_PHRASES = (
    "create",
    "creating",
    "read",
    "reading",
    "write",
    "writing",
    "convert",
    "converting",
    "generate",
    "generating",
    "parse",
    "parsing",
    "process",
    "processing",
    "render",
    "rendering",
    "export",
    "exporting",
    "import",
    "importing",
    "extract",
    "extracting",
    "modify",
    "modifying",
    "build",
    "building",
    "manipulate",
    "manipulating",
    "load",
    "loading",
    "save",
    "saving",
    "edit",
    "editing",
    "handle",
    "handling",
    "work with",
    "working with",
    "library for",
    "implementation of",
    "provides",
    "toolkit for",
    "sdk for",
)
_ECOSYSTEM_KEYWORDS = {
    "java": ("java",),
    "net": (".net", "c#", "dotnet", "csharp"),
    "python": ("python",),
    "typescript": ("typescript", "javascript", "node"),
    "cpp": ("c++", "cpp"),
    "go": ("go", "golang"),
}
_ALL_ECOSYSTEM_KEYWORDS = tuple(kw for kws in _ECOSYSTEM_KEYWORDS.values() for kw in kws)
_HEADING_RE = re.compile(r"^(#{1,6})\s", re.MULTILINE)


def _is_prose_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("#"):
        return False
    if stripped.startswith("[![") or stripped.startswith("!["):
        return False
    return True


def product_explanation_offset(text: str) -> int | None:
    """Character offset of the first prose line, within the opening window,
    that reads as a product description (>= 8 words, contains a concrete
    phrase). None if no such line exists. Public: shared by this report and
    the product_first_opening validator rule -- both need the exact position,
    not just a yes/no answer, to compare against where a commercial link
    first appears."""
    offset = 0
    for line in text.split("\n")[:_OPENING_WINDOW_LINES]:
        if (
            _is_prose_line(line)
            and len(line.split()) >= 8
            and any(phrase in line.lower() for phrase in _CONCRETE_PHRASES)
        ):
            return offset
        offset += len(line) + 1  # +1 for the newline consumed by split("\n")
    return None


def _opening_block(text: str) -> str:
    lines = [ln for ln in text.split("\n")[:_OPENING_WINDOW_LINES] if _is_prose_line(ln)]
    return " ".join(lines[:3])


def _states_audience_or_ecosystem(opening: str, platform: str | None) -> tuple[bool, str | None]:
    lower = opening.lower()
    keywords = _ECOSYSTEM_KEYWORDS.get(platform or "", ())
    if any(kw in lower for kw in keywords) or any(kw in lower for kw in _ALL_ECOSYSTEM_KEYWORDS):
        return True, opening or None
    return False, None


def _has_runnable_example(text: str) -> tuple[bool, str]:
    fence_count = text.count("```")
    blocks = fence_count // 2
    if fence_count >= 4:
        return True, f"{blocks} fenced code blocks found"
    return False, f"only {blocks} fenced code block(s) found"


def _heading_levels_consistent(text: str) -> tuple[bool, str | None]:
    levels = [len(m.group(1)) for m in _HEADING_RE.finditer(text)]
    if len(levels) < 2:
        return True, "fewer than two headings -- nothing to check"
    skips = [
        f"H{levels[i]}->H{levels[i + 1]}"
        for i in range(len(levels) - 1)
        if levels[i + 1] - levels[i] > 1
    ]
    if skips:
        return False, f"heading level(s) skipped: {', '.join(skips)}"
    return True, None


@dataclass
class READMEPresentationReport:
    explains_product_in_opening: bool
    states_audience_or_ecosystem: bool
    has_runnable_example: bool
    heading_levels_consistent: bool
    install_path_resolved: bool | None  # None = not checked (no resolver supplied)
    evidence: dict[str, str | None] = field(default_factory=dict)

    @property
    def diagnostic_gaps(self) -> list[str]:
        gaps = [
            name
            for name, ok in (
                ("explains_product_in_opening", self.explains_product_in_opening),
                ("states_audience_or_ecosystem", self.states_audience_or_ecosystem),
                ("has_runnable_example", self.has_runnable_example),
                ("heading_levels_consistent", self.heading_levels_consistent),
            )
            if not ok
        ]
        if self.install_path_resolved is False:
            gaps.append("install_path_resolved")
        return gaps


def detect_presentation(
    readme_text: str,
    *,
    platform: str | None = None,
    ecosystem: str | None = None,
    manifest: dict[str, str] | None = None,
    resolver: Callable[[str, dict[str, str]], object] | None = None,
) -> READMEPresentationReport:
    """resolver, if supplied, is a callable(ecosystem, manifest) -> ResolutionResult
    (see ecosystems/resolver.py) used for dimension 5. Left unset,
    install_path_resolved stays None (not checked) -- matching the opt-in-only,
    never-a-default-hard-gate pattern links/validator.py already establishes
    for live network checks."""
    opening = _opening_block(readme_text)
    explains = product_explanation_offset(readme_text) is not None
    audience, audience_ev = _states_audience_or_ecosystem(opening, platform)
    example, example_ev = _has_runnable_example(readme_text)
    headings, headings_ev = _heading_levels_consistent(readme_text)

    install_resolved: bool | None = None
    install_ev: str | None = None
    if resolver is not None and ecosystem and manifest:
        result = resolver(ecosystem, manifest)
        install_resolved = getattr(result, "found", None)
        install_ev = getattr(result, "detail", None)

    return READMEPresentationReport(
        explains_product_in_opening=explains,
        states_audience_or_ecosystem=audience,
        has_runnable_example=example,
        heading_levels_consistent=headings,
        install_path_resolved=install_resolved,
        evidence={
            "explains_product_in_opening": opening or None,
            "states_audience_or_ecosystem": audience_ev,
            "has_runnable_example": example_ev,
            "heading_levels_consistent": headings_ev,
            "install_path_resolved": install_ev,
        },
    )
