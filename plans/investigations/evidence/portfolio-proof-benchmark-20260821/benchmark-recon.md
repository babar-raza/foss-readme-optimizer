# Aspose.org Evolving Benchmark Recon

## Purpose

This is a development-input observation, not candidate acceptance and not factual product evidence.
It records why Repo Presenter must refresh and qualify Aspose.org's generated visitor-quality corpus
at execution time instead of pinning its present contents forever.

## Observed Source

- Repository: `D:/onedrive/Documents/GitHub/aspose.org`
- Generated root: `reports/repo-presenter-regen-full`
- Initial audit producer HEAD: `bf9381af81415843a36a8f50cb6415e01f03ad55`
- Later provenance check producer HEAD: `92f213302a15797bc0bce1b8f34e45f11db02acc`
- Ignore rule: `.gitignore:18` excludes `reports/`; `git check-ignore -v` confirms the target
  README is generated and absent from both inspected Git trees.
- Working repository condition at the later check: dirty. This is recorded, not imported as
  committed source mechanism.

The changing producer HEAD does not identify generated output bytes. A valid campaign snapshot must
therefore bind committed producer source separately from a twice-stable checksum inventory of the
generated tree.

## Commands And Results

The initial full aggregate audit was run with:

```powershell
D:/onedrive/Documents/GitHub/aspose.org/.venv/Scripts/python.exe `
  D:/onedrive/Documents/GitHub/aspose.org/scripts/pipeline/commands/foss/readme_refresh_run.py `
  audit-portfolio --candidate-tree repo-presenter-regen-full --json
```

Observed result:

- aggregate denominator: 30;
- clean: 27;
- current hard-gate failures: 3;
- failing candidates: `page/python`, `pdf/cpp`, and `pdf/go`;
- common failing category: `diagram_hybrid_reverification`;
- disposition-verified: 22; five published candidates were skipped by that disposition check.

A direct generated-tree inventory found 31 `readme.md` files. A later PowerShell inventory again
found 31 and found exactly one candidate without both `last-verified.json` and
`code-example-dispositions.json`: `cells/typescript/readme.md`. The aggregate audit therefore omitted
one visible candidate and did not prove a complete synchronized 31-candidate benchmark.

## Disposition

- The corpus remains the target visitor-quality floor after local qualification.
- Its prose and claims are not facts and are never copied as authority.
- Missing receipts, audit omissions, and current failures are diagnostics; they cannot lower local
  acceptance.
- At campaign execution, rerun discovery, stable-double-read, denominator reconciliation, aggregate
  audit, and local qualification. The counts in this report are not frozen expectations.
- If Aspose.org has repaired and synchronized the current failures by then, the new stable snapshot
  supersedes this diagnostic for calibration. If it has not, unaffected qualified dimensions remain
  reusable while failed items remain quarantined.
- Production and acceptance must continue with the sibling repository absent.

## Governing References

- `plans/idea.md`, "Portfolio README Presentation Contract"
- `plans/master.md`, Decision 104 and "Qualified development-oracle refresh"
- `plans/requirements/catalog.jsonl`, `KNOW-014`
- `plans/investigations/control/portfolio-readme-proof-contract.md`, "Refreshable Visitor-Quality
  Benchmark"
- `plans/investigations/control/level8-autonomous-mission-task-graph.yaml`,
  `L8-PF-01-KNOWLEDGE-ACCEPTANCE-IDENTITY`
