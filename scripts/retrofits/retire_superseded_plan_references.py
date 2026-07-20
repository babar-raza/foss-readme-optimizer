"""One-shot retrofit (run from anywhere): retire the superseded scratch-plan pointer and the
abolished TC-/MS- taskcard tags across investigation artifacts. New authority = governed trio
(master.md + requirements.md + GOVERNANCE.md).

Kept after use as the executable record of this transformation — see plans/GOVERNANCE.md,
"Repository layout", placement rule 5. Rescued from a session scratchpad where it was
originally authored (as retrofit_headers.py) and would otherwise have been lost.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH_FULL = r"C:\Users\prora\.claude\plans\production-investigation-and-swift-goose.md"
GOVERNED = "plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)"

targets = list((ROOT / "plans" / "investigations").rglob("*"))
targets += [ROOT / "docs" / "repository-presentation-surface-model.md"]

# drop a line if, ignoring leading comment/quote/blockquote/space, it is a taskcard tag
TASKCARD_LINE = re.compile(r'^\s*[#>"\s-]*"?taskcard"?\s*[:=].*(TC-|MS-|REV)', re.IGNORECASE)

changed = []
for p in targets:
    if not p.is_file() or p.suffix not in {".py", ".md", ".yaml", ".yml", ".json", ".csv"}:
        continue
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        continue
    orig = text
    text = text.replace(SCRATCH_FULL, GOVERNED)
    text = text.replace("production-investigation-and-swift-goose.md", GOVERNED)
    text = text.replace("authoritative_plan", "governed_by")
    # drop taskcard tag lines (they reference abolished TC-/MS- IDs)
    kept = [ln for ln in text.splitlines() if not TASKCARD_LINE.match(ln)]
    text = "\n".join(kept) + ("\n" if text.endswith("\n") else "")
    if text != orig:
        p.write_text(text, encoding="utf-8")
        changed.append(str(p.relative_to(ROOT)))

print(f"retrofitted {len(changed)} files:")
for c in changed:
    print(" ", c)
