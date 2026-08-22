"""Public compatibility seam for the process-isolated repository worker pool."""

from readme_agent.supervisor.portfolio_proof_engine.repository_worker_contracts import (
    DEFAULT_GRACE_PERIOD_SECONDS,
    DEFAULT_MAX_CAPTURE_BYTES,
    DEFAULT_PROVIDER_CONCURRENCY,
    DEFAULT_REPOSITORY_CONCURRENCY,
    PROVIDER_RESOURCE_CLASS,
    BatchReportV1,
    CancellationOutcomeV1,
    RepositoryJobSpecV1,
    ResourceRequirementV1,
    WorkerExitClassificationV1,
    WorkerResultV1,
    canonical_sha256,
    utc_now_iso,
)
from readme_agent.supervisor.portfolio_proof_engine.repository_worker_scheduler import (
    RepositoryWorkerPool,
)

__all__ = [
    "DEFAULT_GRACE_PERIOD_SECONDS",
    "DEFAULT_MAX_CAPTURE_BYTES",
    "DEFAULT_PROVIDER_CONCURRENCY",
    "DEFAULT_REPOSITORY_CONCURRENCY",
    "PROVIDER_RESOURCE_CLASS",
    "BatchReportV1",
    "CancellationOutcomeV1",
    "RepositoryJobSpecV1",
    "RepositoryWorkerPool",
    "ResourceRequirementV1",
    "WorkerExitClassificationV1",
    "WorkerResultV1",
    "canonical_sha256",
    "utc_now_iso",
]
