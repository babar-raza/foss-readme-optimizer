"""Map a candidate onto the frozen development benchmark obligations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.readme.readme_reconciliation import ReadmeReconciliationReportV1

BenchmarkDispositionV1 = Literal["accepted", "adapted", "quarantined", "not_applicable"]
CandidateBenchmarkDimensionStatusV1 = Literal[
    "EVIDENCE_BOUND_PENDING_ACCEPTANCE",
    "QUARANTINED_NOT_FACT_AUTHORITY",
    "NOT_APPLICABLE",
]

_PROFILE_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "aspose_benchmark_quality_profile.json"
)
_DIMENSION_EVIDENCE: dict[str, tuple[str, ...]] = {
    "information_coverage": ("candidate/claim-map.json", "knowledge-application.json"),
    "product_specificity": ("candidate/claim-map.json", "assessment/evidence-map.json"),
    "structure_and_navigation": (
        "assessment/current-readme-assessment.json",
        "planning/readme-document-plan.json",
        "candidate/README.md",
    ),
    "branding_and_visuals": (
        "planning/readme-document-plan.json",
        "candidate/README.md",
    ),
    "capability_depth": ("candidate/claim-map.json", "knowledge-application.json"),
    "installation_and_dependencies": (
        "candidate/claim-map.json",
        "candidate/README.md",
    ),
    "source_derived_examples": ("candidate/claim-map.json", "candidate/README.md"),
    "api_reference_depth": ("knowledge-application.json", "candidate/README.md"),
    "documentation_and_resources": ("candidate/claim-map.json", "candidate/README.md"),
    "limitations": ("candidate/claim-map.json", "candidate/README.md"),
    "development_and_testing": ("assessment/evidence-map.json", "candidate/README.md"),
    "licensing": ("candidate/claim-map.json", "candidate/README.md"),
    "inherited_content_accountability": (
        "assessment/evidence-map.json",
        "candidate/readme-reconciliation.json",
    ),
    "public_tone_and_process_hygiene": (
        "planning/readme-document-plan.json",
        "candidate/README.md",
    ),
}


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CandidateBenchmarkDimensionV1(_StrictFrozenModel):
    dimension_id: str = Field(min_length=3)
    benchmark_disposition: BenchmarkDispositionV1
    obligation: str = Field(min_length=3)
    applicable: bool
    status: CandidateBenchmarkDimensionStatusV1
    evidence_paths: list[str]

    @model_validator(mode="after")
    def _status_matches_disposition(self) -> CandidateBenchmarkDimensionV1:
        expected = {
            "accepted": "EVIDENCE_BOUND_PENDING_ACCEPTANCE",
            "adapted": "EVIDENCE_BOUND_PENDING_ACCEPTANCE",
            "quarantined": "QUARANTINED_NOT_FACT_AUTHORITY",
            "not_applicable": "NOT_APPLICABLE",
        }[self.benchmark_disposition]
        if self.status != expected:
            raise ValueError("candidate benchmark status disagrees with benchmark disposition")
        if self.applicable != (self.benchmark_disposition in {"accepted", "adapted"}):
            raise ValueError("candidate benchmark applicability disagrees with disposition")
        if self.applicable and not self.evidence_paths:
            raise ValueError("applicable benchmark dimensions require candidate evidence")
        return self


class CandidateBenchmarkComparisonV1(_StrictFrozenModel):
    schema_version: Literal[1] = 1
    comparison_type: Literal["CandidateBenchmarkComparisonV1"] = "CandidateBenchmarkComparisonV1"
    repository: str = Field(pattern=r"^[^/]+/[^/]+$")
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    benchmark_profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    benchmark_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    comparison_status: Literal["CANDIDATE_EVIDENCE_MAPPED"] = "CANDIDATE_EVIDENCE_MAPPED"
    acceptance_status: Literal["PENDING_DETERMINISTIC_AND_INDEPENDENT_REVIEW"] = (
        "PENDING_DETERMINISTIC_AND_INDEPENDENT_REVIEW"
    )
    benchmark_prose_used: Literal[False] = False
    runtime_dependency_on_aspose_org: Literal[False] = False
    dimensions: list[CandidateBenchmarkDimensionV1] = Field(min_length=1)

    @model_validator(mode="after")
    def _dimensions_are_unique(self) -> CandidateBenchmarkComparisonV1:
        ids = [item.dimension_id for item in self.dimensions]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate benchmark dimensions must be unique")
        return self


def load_benchmark_quality_profile(path: Path = _PROFILE_PATH) -> tuple[dict, str]:
    """Load the self-contained frozen profile and return its byte identity."""

    payload = path.read_bytes()
    profile = json.loads(payload)
    if (
        profile.get("profile_type") != "BenchmarkQualityProfileV1"
        or profile.get("state") != "BENCHMARK_PROFILE_FROZEN"
        or profile.get("runtime_dependency_on_aspose_org") is not False
    ):
        raise ValueError("Aspose benchmark quality profile is not qualified for local use")
    return profile, hashlib.sha256(payload).hexdigest()


def _validate_dimension_evidence(dimension_id: str, bundle_dir: Path) -> None:
    """Validate semantics where mere path existence could conceal failed evidence."""

    if dimension_id == "inherited_content_accountability":
        reconciliation_path = bundle_dir / "candidate" / "readme-reconciliation.json"
        ReadmeReconciliationReportV1.model_validate_json(
            reconciliation_path.read_text(encoding="utf-8")
        )


def build_candidate_benchmark_comparison(
    *,
    repository: str,
    source_revision: str,
    candidate_sha256: str,
    bundle_dir: Path,
    profile_path: Path = _PROFILE_PATH,
) -> CandidateBenchmarkComparisonV1:
    """Bind every benchmark dimension to local evidence without granting acceptance."""

    profile, profile_sha256 = load_benchmark_quality_profile(profile_path)
    dimensions: list[CandidateBenchmarkDimensionV1] = []
    for raw in profile["dimensions"]:
        dimension_id = str(raw["dimension_id"])
        disposition = cast(BenchmarkDispositionV1, str(raw["disposition"]))
        evidence = list(_DIMENSION_EVIDENCE.get(dimension_id, ()))
        missing = [relative for relative in evidence if not (bundle_dir / relative).is_file()]
        if missing:
            raise ValueError(
                f"benchmark dimension {dimension_id!r} lacks candidate evidence: {missing}"
            )
        _validate_dimension_evidence(dimension_id, bundle_dir)
        applicable = disposition in {"accepted", "adapted"}
        status: CandidateBenchmarkDimensionStatusV1 = (
            "EVIDENCE_BOUND_PENDING_ACCEPTANCE"
            if applicable
            else (
                "QUARANTINED_NOT_FACT_AUTHORITY"
                if disposition == "quarantined"
                else "NOT_APPLICABLE"
            )
        )
        dimensions.append(
            CandidateBenchmarkDimensionV1(
                dimension_id=dimension_id,
                benchmark_disposition=disposition,
                obligation=str(raw["obligation"]),
                applicable=applicable,
                status=status,
                evidence_paths=evidence,
            )
        )
    return CandidateBenchmarkComparisonV1(
        repository=repository,
        source_revision=source_revision,
        candidate_sha256=candidate_sha256,
        benchmark_profile_sha256=profile_sha256,
        benchmark_snapshot_sha256=str(profile["snapshot_sha256"]),
        dimensions=dimensions,
    )
