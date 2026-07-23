"""`EVID-001` (Wave 13.1): `RunManifestV2` -- a typed, unified evidence
manifest. Fields not yet populated by any built mechanism default `None`/
empty, matching this project's own established "Field-population policy"
convention (`capabilities/schema.py`)."""

from readme_agent.evidence.manifest_v2 import RunManifestV2
from readme_agent.state.schema import SurfaceFreshnessContractV1


class TestRunManifestV2Defaults:
    def test_minimal_construction_defaults_unpopulated_fields_safely(self):
        manifest = RunManifestV2(
            run_id="run1", org_repo="acme/widget", status="CONVERGED_NO_CHANGE", timestamp="t"
        )
        assert manifest.control_plane_fingerprint is None
        assert manifest.upstream_revision is None
        assert manifest.domain_coverage_complete is None
        assert manifest.surface_freshness == {}
        assert manifest.facts_hash is None
        assert manifest.llm_call_count == 0
        assert manifest.llm_calls == []
        # Wave 13.2/13.3/9.5 fields -- not yet populated by anything, must
        # stay explicit None, never faked.
        assert manifest.authorization_record_id is None
        assert manifest.trigger_dedup_key is None

    def test_surface_freshness_accepts_real_contracts(self):
        contract = SurfaceFreshnessContractV1(
            surface_id="metadata_presentation", authoritative_source="github_api", ttl_seconds=3600
        )
        manifest = RunManifestV2(
            run_id="run1",
            org_repo="acme/widget",
            status="CONVERGED_NO_CHANGE",
            timestamp="t",
            surface_freshness={"metadata_presentation": contract},
        )
        assert manifest.surface_freshness["metadata_presentation"].ttl_seconds == 3600
