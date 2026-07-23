"""Repository-wide, multi-ecosystem profile (Wave 3, `ECO-001`/`ECO-002`/
`ECO-003`) -- pydantic, matching `capabilities/schema.py`'s style."""

from pydantic import BaseModel, Field


class DetectedEcosystem(BaseModel):
    ecosystem: str
    manifest_path: str
    confidence: float
    evidence: str


class PackageRoot(BaseModel):
    """One independently-buildable/publishable unit within a repository --
    Wave 11.1 (`ECO-004`), closing `inspection/file_inventory.py::
    resolve_manifest_candidates()`'s own named "one manifest path per
    ecosystem" monorepo-support limitation. A repository with N
    independently buildable modules (a multi-module Maven/Gradle tree, a
    multi-`.csproj` .NET solution, an npm/Yarn workspace) gets N of these,
    not one flattened, potentially misleading root. `detected_ecosystems`
    above is unchanged and still reflects the original "first match per
    ecosystem" view; `package_roots` is the additive, complete view."""

    path: str  # repo-relative directory containing this root's manifest ("." for the repo root)
    ecosystem: str
    manifest_path: str  # repo-relative path to the manifest file itself
    confidence: float
    evidence: str


class RepositoryProfile(BaseModel):
    """`detected_ecosystems` is a list, not a single string (`ECO-001`) --
    a repository can have more than one manifest at once (a real,
    proven-in-production case for Java: pom.xml or build.gradle; Python:
    pyproject.toml or setup.py). `unresolved_manifests` records manifest-
    shaped files matched to no registered ecosystem, never silently guessed
    (`ECO-003`). `package_roots` (Wave 11.1, `ECO-004`) is the additive,
    multi-root-aware view -- see `PackageRoot`'s own docstring."""

    org_repo: str
    detected_ecosystems: list[DetectedEcosystem] = Field(default_factory=list)
    unresolved_manifests: list[str] = Field(default_factory=list)
    package_roots: list[PackageRoot] = Field(default_factory=list)
