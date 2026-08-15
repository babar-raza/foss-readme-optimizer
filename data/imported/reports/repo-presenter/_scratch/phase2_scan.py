# Adapted from aspose.org: reports/repo-presenter/_scratch/phase2_scan.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

import json
import sys
from pathlib import Path

REPO_ROOT = Path(r"d:/onedrive/Documents/GitHub/aspose.org")
sys.path.insert(0, str(REPO_ROOT / "scripts" / "pipeline" / "commands" / "foss"))
import readme_refresh_run as rr  # noqa: E402

rr.configure()

products = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
excl = json.loads((REPO_ROOT / "data" / "registry_exclusions.json").read_text(encoding="utf-8"))
excl_keys = {(e.get("family"), e.get("platform")) for e in excl} if isinstance(excl, list) else set()
active = sorted(
    (p["family"], p["platform"]) for p in products
    if p.get("active") and (p["family"], p["platform"]) not in excl_keys
)

summary = {}
for family, platform in active:
    readme_path = REPO_ROOT / "reports" / "repo-presenter" / family / platform / "readme.md"
    if not readme_path.is_file():
        summary[f"{family}/{platform}"] = {"error": "no readme.md found"}
        continue
    text = readme_path.read_text(encoding="utf-8")
    clone_cache = rr._product_clone_cache(family, platform)
    try:
        result = rr._run_deterministic_checks(family, platform, text, clone_cache)
    except Exception as exc:  # noqa: BLE001
        summary[f"{family}/{platform}"] = {"error": f"EXCEPTION: {exc!r}"}
        continue
    hard_fails = {k: len(v["findings"]) for k, v in result.items() if v.get("hard_gate") and v.get("findings")}
    summary[f"{family}/{platform}"] = hard_fails or "CLEAN"

clean = [k for k, v in summary.items() if v == "CLEAN"]
dirty = {k: v for k, v in summary.items() if v != "CLEAN"}

print(f"=== {len(clean)}/{len(active)} products ALL HARD GATES CLEAN ===")
for k in clean:
    print(f"  CLEAN: {k}")

print(f"\n=== {len(dirty)}/{len(active)} products with hard-gate findings ===")
for k, v in dirty.items():
    print(f"  {k}: {v}")

# Tally which gates fire most often, across the dirty set
from collections import Counter
gate_tally = Counter()
for v in dirty.values():
    if isinstance(v, dict):
        for gate in v:
            gate_tally[gate] += 1
print("\n=== Gate failure tally (how many products each gate fires on) ===")
for gate, count in gate_tally.most_common():
    print(f"  {gate}: {count}")
