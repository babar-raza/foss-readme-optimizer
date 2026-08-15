# Adapted from aspose.org: reports/repo-presenter/_scratch/verify_api_table.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

import sys
from pathlib import Path

REPO_ROOT = Path(r"d:/onedrive/Documents/GitHub/aspose.org")
sys.path.insert(0, str(REPO_ROOT / "scripts" / "pipeline" / "commands" / "foss"))
import readme_refresh_checks as checks  # noqa: E402
import readme_refresh_run as rr  # noqa: E402


def verify(family: str, platform: str) -> bool:
    readme_path = REPO_ROOT / "reports" / "repo-presenter" / family / platform / "readme.md"
    upstream_path = REPO_ROOT / "reports" / "repo-presenter" / family / platform / "upstream-issues.md"
    index_path = REPO_ROOT / "content" / "reference.aspose.org" / "en" / family / platform / "_index.md"
    clone_cache = REPO_ROOT / "runs" / ".clone_cache" / f"aspose_{family}_{platform}"
    text = readme_path.read_text(encoding="utf-8")
    upstream_text = upstream_path.read_text(encoding="utf-8") if upstream_path.is_file() else ""
    index_text = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    reference_index = checks.parse_reference_api_index(index_text)
    detected_artifacts = rr._detect_dev_test_artifacts(clone_cache)

    ok = True

    def report(name, findings, *, hard_gate, cap=None):
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
    real_module_count = len(reference_index)
    real_class_count = sum(len(rows) for rows in reference_index.values())
    print(f"  real modules: {real_module_count}, real classes: {real_class_count}, "
          f"dev/test artifacts detected: {len(detected_artifacts)}")

    report("api_reference_table_completeness",
           checks.check_api_reference_table_completeness(text, reference_index), hard_gate=True)
    report("no_generic_class_description", checks.check_no_generic_class_description(text), hard_gate=False)
    report("no_truncated_class_description", checks.check_no_truncated_class_description(text), hard_gate=False)
    report("no_stripped_example_in_description",
           checks.check_no_stripped_example_in_description(text), hard_gate=False)
    report("no_leaked_docstring_artifacts", checks.check_no_leaked_docstring_artifacts(text), hard_gate=True)
    report("heading_title_case", checks.check_heading_title_case(text), hard_gate=True)
    report("required_sections", checks.check_required_sections(text), hard_gate=True)
    report("no_upstream_issue_leaked",
           checks.check_no_upstream_issue_leaked_into_readme(text, upstream_text), hard_gate=True)
    report("key_capabilities_quality", checks.check_key_capabilities_quality(text), hard_gate=False)
    report("capability_scope_contradiction",
           checks.check_capability_scope_contradiction(text), hard_gate=False)
    report("scope_limitations_format", checks.check_scope_limitations_format(text), hard_gate=True)
    report("dev_test_artifacts_linked",
           checks.check_dev_test_artifacts_linked(text, detected_artifacts), hard_gate=True)
    report("development_testing_collapse",
           checks.check_development_testing_collapse(text), hard_gate=False)

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
