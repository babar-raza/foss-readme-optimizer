"""Upstream-change drift classifier (Wave 6, decisions #38/#39) -- a scoped-
down promotion of `plans/investigations/tools/reconciliation_prototype.py`'s
three-way (base/accepted/current-upstream) idea onto real, tested code.

Deliberately dropped from the prototype, logged as `BACKLOG` rather than
silently reproduced: fuzzy/embedding-based rewrite-vs-edit similarity,
in-span content-tamper detection, community-file drift
(`COMMUNITY_FILE_DRIFT`), and `CONFLICTING_FACTS` claim-checking (needs the
full decision #22/`DOC-006` product-facts schema, still `RESEARCH-GATED`).

What's kept: a pure hash-and-presence comparison using the real
`readme/markers.py::find_span`/`SPAN_NAMES` (not the prototype's own weaker
span regex) -- callers persist `DriftResult` into the real
`GitStateBackend`/`DomainStateV1` (`state/domain_state.py::save_domain()`),
never the prototype's ad hoc `.state/` JSON store.
"""

from dataclasses import dataclass, field
from typing import Literal

from readme_agent.readme.facts import sha256_text
from readme_agent.readme.markers import SPAN_NAMES, find_span, remove_span

DriftClassification = Literal[
    "FIRST_OBSERVATION",
    "NO_CHANGE",
    "UPSTREAM_CHANGED",
    "OWNED_SPAN_LOST",
    "MIXED_CHANGE",
]


@dataclass
class DriftResult:
    classification: DriftClassification
    stripped_text_hash: str
    owned_span_present_now: bool
    notes: list[str] = field(default_factory=list)


def classify(
    *,
    current_readme_text: str,
    prior_stripped_text_hash: str | None,
    prior_owned_span_present: bool,
) -> DriftResult:
    """Compares the current README (with every owned span stripped) against
    the last-accepted stripped-content hash for this domain. `None` for
    `prior_stripped_text_hash` means no prior accepted state exists yet --
    the very first observation for this org_repo, not an error."""
    stripped_now = current_readme_text
    for span_name in SPAN_NAMES:
        stripped_now = remove_span(stripped_now, span_name)
    stripped_hash_now = sha256_text(stripped_now)
    span_present_now = find_span(current_readme_text, "resources") is not None

    if prior_stripped_text_hash is None:
        return DriftResult(
            classification="FIRST_OBSERVATION",
            stripped_text_hash=stripped_hash_now,
            owned_span_present_now=span_present_now,
            notes=["no prior accepted state for this domain -- establishing baseline"],
        )

    stripped_changed = stripped_hash_now != prior_stripped_text_hash
    span_lost = prior_owned_span_present and not span_present_now

    if not stripped_changed and not span_lost:
        classification: DriftClassification = "NO_CHANGE"
    elif stripped_changed and span_lost:
        classification = "MIXED_CHANGE"
    elif span_lost:
        classification = "OWNED_SPAN_LOST"
    else:
        classification = "UPSTREAM_CHANGED"

    return DriftResult(
        classification=classification,
        stripped_text_hash=stripped_hash_now,
        owned_span_present_now=span_present_now,
    )
