"""MT030 Phase 1 scratch helper: verify a product's content-dispositions.json against its
real old README and candidate readme.md. Also re-runs the full existing gate suite so a Phase 1
pilot agent gets one command confirming nothing else broke.

Usage: .venv/Scripts/python reports/repo-presenter/_scratch/verify_content_units.py {family}/{platform} [...]
"""

# Adapted from aspose.org: reports/repo-presenter/_scratch/verify_content_units.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO_ROOT = Path(r"d:/onedrive/Documents/GitHub/aspose.org")
sys.path.insert(0, str(REPO_ROOT / "scripts" / "pipeline" / "commands" / "foss"))
import readme_refresh_checks as checks  # noqa: E402
import readme_refresh_run as rr  # noqa: E402


def verify(family: str, platform: str) -> bool:
    readme_path = REPO_ROOT / "reports" / "repo-presenter" / family / platform / "readme.md"
    upstream_path = REPO_ROOT / "reports" / "repo-presenter" / family / platform / "upstream-issues.md"
    dispositions_path = REPO_ROOT / "reports" / "repo-presenter" / family / platform / "content-dispositions.json"
    index_path = REPO_ROOT / "content" / "reference.aspose.org" / "en" / family / platform / "_index.md"
    clone_cache = REPO_ROOT / "runs" / ".clone_cache" / f"aspose_{family}_{platform}"
    old_readme_path = clone_cache / "README.md"

    text = readme_path.read_text(encoding="utf-8")
    upstream_text = upstream_path.read_text(encoding="utf-8") if upstream_path.is_file() else ""
    old_readme_text = old_readme_path.read_text(encoding="utf-8", errors="ignore") if old_readme_path.is_file() else ""
    index_text = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    reference_index = checks.parse_reference_api_index(index_text)
    detected_artifacts = rr._detect_dev_test_artifacts(clone_cache)

    content_units = checks.extract_old_readme_content_units(old_readme_text)
    dispositions = json.loads(dispositions_path.read_text(encoding="utf-8")) if dispositions_path.is_file() else []

    ok = True

    def report(name, findings, *, hard_gate, cap=8):
        nonlocal ok
        tag = "hard gate" if hard_gate else "heuristic"
        shown = findings if cap is None else findings[:cap]
        print(f"  {name}: {len(findings)} finding(s) ({tag})")
        for f in shown:
            print(f"    - {f}")
        if len(findings) > len(shown):
            print(f"    ... +{len(findings) - len(shown)} more")
        if hard_gate and findings:
            ok = False

    print(f"=== {family}/{platform} ===")
    print(f"  real old-README content units: {len(content_units)}, dispositions on file: {len(dispositions)}")

    # --- MT030 checks (this pilot's focus) ---
    report("content_unit_disposition_coverage",
           checks.check_content_unit_disposition_coverage(content_units, dispositions), hard_gate=True)
    package_registry = rr._load_package_registry()
    docs_texts = rr._load_content_docs_texts(family, platform)
    report("content_unit_evidence_resolves",
           checks.check_content_unit_evidence_resolves(dispositions, str(clone_cache), package_registry, docs_texts),
           hard_gate=True)
    report("content_unit_merged_into_target_section",
           checks.check_content_unit_merged_into_target_section(text, dispositions), hard_gate=True)
    report("content_unit_no_exact_duplicate_merge",
           checks.check_content_unit_no_exact_duplicate_merge(dispositions), hard_gate=True)
    report("content_unit_classification_plausibility",
           checks.check_content_unit_classification_plausibility(content_units, dispositions), hard_gate=False)
    report("content_unit_probable_duplicate",
           checks.check_content_unit_probable_duplicate(dispositions), hard_gate=False)

    # --- Full pre-existing gate suite (regression guard) ---
    report("dropped_content (links/headings)",
           (lambda d: d["dropped_links"] + d["dropped_headings"] + d["internal_labels"])(
               checks.check_dropped_content(old_readme_text, text, str(clone_cache))
           ), hard_gate=True)
    report("required_sections", checks.check_required_sections(text), hard_gate=True)
    report("heading_title_case", checks.check_heading_title_case(text), hard_gate=True)
    report("scope_limitations_format", checks.check_scope_limitations_format(text), hard_gate=True)
    report("dev_test_artifacts_linked",
           checks.check_dev_test_artifacts_linked(text, detected_artifacts), hard_gate=True)
    report("no_upstream_issue_leaked",
           checks.check_no_upstream_issue_leaked_into_readme(text, upstream_text), hard_gate=True)
    report("no_undisclosed_blocking_commands",
           checks.check_no_undisclosed_blocking_commands(text, upstream_text), hard_gate=True)
    report("api_reference_table_completeness",
           checks.check_api_reference_table_completeness(text, reference_index), hard_gate=True)
    report("no_leaked_docstring_artifacts", checks.check_no_leaked_docstring_artifacts(text), hard_gate=False)
    report("key_capabilities_quality", checks.check_key_capabilities_quality(text), hard_gate=False)
    report("capability_scope_contradiction", checks.check_capability_scope_contradiction(text), hard_gate=False)
    report("development_testing_collapse", checks.check_development_testing_collapse(text), hard_gate=False)
    report("process_narration_smells", checks.check_process_narration_smells(text), hard_gate=False)
    report("enterprise_edition_naming", checks.check_enterprise_edition_naming(text), hard_gate=False)

    print(f"  RESULT: {'CLEAN (hard gates)' if ok else 'HARD-GATE FINDINGS PRESENT (see above)'}")
    print()
    return ok


if __name__ == "__main__":
    products = sys.argv[1:] or []
    all_ok = True
    for p in products:
        fam, plat = p.split("/", 1)
        all_ok = verify(fam, plat) and all_ok
    sys.exit(0 if all_ok else 1)
