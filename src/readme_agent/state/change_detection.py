"""Generic "did this specialist's tracked surface change since the last
accepted run" primitive -- Wave 7's shared extraction of `readme/
reconciliation.py::classify()`'s general shape (Wave 6). Exists so the seven
new Wave 7 specialists' own classify-first checks (the architectural
principle in `plans/master.md` decision #26 addendum: every specialist gets
a cheap classify node before doing real work) reuse one tested
implementation instead of six independent reimplementations -- each an
independent chance to reproduce the exact bug class decision #38 already
found and fixed once (the durable-skip fast path being permanently blind to
a real upstream change because its comparison didn't correctly distinguish
"never had a prior state" from "content genuinely unchanged").

`readme_reconciliation`'s own owned-span concept -- a specialist may track a
single "marker" whose disappearance must be distinguished from ordinary
content drift, since a naive fingerprint comparison alone can't tell "marker
removed" apart from "nothing changed" when removal happens to reproduce a
fingerprint the pre-marker content already had -- is kept general here, not
README-specific: a specialist with no such concept passes `True` for both
marker-presence arguments, which structurally disables the marker-lost/
mixed-change branches and degrades to a plain three-state classification.
"""

from dataclasses import dataclass, field
from typing import Literal

ChangeClassification = Literal[
    "FIRST_OBSERVATION",
    "NO_CHANGE",
    "CHANGED",
    "MARKER_LOST",
    "MIXED_CHANGE",
]


@dataclass
class ChangeResult:
    classification: ChangeClassification
    current_fingerprint: str
    marker_present_now: bool
    notes: list[str] = field(default_factory=list)


def classify_surface(
    *,
    current_fingerprint: str,
    prior_fingerprint: str | None,
    prior_marker_present: bool = True,
    marker_present_now: bool = True,
) -> ChangeResult:
    """`prior_fingerprint=None` means no prior accepted state exists yet --
    the very first observation for this domain, not an error. Callers that
    have no owned-marker concept simply never pass a `False` for either
    marker argument, in which case `marker_lost` can never be true and only
    `FIRST_OBSERVATION`/`NO_CHANGE`/`CHANGED` are ever returned."""
    if prior_fingerprint is None:
        return ChangeResult(
            classification="FIRST_OBSERVATION",
            current_fingerprint=current_fingerprint,
            marker_present_now=marker_present_now,
            notes=["no prior accepted state for this domain -- establishing baseline"],
        )

    content_changed = current_fingerprint != prior_fingerprint
    marker_lost = prior_marker_present and not marker_present_now

    if not content_changed and not marker_lost:
        classification: ChangeClassification = "NO_CHANGE"
    elif content_changed and marker_lost:
        classification = "MIXED_CHANGE"
    elif marker_lost:
        classification = "MARKER_LOST"
    else:
        classification = "CHANGED"

    return ChangeResult(
        classification=classification,
        current_fingerprint=current_fingerprint,
        marker_present_now=marker_present_now,
    )
