# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)
# artifact_role: analysis_or_evidence_only
"""Overwrite laboratory. Per scenario, in an isolated scratch workspace:
  1. build a synthetic non-Aspose product repo (base) — git init + file:// clone URL;
  2. produce the accepted-presentation with the SHIPPED tool (official orchestrator
     entry, fixture LLM);
  3. apply the scenario's current-upstream (product-agent overwrite) to the source repo;
  4. re-run the SHIPPED tool and capture its actual behavior (the current failure);
  5. run the reconciliation prototype (three-way + .state/) and capture recovery + rerun no-op.
Everything is offline/deterministic except one optional live qwen3-next call in the
full-overwrite scenario. Never pushes; the synthetic origin is a local file:// path and
push is neutered anyway.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "plans" / "investigations" / "tools"))

# Transient workspaces (synthetic git repos + clones) live under gitignored .state/
# per the dot-prefix convention — they must NOT bloat the tracked plans/ tree.
SCRATCH = Path(os.environ.get("LAB_SCRATCH", str(REPO_ROOT / ".state" / "overwrite-lab-scratch")))
# Only the small curated report is tracked evidence.
REPORT_DIR = REPO_ROOT / "plans" / "investigations" / "evidence" / "overwrite-lab"
FIXDIR = REPO_ROOT / "tests" / "fixtures" / "overwrite-scenarios"
STATE_ROOT = REPO_ROOT / ".state" / "lab"

ORG, REPO = "acme-foss", "AcmeCells-FOSS-for-Java"
ORG_REPO = f"{ORG}/{REPO}"
PROFILE = "acme-cells-foss"

B0_README = """# AcmeCells FOSS for Java

Open-source Java library for reading and writing spreadsheet files.

## Features

- Read XLSX workbooks
- Write XLSX workbooks
- Formula recalculation

## Installation

Add the dependency (version 1.2.0):

```xml
<dependency>
  <groupId>org.acmesoft</groupId>
  <artifactId>acmecells-foss</artifactId>
  <version>1.2.0</version>
</dependency>
```

## Quick start

```java
Workbook wb = Workbook.load("report.xlsx");
wb.sheet(0).cell("A1").set("hello");
wb.save("out.xlsx");
```

## Known limitations

- No CSV export support

## Documentation

See https://docs.acmesoft.org/cells/v1/

## License

MIT License — see LICENSE.
"""

B0_CONTRIBUTING = """# Contributing to AcmeCells FOSS

- Fork, branch from `main`, open a PR.
- Run `mvn test` before submitting.
- Sign commits with DCO (`git commit -s`).
"""

B0_POM = """<?xml version="1.0"?>
<project><modelVersion>4.0.0</modelVersion>
<groupId>org.acmesoft</groupId><artifactId>acmecells-foss</artifactId>
<version>1.2.0</version><name>AcmeCells FOSS</name>
<licenses><license><name>MIT</name></license></licenses></project>
"""

FACTS_V1 = {
    "product": "AcmeCells FOSS for Java",
    "version": "1.2.0",
    "license": "MIT",
    "owner": "acme-product-agent",
    "capabilities": ["Read XLSX workbooks", "Write XLSX workbooks", "Formula recalculation"],
    "install": {"groupId": "org.acmesoft", "artifactId": "acmecells-foss", "version": "1.2.0"},
}
# current-upstream facts: version bump + CSV export capability now real (limitation removed)
FACTS_V2 = {
    **FACTS_V1,
    "version": "2.0.0",
    "capabilities": FACTS_V1["capabilities"] + ["CSV export"],
    "install": {**FACTS_V1["install"], "version": "2.0.0"},
}

U1_FULL = """# AcmeCells FOSS for Java

Open-source Java library for spreadsheets: XLSX read/write, formulas, and CSV export.

## Features

- Read XLSX workbooks
- Write XLSX workbooks
- Formula recalculation
- CSV export

## Installation

Add the dependency (version 2.0.0):

