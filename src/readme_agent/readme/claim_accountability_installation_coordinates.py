"""Match deterministic source-build prose to one exact Python distribution coordinate."""

from __future__ import annotations

import hashlib
import json
import re

from readme_agent.facts.acquisition_schema import AcquisitionDecisionV1
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.acquisition_contracts import coordinate_rows, matching_coordinate_row
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.claim_accountability_models import StructuredFactCoordinateV1
from readme_agent.readme.document_templates import installation_text

_PYTHON_DISTRIBUTION = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?")


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _selected_manifest_distribution(
    facts: ProductFactsV2,
    coordinate_value: object,
) -> tuple[str, dict] | None:
    identity = facts.selected_fact("product.identity")
    identity_value = identity.value
    if not isinstance(identity_value, dict):
        return None
    ecosystem = str(identity_value.get("ecosystem") or identity_value.get("platform") or "")
    manifest_names = identity_value.get("manifest_names")
    if ecosystem != "python" or not isinstance(manifest_names, list):
        return None

    selected_name = next(
        (
            str(name).strip()
            for name in manifest_names
            if str(name).strip()
            and matching_coordinate_row(coordinate_value, {"name": str(name).strip()})
        ),
        "",
    )
    if not selected_name or _PYTHON_DISTRIBUTION.fullmatch(selected_name) is None:
        return None
    matching_rows = [
        row
        for row in coordinate_rows(coordinate_value)
        if str(row.get("name") or "").casefold() == selected_name.casefold()
    ]
    if len(matching_rows) != 1:
        return None
    selected_row = matching_rows[0]
    if str(selected_row.get("ecosystem") or "") != "python":
        return None
    return selected_name, selected_row


def python_source_build_distribution_coordinates(
    text: str,
    facts: ProductFactsV2,
    fact_id: str,
    value: object,
    source_revision: str | None,
) -> list[StructuredFactCoordinateV1]:
    """Bind only the exact deterministic claim naming one selected source distribution."""

    if not source_revision:
        return []
    acquisition = facts.selected_fact("installation.verified_acquisition")
    if acquisition.source.source_revision != source_revision:
        return []
    try:
        decision = AcquisitionDecisionV1.model_validate(acquisition.value)
    except ValueError:
        return []
    if (
        decision.ecosystem != "python"
        or decision.method != "source_build"
        or decision.outcome != "SOURCE_BUILD_VERIFIED"
        or decision.org_repo != facts.org_repo
        or decision.source_revision != source_revision
    ):
        return []

    selected = _selected_manifest_distribution(facts, value)
    if selected is None:
        return []
    distribution_name, coordinate_row = selected
    expected = installation_text(facts, facts.org_repo, source_revision)
    if expected is None:
        return []
    expected_bytes = expected.encode("utf-8")
    exact_claims = {
        expected_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8").strip()
        for claim in assess_material_claims(expected)
        if f"`{distribution_name}`"
        in expected_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
    }
    if text.strip() not in exact_claims:
        return []

    coordinate_hash = _canonical_sha256(coordinate_row)[:16]
    return [
        StructuredFactCoordinateV1(
            fact_id=fact_id,
            field="installation.coordinates",
            path=f"/python-distributions/{coordinate_hash}/name",
            value_sha256=_canonical_sha256(distribution_name),
        )
    ]
