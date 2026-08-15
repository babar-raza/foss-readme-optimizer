# Adapted from aspose.org: reports/repo-presenter/_scratch/extract_units_mt030p2.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

import sys, json
sys.path.insert(0, "scripts/pipeline/commands/foss")
import readme_refresh_checks as checks

products = [
    ("slides", "cpp"),
    ("slides", "net"),
    ("slides", "python"),
    ("tex", "python"),
    ("words", "python"),
]

for fam, plat in products:
    path = f"runs/.clone_cache/aspose_{fam}_{plat}/README.md"
    text = open(path, encoding="utf-8", errors="ignore").read()
    units = checks.extract_old_readme_content_units(text)
    outpath = f"reports/repo-presenter/_scratch/units_{fam}_{plat}.json"
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(units, f, indent=2, ensure_ascii=False)
    print(f"{fam}/{plat}: {len(units)} units -> {outpath}")
