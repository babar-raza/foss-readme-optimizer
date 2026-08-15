"""One-time mechanical fix for note/python's content-dispositions.json: the MT031 extractor
fix (25-char noise floor -> 4+-letter-word test) recovers 45 real units INSERTED THROUGHOUT
the old README (not just appended at the end, unlike every other MT030 Phase 2 product), which
shifts the live extractor's positional unit_id assignment for every unit that comes after each
insertion point. Verified computationally: (live 147 units) minus (the 45 given "missing" ids)
== the existing 102 entries' excerpts, in the same order, with zero mismatches. So the 102
pre-existing entries' unit_id fields are stale bookkeeping labels (docstring: "not a content
hash") from the old (pre-fix) extraction run -- their classification/disposition/verification
work is untouched here, only the unit_id label is corrected to the live extractor's current
positional id for that same excerpt, which check_content_unit_disposition_coverage requires
for a clean pass.
"""

# Adapted from aspose.org: reports/repo-presenter/_scratch/renumber_note_python_dispositions.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(r"D:\onedrive\Documents\GitHub\aspose.org\scripts\pipeline\commands\foss")))
import readme_refresh_checks as checks

TARGET = Path(r"D:\onedrive\Documents\GitHub\aspose.org\reports\repo-presenter\note\python\content-dispositions.json")
OLD_README = Path(r"D:\onedrive\Documents\GitHub\aspose.org\runs\.clone_cache\aspose_note_python\README.md")

MISSING_IDS = {
    "u0007","u0015","u0016","u0017","u0037","u0038","u0042","u0043","u0045","u0051",
    "u0052","u0053","u0055","u0057","u0061","u0065","u0067","u0068","u0071","u0073",
    "u0076","u0077","u0078","u0079","u0080","u0082","u0087","u0088","u0090","u0095",
    "u0097","u0099","u0100","u0103","u0104","u0105","u0106","u0108","u0111","u0116",
    "u0118","u0126","u0140","u0143","u0146",
}
assert len(MISSING_IDS) == 45

old_readme_text = OLD_README.read_text(encoding="utf-8", errors="ignore")
live_units = checks.extract_old_readme_content_units(old_readme_text)
assert len(live_units) == 147, f"expected 147 live units, got {len(live_units)}"

remaining = [u for u in live_units if u["unit_id"] not in MISSING_IDS]
assert len(remaining) == 102, f"expected 102 remaining (non-missing) live units, got {len(remaining)}"

data = json.loads(TARGET.read_text(encoding="utf-8"))
assert len(data) == 147, f"expected 147 entries in current file (102 old + 45 already-appended), got {len(data)}"

old102 = data[:102]
new45 = data[102:]
assert len(new45) == 45
assert {e["unit_id"] for e in new45} == MISSING_IDS

# Verify positional excerpt alignment before mutating anything.
for i, (old_e, new_u) in enumerate(zip(old102, remaining)):
    assert old_e["excerpt"] == new_u["excerpt"], f"mismatch at position {i}: {old_e['excerpt']!r} vs {new_u['excerpt']!r}"

renumber_map = {}
for old_e, new_u in zip(old102, remaining):
    renumber_map[old_e["unit_id"]] = new_u["unit_id"]

renumbered_102 = []
for old_e, new_u in zip(old102, remaining):
    fixed = dict(old_e)  # shallow copy; nested verification dict is not mutated, just reassigned as-is
    fixed["unit_id"] = new_u["unit_id"]
    renumbered_102.append(fixed)

# Sanity: no duplicate ids introduced, full 147-id coverage achieved.
all_ids = [e["unit_id"] for e in renumbered_102] + [e["unit_id"] for e in new45]
assert len(all_ids) == 147
assert len(set(all_ids)) == 147, "duplicate unit_id after renumbering!"
live_id_set = {u["unit_id"] for u in live_units}
assert set(all_ids) == live_id_set, "renumbered id set does not match live extraction id set!"

combined = renumbered_102 + new45
TARGET.write_text(json.dumps(combined, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

print(f"Renumbered {len(renumbered_102)} pre-existing entries (content/classification/verification untouched).")
print(f"Kept {len(new45)} newly-appended entries as-is.")
print(f"Total: {len(combined)} entries, {len(set(all_ids))} unique ids, matches live extraction: {set(all_ids) == live_id_set}")
print()
print("Sample id remaps (old -> new):")
for i, (old_e, new_u) in enumerate(zip(old102, remaining)):
    if old_e["unit_id"] != new_u["unit_id"]:
        print(f"  {old_e['unit_id']} -> {new_u['unit_id']}  ({old_e['excerpt'][:50]!r})")
        if i > 20:
            break
