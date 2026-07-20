"""Per-element promotional-gap scanner -- the module the rest of the pipeline
hinges on. Scans the *entire* README (not just our own marker span), so a
repo whose promotion was hand-authored (the 3d family) is correctly detected
as already-compliant, and a repo that's only partially done (pdf/java) is
correctly detected as missing exactly one thing.

Calibrated against 14 real READMEs captured live from GitHub on 2026-07-17
(tests/fixtures/readmes/real_audit_2026-07-17/), not synthetic cases alone --
see tests/unit/test_gap_detector.py for the ground-truth table this must
reproduce exactly.
"""

import re
from dataclasses import dataclass, field

_LICENSE_HEADING_RE = re.compile(r"^#{1,6}\s*license\b", re.IGNORECASE | re.MULTILINE)
_LICENSE_BADGE_RE = re.compile(r"img\.shields\.io/badge/license", re.IGNORECASE)
# Org-agnostic on purpose (generic-engine decision -- see AGENTS/plan): matches
# any "products.<vendor>.org"/".com"-shaped URL, not literally "aspose". Aspose
# real data matches this as a strict subset, so the 2026-07-17 ground-truth
# fixture corpus (all real Aspose repos) is unaffected by this genericity.
_PRODUCTS_ORG_RE = re.compile(r"products\.[a-z0-9-]+\.org\b", re.IGNORECASE)
_PRODUCTS_COM_RE = re.compile(r"products\.[a-z0-9-]+\.com\b", re.IGNORECASE)
_COMMERCIAL_LINK_RE = re.compile(r"products\.[a-z0-9-]+\.(org|com)\b", re.IGNORECASE)

# Deliberately not a single "mentions commercial" keyword -- audit finding #2:
# "part of the Aspose family" (pdf/Go) and a bare "free version of X" linking
# to GitHub (words/Python) both needed to NOT count on their own; requiring
# co-location with a real products.aspose.* link (see _relationship_explained)
# is what actually distinguishes real relationship prose from decoration.
#
# "subset" was tried and removed: it false-positived on pdf/Go's bundled-font
# licensing text ("Latin-subset copies of four metric-compatible fonts"),
# which sits near the file's one products.aspose.com link but has nothing to
# do with the FOSS-vs-commercial relationship -- caught by the ground-truth
# fixture test, not by inspection, which is exactly why that test exists.
_RELATIONSHIP_KEYWORDS_RE = re.compile(
    r"\b(commercial|full-featured|full version|upgrade|paid|premium|proprietary|"
    r"broader feature|free version|lightweight version|a subset of)\b",
    re.IGNORECASE,
)
_CO_LOCATION_WINDOW = 600  # chars either side of a keyword match, calibrated
# against the real fixture corpus -- not a precisely validated constant.

REQUIRED_ELEMENTS = (
    "license_mentioned",
    "products_org_link",
    "products_com_link",
    "relationship_explained",
)


@dataclass
class GapReport:
    license_mentioned: bool
    products_org_link: bool
    products_com_link: bool
    relationship_explained: bool
    evidence: dict[str, str | None] = field(default_factory=dict)

    @property
    def gaps(self) -> list[str]:
        return [name for name in REQUIRED_ELEMENTS if not getattr(self, name)]

    @property
    def fully_compliant(self) -> bool:
        return not self.gaps


def _excerpt(text: str, match: re.Match) -> str:
    start = max(0, match.start() - 20)
    end = min(len(text), match.end() + 40)
    return text[start:end].replace("\n", " ").strip()


def _license_mentioned(text: str, detected_license: str | None) -> tuple[bool, str | None]:
    match = _LICENSE_HEADING_RE.search(text)
    if match:
        return True, _excerpt(text, match)
    match = _LICENSE_BADGE_RE.search(text)
    if match:
        return True, _excerpt(text, match)
    if detected_license:
        pattern = re.compile(
            rf"\b{re.escape(detected_license)}\b.{{0,40}}license|license.{{0,40}}\b{re.escape(detected_license)}\b",
            re.IGNORECASE | re.DOTALL,
        )
        match = pattern.search(text)
        if match:
            return True, _excerpt(text, match)
    return False, None


def _relationship_explained(text: str) -> tuple[bool, str | None]:
    for kw_match in _RELATIONSHIP_KEYWORDS_RE.finditer(text):
        window_start = max(0, kw_match.start() - _CO_LOCATION_WINDOW)
        window_end = min(len(text), kw_match.end() + _CO_LOCATION_WINDOW)
        window = text[window_start:window_end]
        if _COMMERCIAL_LINK_RE.search(window):
            return True, _excerpt(text, kw_match)
    return False, None


def commercial_com_link_matches(text: str) -> list[re.Match]:
    """Public accessor: every products.<vendor>.com occurrence, in document
    order. Deliberately .com-only, not the combined org|com pattern -- .org is
    the FOSS/community reference, not a "commercial mention" in the
    promotional-density sense decision #9 targets. Used by the
    product_first_opening and commercial_mention_discipline validator rules."""
    return list(_PRODUCTS_COM_RE.finditer(text))


def first_commercial_link_index(text: str) -> int | None:
    """Character offset of the first products.<vendor>.com occurrence, or
    None. Public: shared by the product_first_opening validator rule."""
    match = _PRODUCTS_COM_RE.search(text)
    return match.start() if match else None


def detect(readme_text: str, detected_license: str | None = None) -> GapReport:
    license_ok, license_ev = _license_mentioned(readme_text, detected_license)

    org_match = _PRODUCTS_ORG_RE.search(readme_text)
    com_match = _PRODUCTS_COM_RE.search(readme_text)
    relationship_ok, relationship_ev = _relationship_explained(readme_text)

    return GapReport(
        license_mentioned=license_ok,
        products_org_link=org_match is not None,
        products_com_link=com_match is not None,
        relationship_explained=relationship_ok,
        evidence={
            "license_mentioned": license_ev,
            "products_org_link": _excerpt(readme_text, org_match) if org_match else None,
            "products_com_link": _excerpt(readme_text, com_match) if com_match else None,
            "relationship_explained": relationship_ev,
        },
    )
