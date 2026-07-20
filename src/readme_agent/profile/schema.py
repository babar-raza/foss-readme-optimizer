"""Repository-wide, multi-ecosystem profile (Wave 3, `ECO-001`/`ECO-002`/
`ECO-003`) -- pydantic, matching `capabilities/schema.py`'s style."""

from pydantic import BaseModel, Field


class DetectedEcosystem(BaseModel):
    ecosystem: str
    manifest_path: str
    confidence: float
    evidence: str


class RepositoryProfile(BaseModel):
    """`detected_ecosystems` is a list, not a single string (`ECO-001`) --
    a repository can have more than one manifest at once (a real,
    proven-in-production case for Java: pom.xml or build.gradle; Python:
    pyproject.toml or setup.py). `unresolved_manifests` records manifest-
    shaped files matched to no registered ecosystem, never silently guessed
    (`ECO-003`)."""

    org_repo: str
    detected_ecosystems: list[DetectedEcosystem] = Field(default_factory=list)
    unresolved_manifests: list[str] = Field(default_factory=list)
