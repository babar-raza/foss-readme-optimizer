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

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from readme_agent.state.schema import SurfaceFreshnessContractV1


class RunManifestV2(BaseModel):
    run_id: str
    org_repo: str
    status: str
    timestamp: str

    prompt_registry_content_hash: str | None = None
    prompt_hashes_by_id: dict[str, str] = Field(default_factory=dict)
    prompt_dependency_hashes: dict[str, str] = Field(default_factory=dict)
    control_plane_fingerprint: str | None = None
    upstream_revision: str | None = None
    domain_coverage_complete: bool | None = None
    # Wave 9.7 (`FRESH-001`+): whatever `SupervisorStateV1.surface_freshness`
    # was carried forward or refreshed to by the end of this specific run --
    # `{}` for a run where the specialist tier never reached that point
    # (e.g. a clone failure), not a faked "everything fresh" claim.
    surface_freshness: dict[str, SurfaceFreshnessContractV1] = Field(default_factory=dict)

    facts_hash: str | None = None
    llm_accounting_status: Literal["EXACT", "UNKNOWN_LEGACY"] = "UNKNOWN_LEGACY"
    llm_call_count: int | None = None
    llm_calls: list[str] = Field(default_factory=list)
    llm_call_ids: list[str] = Field(default_factory=list)
    llm_calls_by_job: dict[str, int] = Field(default_factory=dict)
    llm_fixture_call_count: int | None = None
    llm_cache_reuse_count: int | None = None
    llm_prompt_tokens: int | None = None
    llm_completion_tokens: int | None = None
    llm_total_tokens: int | None = None
    llm_ledger_path: str | None = None
    llm_ledger_sha256: str | None = None

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

    @model_validator(mode="after")
    def _reconcile_llm_accounting(self) -> "RunManifestV2":
        if self.llm_accounting_status == "UNKNOWN_LEGACY":
            if self.llm_call_count is not None or self.llm_call_ids:
                raise ValueError("UNKNOWN_LEGACY LLM accounting cannot claim exact call totals")
            return self
        if self.llm_call_count is None:
            raise ValueError("EXACT LLM accounting requires llm_call_count")
        if len(set(self.llm_call_ids)) != len(self.llm_call_ids):
            raise ValueError("LLM call IDs must be unique")
        if self.llm_call_count != len(self.llm_call_ids):
            raise ValueError("LLM provider call count must equal the number of call IDs")
        if self.llm_call_count != sum(self.llm_calls_by_job.values()):
            raise ValueError("LLM per-job totals must reconcile with provider call count")
        return self