```xml
<dependency>
  <groupId>org.acmesoft</groupId>
  <artifactId>acmecells-foss</artifactId>
  <version>2.0.0</version>
</dependency>
```

## Quick start

```java
Workbook wb = Workbook.load("report.xlsx");
wb.exportCsv("out.csv");
```

## Documentation

See https://docs.acmesoft.org/cells/v2/

## License

MIT License — see LICENSE.
"""

U1_GENERIC = """# AcmeCells

A Java library.

## Install

Run maven build.

## License

MIT.
"""

U1_REDESIGN = """# AcmeCells FOSS for Java

> Spreadsheets for Java: XLSX read/write and formula recalculation. MIT licensed.

## Contents
- [Install](#install) · [First steps](#first-steps) · [Limits](#limits) · [Docs](#docs)

## Install

```xml
<dependency>
  <groupId>org.acmesoft</groupId>
  <artifactId>acmecells-foss</artifactId>
  <version>1.2.0</version>
</dependency>
```

## First steps

```java
Workbook wb = Workbook.load("report.xlsx");
wb.sheet(0).cell("A1").set("hello");
wb.save("out.xlsx");
```

## Limits

- No CSV export support

## Docs

https://docs.acmesoft.org/cells/v1/ — full reference.

## License

MIT License — see LICENSE.
"""

U1_STALE_CLAIM = B0_README.replace(
    "- Formula recalculation", "- Formula recalculation\n- PDF rendering"
)

FIXTURE_LLM = {
    "relationship_paragraph": (
        "AcmeCells FOSS is the open source edition of the AcmeCells "
        "family and covers everyday spreadsheet automation. Teams that "
        "need advanced pivot, charting, or priority support can move to "
        "the commercial edition, which offers a straightforward upgrade "
        "path from this library."
    ),
    "talking_points_covered": ["open_source_scope", "commercial_upgrade_path"],
    "claims": {
        "license_name": "MIT",
        "commercial_link_url": "https://products.acmesoft.com/cells/java/",
    },
}

POLICY = {
    "schema_version": 2,
    "policy_profile": PROFILE,
    "required_elements": {
        "license_mentioned": {"detected_license": "MIT"},
        "products_org_link": {
            "url": "https://products.acmesoft.org/cells/java/",
            "family_url": "https://products.acmesoft.org/cells/",
            "label": "AcmeCells FOSS for Java",
        },
        "products_com_link": {
            "url": "https://products.acmesoft.com/cells/java/",
            "family_url": "https://products.acmesoft.com/cells",
            "label": "AcmeCells for Java",
            "utm": {
                "utm_source": "github",
                "utm_medium": "readme",
                "utm_campaign": "central-agent-lab",
            },
        },
        "relationship_explained": {
            "min_sentences": 2,
            "talking_points": ["open_source_scope", "commercial_upgrade_path"],
        },
    },
    "secondary_links": [],
    "block": {
        "word_limit": {"min": 20, "max": 120},
        "prohibited_terms": ["guarantee", "100%", "best in the world"],
        "link_whitelist_domains": [
            "products.acmesoft.org",
            "products.acmesoft.com",
            "docs.acmesoft.org",
        ],
    },
}


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "core.autocrlf=false", *args], cwd=repo, capture_output=True, text=True
    )


def build_workspace(scen: str) -> Path:
    ws = SCRATCH / scen / "workspace"
    if ws.exists():
        shutil.rmtree(ws, onerror=lambda f, p, e: (os.chmod(p, 0o777), f(p)))
    src = ws / "source_repo"
    src.mkdir(parents=True)
    (src / "README.md").write_text(B0_README, encoding="utf-8", newline="\n")
    (src / "CONTRIBUTING.md").write_text(B0_CONTRIBUTING, encoding="utf-8", newline="\n")
    (src / "pom.xml").write_text(B0_POM, encoding="utf-8", newline="\n")
    (src / "LICENSE").write_text(
        "MIT License\n\nPermission is hereby granted...\n", encoding="utf-8", newline="\n"
    )
    git(src, "init", "-b", "main")
    git(src, "config", "user.email", "lab@example.invalid")
    git(src, "config", "user.name", "Product Agent (lab)")
    git(src, "add", "-A")
    git(src, "commit", "-m", "base: product agent baseline")

    (ws / "data").mkdir()
    entry = {
        "family": "cells",
        "platform": "java",
        "repo_name": REPO,
        "repo_url": f"https://github.com/{ORG}/{REPO}",
        "clone_url": src.resolve().as_uri(),
        "active": True,
        "discovered_via": "lab",
        "mode": "full",
        "ecosystem": "maven",
        "policy_profile": PROFILE,
    }
    (ws / "data" / "products.json").write_text(json.dumps([entry], indent=2), encoding="utf-8")
    (ws / "config" / "policies").mkdir(parents=True)
    (ws / "config" / "policies" / f"{PROFILE}.yml").write_text(
        yaml.safe_dump(POLICY, sort_keys=False), encoding="utf-8"
    )
    (ws / "fixture_llm.json").write_text(json.dumps(FIXTURE_LLM, indent=2), encoding="utf-8")
    return ws


def run_shipped(ws: Path, mode: str = "full") -> dict:
    """Official programmatic entry (run_repo), sandboxed via cwd + README_AGENT_RUNS_DIR."""
    old_cwd = os.getcwd()
    os.chdir(ws)
    os.environ["README_AGENT_RUNS_DIR"] = str(ws / "runs")
    # fresh import state so registry defaults (cwd-relative) resolve inside the sandbox
    for m in list(sys.modules):
        if m.startswith("readme_agent"):
            del sys.modules[m]
    try:
        from readme_agent import orchestrator

        gen = orchestrator.generate_repo(
            ORG_REPO, llm_mode="fixture", fixture_response_path=ws / "fixture_llm.json"
        )
        work_readme = gen.work_readme_path.read_text(encoding="utf-8")
        if mode == "full" and gen.status == "GENERATED":
            wp = gen.work_readme_path.parent
            git(wp, "add", "-A")
            git(wp, "commit", "-m", f"central: close gaps ({gen.facts_hash[:12]})")
        return {
            "status": gen.status,
            "llm_called": gen.llm_called,
            "facts_hash": gen.facts_hash,
            "failed_validators": [
                r.rule_name
                for r in gen.validation_results
                if not r.passed and r.severity == "ERROR"
            ],
            "gaps": gen.gap_report.gaps,
            "work_readme": work_readme,
        }
    except Exception as e:  # noqa: BLE001 -- capture, don't crash the lab
        return {"status": f"EXCEPTION: {type(e).__name__}: {e}"}
    finally:
        os.chdir(old_cwd)


def apply_current_upstream(ws: Path, scen: str) -> None:
    src = ws / "source_repo"
    if scen == "full-overwrite-new-version":
        (src / "README.md").write_text(U1_FULL, encoding="utf-8", newline="\n")
        (src / "pom.xml").write_text(B0_POM.replace("1.2.0", "2.0.0"), encoding="utf-8")
    elif scen == "partial-overwrite-corrupt-markers":
        work = ws / "runs" / "work" / f"{ORG}__{REPO}"
        accepted = (work / "README.md").read_text(encoding="utf-8")
        broken = accepted.replace(":end -->", " -->", 1)  # corrupt first end marker
        broken = broken.replace("(version 1.2.0)", "(version 2.0.0)")
        (src / "README.md").write_text(broken, encoding="utf-8", newline="\n")
        (src / "pom.xml").write_text(B0_POM.replace("1.2.0", "2.0.0"), encoding="utf-8")
    elif scen == "generic-template-regression":
        (src / "README.md").write_text(U1_GENERIC, encoding="utf-8", newline="\n")
    elif scen == "legitimate-structural-redesign":
        (src / "README.md").write_text(U1_REDESIGN, encoding="utf-8", newline="\n")
    elif scen == "stale-facts-conflict":
        (src / "README.md").write_text(U1_STALE_CLAIM, encoding="utf-8", newline="\n")
    elif scen == "community-file-removed":
        (src / "CONTRIBUTING.md").unlink()
    elif scen == "concurrent-upstream-advance":
        (src / "README.md").write_text(U1_FULL, encoding="utf-8", newline="\n")
        (src / "pom.xml").write_text(B0_POM.replace("1.2.0", "2.0.0"), encoding="utf-8")
    git(src, "add", "-A")
    git(src, "commit", "-m", f"current-upstream: product agent update ({scen})")


def reconciliation_facts(scen: str) -> dict:
    return {
        "full-overwrite-new-version": FACTS_V2,
        "partial-overwrite-corrupt-markers": FACTS_V2,
        "concurrent-upstream-advance": FACTS_V2,
    }.get(scen, FACTS_V1)


# Tokens that exist ONLY in each scenario's current-upstream (never in base/accepted).
# The reconciled candidate MUST contain them — the independent, non-tautological
# preservation proof. A wrong entry fails the vacuity guard loudly at build time.
# "CSV export" is excluded from full-overwrite because base says "No CSV export
# support" — only genuinely upstream-only tokens qualify.
NEW_TOKENS = {
    "full-overwrite-new-version": ["2.0.0", "exportCsv"],
    "partial-overwrite-corrupt-markers": ["(version 2.0.0)"],
    "legitimate-structural-redesign": ["First steps", "## Contents"],
    "concurrent-upstream-advance": ["exportCsv"],
}


def main() -> int:
    from reconciliation_prototype import StateStore, run_reconciliation, sha

    from readme_agent.registry.models import PolicyProfile

    policy = PolicyProfile.model_validate(POLICY)
    scenarios = [
        "full-overwrite-new-version",
        "partial-overwrite-corrupt-markers",
        "generic-template-regression",
        "legitimate-structural-redesign",
        "stale-facts-conflict",
        "community-file-removed",
        "concurrent-upstream-advance",
    ]
    report: dict = {}
    FIXDIR.mkdir(parents=True, exist_ok=True)

    for scen in scenarios:
        print(f"\n=== {scen} ===")
        ws = build_workspace(scen)
        src = ws / "source_repo"

        # accepted-presentation via the SHIPPED tool
        accepted_run = run_shipped(ws)
        accepted_readme = accepted_run.pop("work_readme", "")
        print(
            f"  accepted: {accepted_run['status']} llm={accepted_run.get('llm_called')} "
            f"gaps_closed_from={accepted_run.get('gaps')}"
        )

        # snapshot the three-way inputs with self-explanatory names
        sdir = FIXDIR / scen
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / "upstream-base-README.md").write_text(B0_README, encoding="utf-8")
        (sdir / "accepted-presentation-README.md").write_text(accepted_readme, encoding="utf-8")

        # current-upstream overwrite by the product agent
        apply_current_upstream(ws, scen)
        upstream_readme = (src / "README.md").read_text(encoding="utf-8")
        (sdir / "current-upstream-README.md").write_text(upstream_readme, encoding="utf-8")

        # VACUITY GUARD: prove the preservation-proof tokens are genuinely upstream-only
        # (present in current-upstream, absent from base). Otherwise the candidate token
        # check is meaningless. A bad NEW_TOKENS entry fails the lab loudly, here.
        for tok in NEW_TOKENS.get(scen, []):
            assert tok in upstream_readme, f"{scen}: token {tok!r} not in upstream (vacuity guard)"
            assert tok not in B0_README, f"{scen}: token {tok!r} also in base (not upstream-only)"

        # SHIPPED tool against current-upstream — capture the current failure honestly
        cur = run_shipped(ws, mode="dry_run")
        cur_readme = cur.pop("work_readme", "")
        # "exportCsv" appears ONLY in current-upstream's new example — a true upstream-only token
        cur["work_readme_contains_upstream_capability"] = (
            "exportCsv" in cur_readme
            if scen in ("full-overwrite-new-version", "concurrent-upstream-advance")
            else None
        )
        cur["facts_hash_changed_vs_accepted"] = cur.get("facts_hash") != accepted_run.get(
            "facts_hash"
        )
        print(
            f"  shipped-on-upstream: {cur['status']} failed={cur.get('failed_validators')} "
            f"hash_changed={cur['facts_hash_changed_vs_accepted']} "
            f"sees_new_content={cur['work_readme_contains_upstream_capability']}"
        )

        # RECONCILIATION: seed state from the accepted-presentation acceptance
        # (upstream_base=base, accepted_output=accepted) to model reality.
        state_key = f"{ORG}__{REPO}"
        state_root = STATE_ROOT / scen
        if state_root.exists():
            shutil.rmtree(state_root)
        StateStore(state_root).save(
            state_key,
            {
                "schema": "RepositoryPresentationStateV1-prototype",
                "fingerprint": "seeded-from-accepted-presentation",
                "upstream_commit": "base",
                "upstream_base": B0_README,
                "accepted_output": accepted_readme,
                "accepted_files": {"CONTRIBUTING.md": B0_CONTRIBUTING},
                "facts_hash": sha(json.dumps(FACTS_V1, sort_keys=True)),
                "policy_hash": sha(policy.model_dump_json()),
                "tool_version": "reconciliation-prototype-1",
                "generation_cache": {},
            },
        )

        adv = None
        if scen == "concurrent-upstream-advance":

            def adv(s=src):  # product agent pushes again mid-run
                (s / "NOTICE.md").write_text("late change\n", encoding="utf-8")
                git(s, "add", "-A")
                git(s, "commit", "-m", "second update: concurrent product-agent commit")

        work_root = ws / "reconciliation-work"
        first = run_reconciliation(
            src,
            policy,
            reconciliation_facts(scen),
            state_key,
            state_root,
            work_root,
            ws / "fixture_llm.json",
            live_llm=(scen == "full-overwrite-new-version"),
            head_advancer=adv,
            new_tokens=NEW_TOKENS.get(scen),
        )
        print(
            f"  reconcile#1: {first.status} drift={first.drift} llm={first.llm} "
            f"checks={first.checks}"
        )

        rerun = None
        if first.status in ("PROPOSED", "ACCEPTED_BASELINE"):
            rerun = run_reconciliation(
                src,
                policy,
                reconciliation_facts(scen),
                state_key,
                state_root,
                work_root,
                ws / "fixture_llm.json",
                live_llm=False,
            )
            print(
                f"  reconcile#2 (rerun): {rerun.status} drift={rerun.drift} "
                f"llm_calls={rerun.checks.get('llm_calls_this_run')}"
            )

        report[scen] = {
            "accepted": accepted_run,
            "shipped_on_upstream": cur,
            "reconcile_first_run": {
                "status": first.status,
                "drift": first.drift,
                "llm": first.llm,
                "checks": first.checks,
                "handoff": first.handoff,
                "notes": first.notes,
                "patch": first.patch_path,
            },
            "reconcile_rerun": {"status": rerun.status, "checks": rerun.checks} if rerun else None,
        }
        if first.candidate_path and Path(first.candidate_path).name == "README.md":
            (sdir / "reconciled-candidate-README.md").write_text(
                Path(first.candidate_path).read_text(encoding="utf-8"), encoding="utf-8"
            )
        (sdir / "scenario.md").write_text(
            f"# {scen}\n\nupstream-base -> accepted-presentation (shipped tool, fixture LLM) "
            f"-> current-upstream (product-agent overwrite) -> shipped-tool failure capture "
            f"-> reconciliation recovery.\n\n"
            f"Shipped on current-upstream: `{cur['status']}` "
            f"(failed: {cur.get('failed_validators')})\n"
            f"Reconciled: `{first.status}` drift `{first.drift}`; rerun: "
            f"`{rerun.status if rerun else 'n/a'}`\n",
            encoding="utf-8",
        )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / "lab-report.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
