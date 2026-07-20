"""One-shot retrofit (run from anywhere): normalize references to the superseded scratch plan's
tranche/taskcard/proof-number scheme into governed, self-explanatory vocabulary.

Kept after use as the executable record of this transformation — see plans/GOVERNANCE.md,
"Repository layout", placement rule 5. Rescued from a session scratchpad where it was
originally authored (as normalize_refs.py) and would otherwise have been lost.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
files = [
    p
    for p in (ROOT / "plans" / "investigations").rglob("*")
    if p.is_file() and p.suffix in {".py", ".md", ".yaml", ".yml", ".csv"}
]
files.append(ROOT / "docs" / "repository-presentation-surface-model.md")

# Ordered exact replacements (longest / most-specific first).
EXACT = [
    ("healing spec HEAL-001", "the healing directive"),
    ("HEAL-001", "the healing directive"),
    ("HEAL-002", "the healing directive"),
    ("Part I.1", "the current-state reconstruction"),
    ("Part I.2", "the subsystem verdicts"),
    ("Part I.3", "the control-class model"),
    ("Part I.4", "the cross-cutting architecture"),
    ("Part I.5", "the coordination requirements"),
    ("Part I.6", "the reuse analysis"),
    ("Part-I", "the current-state"),
    ("Part I", "the analysis"),
    ("T5 roadmap", "the roadmap"),
    ("T5 wave", "the roadmap wave"),
    ("T6-01", "the governed deltas"),
    ("T6-02", "the traceability report"),
    ("T4-01", "the framework selection"),
    ("T4-02", "the reconciliation/apply design"),
    ("T4-03", "the consolidated architecture"),
    ("T3-01", "the schema freeze"),
    ("T3-02", "the surface/drift docs"),
    ("T2-01", "the repository-file proof"),
    ("T2-06", "the shared-evidence proof"),
    ("T1-02", "the settings current-state"),
    ("T1-03", "the release/audit current-state"),
    ("T1-04", "the reuse/LLM analysis"),
    ("T1-01", "the README current-state"),
    ("T0-02", "the control-class inventory"),
    ("T0-01", "the coverage matrix"),
    ("Tranche 0", "requirements reconciliation"),
    ("Tranche 1", "current-state reconstruction"),
    ("Tranche 2", "the control-class proofs"),
    ("Tranche 3", "the schema step"),
    ("Proof 1", "the repository-file proof"),
    ("Proof 2", "the settings proof"),
    ("Proof 3", "the social-preview proof"),
    ("Proof 4", "the handoff proof"),
    ("Proof 5", "the generated-surface audit"),
    ("proof 1", "the repository-file proof"),
    ("proof 2", "the settings proof"),
    ("proof 3", "the social-preview proof"),
    ("proof 4", "the handoff proof"),
    ("proof 5", "the generated-surface audit"),
    ("single-plan authority, ", ""),
    (
        "the authoritative plan operates under it and the traceability report enforces it",
        "the governed docs operate under it",
    ),
    ("the authoritative plan's tranche/proof/roadmap design", "the governed roadmap"),
    (
        "authored from the completed the current-state investigation",
        "authored from the completed current-state investigation",
    ),
]

changed = []
for p in files:
    text = p.read_text(encoding="utf-8")
    orig = text
    # remove taskcard IDs like TC-T2-01, TC-T1-04-03, TC-REV-01, and bracket wrappers
    text = re.sub(r"\s*\[TC-[A-Z0-9-]+\]", "", text)
    text = re.sub(r"\bTC-[A-Z0-9-]+\b", "", text)
    for a, b in EXACT:
        text = text.replace(a, b)
    # tidy artifacts of removal
    text = re.sub(r"\(\s*;\s*", "(", text)
    text = re.sub(r"\s+\)", ")", text).replace("( ", "(")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +\n", "\n", text)
    if text != orig:
        p.write_text(text, encoding="utf-8")
        changed.append(p.relative_to(ROOT).as_posix())

print(f"normalized {len(changed)} files")
for c in changed:
    print(" ", c)
