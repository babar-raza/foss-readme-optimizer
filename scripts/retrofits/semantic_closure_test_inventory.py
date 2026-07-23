"""Map semantic-closure requirements to focused pytest selectors."""

TEST_GROUPS: dict[str, tuple[str, ...]] = {
    "tests/unit/test_effect_ledger.py::TestDispatchGatedEffectAuthorization": ("GOV-026",),
    "tests/unit/test_capabilities.py::TestAuditPackageReleaseSurfacesCapability": ("OWN-004",),
    "tests/unit/test_capabilities.py::TestAuditGithubGeneratedSurfacesCapability": ("OWN-012",),
    "tests/unit/test_validation_rules.py::TestProductFirstOpening": ("RDM-002",),
    "tests/unit/test_validation_rules.py::TestCommercialMentionDiscipline": ("RDM-010", "VAL-006"),
    "tests/unit/test_readme_renderer.py::TestFullGapRendersOneSpanWithEveryElement": (
        "RDM-013",
        "CORE-009",
    ),
    "tests/unit/test_presentation_report.py::TestDetectPresentation": ("RDM-014",),
    "tests/unit/test_cli.py::test_version_exits_zero": ("CORE-002", "CORE-026"),
    "tests/unit/test_orchestrator.py::TestAllowList": ("CORE-003", "SAFE-003"),
    "tests/unit/test_supervisor_loop.py::TestWriteCapableModeGate": ("CORE-004", "CORE-033"),
    "tests/unit/test_capabilities.py::TestProfileRepositoryCapability": ("CORE-004", "CORE-033"),
    (
        "tests/unit/test_registry_loader.py::"
        "test_real_products_json_loads_and_has_at_least_the_known_entries"
    ): ("CORE-005",),
    "tests/unit/test_license_auditor.py::TestDetectLicense": ("CORE-007",),
    "tests/unit/test_gap_detector.py::test_gap_report_matches_audit_table": ("CORE-008",),
    "tests/unit/test_readme_facts.py::TestComputeFactsHash": ("CORE-011", "NFR-001"),
    "tests/unit/test_gitsafety.py::TestCloneBaselineAndWork": ("CORE-012", "CORE-031"),
    (
        "tests/unit/test_generation_schema_version.py::"
        "test_owned_span_contract_files_changed_only_with_a_version_bump"
    ): ("CORE-014",),
    "tests/unit/test_orchestrator.py::TestStaleNoncompliantAndForceRegenerate": (
        "CORE-016",
        "CORE-017",
    ),
    "tests/unit/test_readme_renderer.py::TestRendererNeverInventsUrls": ("CORE-018", "LLM-001"),
    "tests/unit/test_readme_facts.py::TestSha256Text": ("CORE-019",),
    "tests/unit/test_cli.py::TestSuperviseCommand": ("CORE-027", "AGT-001"),
    "tests/unit/test_preflight.py::TestGithubCheck": ("CORE-028",),
    "tests/unit/test_preflight.py::TestLlmCheck": ("CORE-028", "LLM-008"),
    "tests/unit/test_ecosystems.py::TestJavaParser": ("CORE-029",),
    "tests/unit/test_readme_markers.py::TestFindAndReplace": ("CORE-030",),
    "tests/unit/test_readme_markers.py::TestRemoveSpan": ("CORE-030",),
    "tests/unit/test_registry_discovery.py::test_merge_new_entry_defaults_to_disabled": (
        "CORE-032",
    ),
    "tests/unit/test_registry_discovery.py::test_merge_preserves_owned_fields_on_existing_entry": (
        "CORE-032",
    ),
    (
        "tests/unit/test_inspection.py::TestFileInventoryManifests::"
        "test_bound_is_reached_deterministically_regardless_of_os_walk_order"
    ): ("DEP-004",),
    "tests/unit/test_capabilities.py::TestRegistryEff001RegistrationGate": ("EFF-001",),
    "tests/unit/test_effect_ledger.py::TestDispatchGatedEffectReconciliationCheck": ("EFF-001",),
    "tests/unit/test_effect_identity.py::TestBuildEffectIdentity": ("EFF-006",),
    "tests/unit/test_effect_ledger.py::TestDispatchGatedEffectCandidateAwareness": ("EFF-006",),
    "tests/unit/test_supervisor_loop.py::TestRunManifestV2Evidence": ("EVID-002",),
    "tests/unit/test_freshness_contract.py": ("FRESH-001",),
    "tests/unit/test_convergence.py::TestFinalStatus": ("GAP-002", "AGT-004"),
    "tests/unit/test_orchestrator.py::TestFullyCompliantRepo": ("LLM-001", "LLM-002"),
    "tests/unit/test_orchestrator.py::TestBlankSlateRepo": ("LLM-002", "NFR-002"),
    "tests/unit/test_llm_client.py::TestFixtureClient": ("LLM-003",),
    "tests/unit/test_validation_rules.py::TestReferentialIntegrity": ("LLM-004", "VAL-002"),
    "tests/unit/test_llm_client.py::TestLiveClientRetry": ("LLM-007",),
    "tests/security/test_no_secrets_in_evidence.py": ("LLM-013", "SAFE-007"),
    "tests/unit/test_llm_client.py::TestLiveClientHappyPath": ("LLM-014",),
    "tests/unit/test_state_backend.py::TestFakeStateBackendCAS": ("MEM-003",),
    "tests/unit/test_validate_plan_structure.py::TestRealRepoIsClean": ("NFR-004",),
    (
        "tests/unit/test_registry_discovery.py::"
        "test_real_families_json_has_26_entries_with_matching_org_convention"
    ): ("OPS-007",),
    (
        "tests/unit/test_registry_discovery.py::"
        "test_real_families_json_covers_every_org_referenced_by_products_json"
    ): ("OPS-007",),
    "tests/unit/test_task_graph.py::TestCycleRejection": ("ORC-001",),
    "tests/unit/test_verify_package_acquisition.py::TestExecuteMultiRoot": ("PKG-005",),
    "tests/unit/test_open_presentation_pr.py::TestExecuteOrchestration": ("PRL-004",),
    "tests/unit/test_effect_ledger.py::TestDispatchGatedEffectLockRevalidation": ("PRL-008",),
    "tests/unit/test_supervisor_loop.py::TestSpecialistResultsEvidence": ("AGT-003",),
    "tests/unit/test_supervisor_loop.py::TestMaxTurns": ("AGT-004",),
    "tests/unit/test_validation_rules.py::TestRegistryAggregation": ("VAL-001",),
    "tests/unit/test_validation_rules.py::TestChangeBoundary": ("VAL-003",),
    "tests/unit/test_validation_rules.py::TestWordCount": ("VAL-004",),
    "tests/unit/test_validation_rules.py::TestProhibitedTerms": ("VAL-004",),
    "tests/unit/test_validation_rules.py::TestLinkWhitelist": ("VAL-004",),
    "tests/unit/test_validation_rules.py::TestTalkingPoints": ("VAL-004",),
    "tests/unit/test_evidence_writer.py::TestWriteEvidence": ("SAFE-009",),
    "tests/unit/test_evidence_writer.py::TestWriteRunManifestV2": ("SAFE-008", "SAFE-009"),
    "tests/unit/test_gitsafety.py::TestNeuterAndVerify": ("SAFE-001", "SAFE-002"),
    "tests/unit/test_gitsafety.py::TestHookActuallyBlocksARealPush": ("SAFE-001",),
}
