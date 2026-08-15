# Adapted from aspose.org: reports/repo-presenter/_scratch/gen_api_table.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

import re
import sys
from pathlib import Path

REPO_ROOT = Path(r"d:/onedrive/Documents/GitHub/aspose.org")
sys.path.insert(0, str(REPO_ROOT / "scripts" / "pipeline" / "commands" / "foss"))
import readme_refresh_checks as checks  # noqa: E402


def real_index_md_text(family: str, platform: str) -> str:
    p = REPO_ROOT / "content" / "reference.aspose.org" / "en" / family / platform / "_index.md"
    return p.read_text(encoding="utf-8")


def gen_table(family: str, platform: str) -> None:
    text = real_index_md_text(family, platform)
    body = checks._strip_frontmatter(text)

    # Re-walk the raw body ourselves (not the flattened parse_reference_api_index) so we can
    # preserve real sub-table boundaries (Interfaces/Structs/Enumerations) for rendering, while
    # still deduping by class name within a module (the real source has at least one duplicate
    # row -- cells/cpp's DiagnosticSeverity appears twice with an identical description).
    modules = {}  # module -> list of (kind, class, desc) in kind="main"|sub-name order preserved
    current_module = None
    current_kind = "main"
    for line in body.splitlines():
        h2 = re.match(r"^##\s+(.+?)\s*$", line)
        if h2:
            current_module = h2.group(1).strip()
            current_kind = "main"
            modules.setdefault(current_module, [])
            continue
        h3 = re.match(r"^###\s+(.+?)\s*$", line)
        if h3 and current_module is not None:
            current_kind = h3.group(1).strip()
            continue
        row = re.match(r"^\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|\s*$", line)
        if row and current_module is not None:
            modules[current_module].append((current_kind, row.group(1), row.group(2)))

    def header_word(kind: str) -> str:
        singular = {"Interfaces": "Interface", "Structs": "Struct", "Enumerations": "Enumeration"}
        return singular.get(kind, "Class")

    out = []
    for module, rows in modules.items():
        if not rows:
            continue  # e.g. "See Also" -- a bullet list, not a class table
        out.append(f"### {module}")
        seen = set()
        by_kind = {}
        order = []
        for kind, cls, desc in rows:
            if cls in seen:
                continue
            seen.add(cls)
            by_kind.setdefault(kind, [])
            if kind not in order:
                order.append(kind)
            by_kind[kind].append((cls, desc))
        for kind in order:
            if kind != "main":
                out.append(f"\n#### {kind}")
            out.append(f"\n| {header_word(kind)} | Description |\n|---|---|")
            for cls, desc in by_kind[kind]:
                flag = ""
                if checks._GENERIC_CLASS_DESCRIPTION_RE.match(desc):
                    flag = " <<<GENERIC"
                elif checks._TRUNCATED_DESCRIPTION_RE.search(desc):
                    flag = " <<<TRUNCATED"
                elif checks._STRIPPED_EXAMPLE_RE.search(desc):
                    flag = " <<<STRIPPED_EXAMPLE"
                out.append(f"| `{cls}` | {desc} |{flag}")
        out.append("")

    sys.stdout.buffer.write(("\n".join(out) + "\n").encode("utf-8"))
    total = sum(len(v) for v in modules.values())
    sys.stderr.buffer.write((f"<!-- {family}/{platform}: {len(modules)} module(s) (incl. empty), "
                              f"{total} raw rows -->\n").encode("utf-8"))


if __name__ == "__main__":
    gen_table(sys.argv[1], sys.argv[2])
