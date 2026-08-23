# Integration notes (for whoever integrates this later -- not performed here)

This module is intentionally **not integrated**. Nothing here should be read as a
suggestion that integration is trivial or already validated end-to-end -- only that the
module itself is a correct, tested, standalone piece.

## What integration would concretely involve

1. **Diagnostic code mapping.** Real callers (`facts/deterministic_truth_salvage.py`,
   `facts/local_verification.py`, `facts/acquisition.py`, and friends) produce their own
   outcome/failure vocabularies (`AcquisitionOutcome`, `LocalProductVerificationV1.outcome`,
   the `product_source_failure` return-code check, etc.). None of these are wired to
   `_DIAGNOSTIC_CODE_TO_BLOCK_CLASS` here. A translation layer -- either extending that
   table or mapping at the call site -- is integration-time work.

2. **Evidence catalog construction.** Nothing in this module builds an
   `AvailableFactEvidenceCatalogV1` from real repository state. A real integration needs
   a function that, given a repository's current source tree, manifest, package
   registry response, and any imported-knowledge bundle, produces the right
   `AvailableFactEvidenceV1` items with correctly-populated `evidence_kind`,
   `competent_claim_kinds`, and identity-binding fields.

3. **Dependency fingerprint construction.** Similarly, nothing here computes a real
   `ExternalDependencyFingerprintV1` from live state. `facts/acceptance_contract.py`
   (`FactAcceptanceContractV1.canonical_hash()`/`.component_hashes`) and
   `facts/verification_contract.py` already compute several of the underlying hashes
   this module's fields are modeled after -- a real integration likely sources several
   `ExternalDependencyFingerprintV1` fields from those existing functions rather than
   inventing new hashing logic.

4. **Call-site wiring.** No existing file calls `resolve_external_fact_block` or
   `classify_external_fact_block_class`. The most natural call site, based on this
   investigation, is inside or alongside
   `facts/deterministic_truth_salvage.py::_finding()` /
   `_dependent_product_source_block_category()`, which currently does its own narrow,
   inline `infra_external` classification for example/acquisition failures specifically
   -- this module could either replace that narrow logic or run alongside it, but that
   decision belongs to the integrator, not this handoff.

5. **Persistence, if wanted.** This module is pure and stateless -- it does not persist
   its output anywhere. If a caller wants "don't re-derive an unchanged resolution"
   behavior across process runs (as `supervisor/blocked_decision_cache.py` does for
   triage verdicts), that would be a thin persistence wrapper around
   `resolve_external_fact_block`'s already-fresh-every-call output, not a change to this
   module itself.

## What was explicitly NOT done

No fact-readiness, gating, supervisor, capability-dispatcher, or CLI file was modified.
No registry entry was added anywhere. No blocked-decision cache was touched. No retry
was executed against any real repository. No mission graph or plan file was modified. No
merge, rebase, or cherry-pick was performed. No pull request was opened.
