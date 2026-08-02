# Wave 3 truth-machinery repair evidence

Verdict: `BOUNDED_SLICE_ACCEPTED`.

This evidence proves only `IV-PFR-001`, `IV-PFR-002`, and `IV-PFR-005` at implementation HEAD
`6dcf22052a936cc7ff1763c57500eaf92457de7a`. It does not close Wave 3, produce a current README
candidate, satisfy Gate A, authorize a product effect, or award a maturity level.

At durable state version 679, the live mission projection separated one current/reusable
`FACTS_READY` result from 17 historical raw results. Facts-stage manifests bind the exact Note
source revision and captured `RepositorySnapshotV1`. An independent same-revision replay preserved
all 81 revision-bundle files byte-for-byte and retained their modification times while making zero
provider calls and zero effects.

## Reproduction

```powershell
.venv/Scripts/readme-agent supervise --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml --mission-action status --mission-observer Codex
.venv/Scripts/python -m pytest -q tests/unit/test_local_poc_evidence.py
.venv/Scripts/python scripts/governance/run_full_pytest.py
.venv/Scripts/readme-agent supervise --repo aspose-note-foss/Aspose.Note-FOSS-for-Python --execution-profile local_poc --bounded-verified-canary --max-readme-poc-stage FACTS_READY
```

The structured proof is in `verification.json`; independent authorship and replay are in
`independent-verification.json`. File checksums are in `sha256sums.txt`.
