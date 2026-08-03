# Verified Page/PDF Python closeout

This evidence closes `L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES` only. It does not
claim the complete Python POC or full-registry Gate A.

## Accepted candidates

- Aspose.Page FOSS for Python: source `dac5d70e0f91949a780f2e98dfbb12314a5fbc70`,
  candidate `ce4b339678b1d905f4f09ca627cd4ba3b06d4363c96570155cca7bd89955724d`.
- Aspose.PDF FOSS for Python: source `737d26451ed5c58e53017e3c9460e834f99d20ed`,
  candidate `2c62095e3b3aaeb18754e79caf897f2f4fb30a91aaa2b6329106bf31bdac1fd7`.

Both candidates passed repository-verified facts, structured composition, deterministic
validation, non-authoring independent review, checksum reconstruction, push-blocking inspection,
and an unchanged rerun with zero provider calls and zero product effects. The corrected PDF
Mermaid represents all 15 selected verified capabilities.

The exact reviewable README bytes are promoted in
`plans/investigations/evidence/finalized-repository-readmes-v1/` and bound by its
`cohort-manifest.json`.

## Reproduction

From repository root on the recorded commit:

```powershell
$env:README_AGENT_STATE_REMOTE=(Resolve-Path 'runs\control\local-verified-canary-state.git').Path
.venv\Scripts\readme-agent supervise --repo aspose-page-foss/Aspose.Page-FOSS-for-Python --execution-profile local_poc --bounded-verified-canary --no-registry-heal
.venv\Scripts\readme-agent supervise --repo aspose-pdf-foss/Aspose-PDF-FOSS-for-Python --execution-profile local_poc --bounded-verified-canary --no-registry-heal
.venv\Scripts\python scripts\governance\run_full_pytest.py
```

The unchanged canary commands must return `CONVERGED_NO_TRACKED_CHANGE`, zero provider calls,
one cache reuse, and `NO_OP_PROVEN` without a product write.
