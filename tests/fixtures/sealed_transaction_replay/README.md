# Sealed transaction replay fixtures

Synthetic, structurally faithful bundle inputs for
`tests/unit/test_sealed_transaction_replay.py`. **Not captured from a live run.**

No real PF-03 pair (a completed transaction plus its immediate no-op replay) exists in this
repository yet: the PF-02 bundle at
`runs/readme-poc/aspose-3d-foss__Aspose.3D-FOSS-for-Python/ee05c1ba9153ef5916b7a108406c794f2e464d01/`
stops at `DETERMINISTIC_VALIDATED`, and the only `NO_OP_PROVEN` example predates `stage_receipts`,
`candidate_stage_dependency_key`, and the LLM call ledger. These three files are the byte-stable
core of a synthetic bundle pair the test suite builds in memory around them.

Attesting a real captured pair remains an integration-time test once `L8-PF-03-SEALED-CANDIDATE-NO-OP`
produces one -- see the module docstring in the test file.
