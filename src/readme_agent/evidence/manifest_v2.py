"""Wave 13.1 (`EVID-001`+): a unified run-manifest schema for
`supervisor/loop.py::supervise_repo()`'s own evidence bundle, consolidating
fields Waves 8-9 already compute in scattered places (control-plane
fingerprint, domain coverage, per-surface freshness) into one canonical,
typed record -- replacing `_write_supervise_evidence()`'s own ad hoc
`manifest.json` dict literal. Reuses `evidence/writer.py`'s existing
redaction/atomic-write/checksum helpers (`write_run_manifest_v2()`, added
there) -- no parallel writer.

Fields not yet populated by any built mechanism stay explicit `None`,
named here with which wave/phase is expected to populate them -- never
faked to fill a field early, matching `capabilities/schema.py`'s own
established "Field-population policy" convention."""

from pydantic import BaseModel, Field

from readme_agent.state.schema import SurfaceFreshnessContractV1


class RunManifestV2(BaseModel):
    run_id: str
    org_repo: str
    status: str
    timestamp: str

    prompt_registry_content_hash: str | None = None
    control_plane_fingerprint: str | None = None
    upstream_revision: str | None = None
    domain_coverage_complete: bool | None = None
    # Wave 9.7 (`FRESH-001`+): whatever `SupervisorStateV1.surface_freshness`
    # was carried forward or refreshed to by the end of this specific run --
    # `{}` for a run where the specialist tier never reached that point
    # (e.g. a clone failure), not a faked "everything fresh" claim.
    surface_freshness: dict[str, SurfaceFreshnessContractV1] = Field(default_factory=dict)

    facts_hash: str | None = None
    llm_call_count: int = 0
    llm_calls: list[str] = Field(default_factory=list)

    # Wave 13.1 (`GOV-012`/`SAFE-014`/`SAFE-017`): which requirement IDs
    # this run exercised, and whether each was exercised without error --
    # reuses `specialists/independent_verification.py`'s own already-built
    # `requirement_map` (Wave 8c) rather than recomputing it. `{}` when
    # `independent_verification` did not run this turn (e.g. a shortcut or
    # clone-failure path), not a faked "nothing to report."
    requirement_ids_exercised: dict[str, bool] = Field(default_factory=dict)

    # Wave 13.2/13.3 (`AUTH-001`-`006`): populated once the authorization-
    # record mechanism exists; `None` until then, not faked.
    authorization_record_id: str | None = None
    # Wave 9.5 (`RUN-006`): the trigger identity that initiated this run,
    # when known -- not yet threaded from `commands.py::cmd_supervise()`
    # into `supervise_repo()`'s own evidence-writing path; `None` until a
    # later phase wires it through.
    trigger_dedup_key: str | None = None
