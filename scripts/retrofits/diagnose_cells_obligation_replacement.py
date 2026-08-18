#!/usr/bin/env python
"""2026-08-18: pinpoint exactly which `verified_obligation_replacement`
resolution fails `mandatory_claim_replacements_have_exact_provenance` for
aspose-cells-foss/Aspose.Cells-FOSS-for-Python, by replaying the real check
functions against data reconstructed from an already-captured evidence
bundle -- no live pipeline re-run, no new provider calls. Kept after use as
the reusable diagnostic pattern for this class of question (which real
Pydantic models does the mechanical claim-accountability validator actually
see); see the GOV-014 backlog row this was opened to resolve.

Usage: ./.venv/Scripts/python scripts/retrofits/diagnose_cells_obligation_replacement.py \
    <evidence_dir>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from readme_agent.facts.schema_v2 import ProductFactsV2  # noqa: E402
from readme_agent.readme.claim_accountability_models import (  # noqa: E402
    ReadmeClaimAccountabilityV1,
)
from readme_agent.readme.claim_replacement_validation import (  # noqa: E402
    replacement_candidate_claims_are_exact,
    replacement_provenance_is_exact,
)
from readme_agent.readme.document_plan import (  # noqa: E402
    CandidateContentProvenanceV1,
    SourceClaimResolutionV1,
)
from readme_agent.readme.source_claim_contradiction import (  # noqa: E402
    contradicted_source_claim_fact_ids,
)


def main() -> None:
    evidence_dir = Path(sys.argv[1])
    payload = json.loads((evidence_dir / "specialist_results.json").read_text(encoding="utf-8"))
    render_result = payload["readme_presentation"]["details"]["current_failure_artifacts"][
        "render_result"
    ]
    plan = render_result["readme_document_plan"]
    facts = ProductFactsV2.model_validate(render_result["product_facts_v2"])
    source_text = render_result["source_text"]
    accountability = plan["claim_accountability"]
    source_by_id = {
        record["claim_id"]: record
        for record in accountability["claims"]
        if record["stage"] == "source"
    }
    candidate_records = [
        ReadmeClaimAccountabilityV1.model_validate(record)
        for record in accountability["claims"]
        if record["stage"] == "candidate"
    ]
    provenance_by_id = {
        item["provenance_id"]: CandidateContentProvenanceV1.model_validate(item)
        for item in plan["candidate_content_provenance"]
    }
    resolutions = {
        item["claim_id"]: SourceClaimResolutionV1.model_validate(item)
        for item in plan["source_claim_resolutions"]
    }

    total = 0
    failing = []
    for claim_id, resolution in resolutions.items():
        if resolution.resolution != "verified_obligation_replacement":
            continue
        total += 1
        source_record = source_by_id.get(f"source:{claim_id}")
        reasons = []
        if source_record is None:
            reasons.append("no matching source-stage accountability record")
        else:
            if source_record["survives_in_candidate"] is not False:
                reasons.append(
                    f"survives_in_candidate={source_record['survives_in_candidate']!r} (need False)"
                )
            if source_record["expected_disposition"] != "verified_obligation_replacement":
                reasons.append(
                    "expected_disposition="
                    f"{source_record['expected_disposition']!r} "
                    "(need verified_obligation_replacement)"
                )
        provenance_exact = replacement_provenance_is_exact(
            resolution,
            facts,
            provenance_by_id,
            exact_source_fact_ids=(
                source_record["accepted_fact_ids"] if source_record is not None else None
            ),
            exact_source_fact_coordinates=(
                source_record["accepted_fact_coordinates"]
                if source_record is not None and resolution.obligation_id == "golden_workflow"
                else None
            ),
            allow_contradicted_source_subset=bool(resolution.contradiction_fact_ids),
        )
        if not provenance_exact:
            reasons.append("replacement_provenance_is_exact() -> False")
        claims_exact = replacement_candidate_claims_are_exact(
            resolution, candidate_records, provenance_by_id
        )
        if not claims_exact:
            reasons.append("replacement_candidate_claims_are_exact() -> False")
        if resolution.contradiction_fact_ids:
            expected_contradictions = contradicted_source_claim_fact_ids(
                source_text,
                # source_claim_by_id[claim_id] would be the assessed claim; the resolution's
                # own byte range is an exact stand-in for this diagnostic's purposes.
                type(
                    "FakeClaim",
                    (),
                    {
                        "source_byte_start": resolution.source_byte_start,
                        "source_byte_end": resolution.source_byte_end,
                    },
                )(),
                facts,
            )
            if set(resolution.contradiction_fact_ids) != expected_contradictions:
                reasons.append(
                    "contradiction_fact_ids mismatch: "
                    f"resolution={resolution.contradiction_fact_ids} "
                    f"expected={sorted(expected_contradictions)}"
                )
        if reasons:
            failing.append((claim_id, resolution.obligation_id, reasons))

    print(f"{total} verified_obligation_replacement resolutions checked")
    print(f"{len(failing)} failing")
    for claim_id, obligation_id, reasons in failing:
        print(f"\n{claim_id} (obligation={obligation_id}):")
        for reason in reasons:
            print(f"  - {reason}")


if __name__ == "__main__":
    main()
