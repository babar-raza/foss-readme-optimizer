# Adapted from aspose.org: reports/repo-presenter/_scratch/insert_pdf_net_table.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

from pathlib import Path

REPO = Path(r"d:/onedrive/Documents/GitHub/aspose.org")
README = REPO / "reports" / "repo-presenter" / "pdf" / "net" / "readme.md"
SP = Path("C:/Users/prora/AppData/Local/Temp/claude/d--onedrive-Documents-GitHub-aspose-org/d0a4bedb-b896-46f0-a8d1-513863007d0b/scratchpad")

readme_text = README.read_text(encoding="utf-8")
fixed_table = (SP / "pdf_net_table_fixed.md").read_text(encoding="utf-8").rstrip("\n")

marker = "<summary>View Selected API Surface</summary>\n"
idx = readme_text.index(marker)
insert_at = idx + len(marker)

before = readme_text[:insert_at]
after = readme_text[insert_at:]

# after currently starts with "\n| Area | Key classes |\n..." up to "\n</details>"
# We want: blank line, fixed_table, blank line, ---, blank line, #### Detailed Member Reference,
# then the existing "after" content (which already starts with a blank line before the Area table).

insertion = "\n" + fixed_table + "\n\n---\n\n#### Detailed Member Reference\n"

new_text = before + insertion + after

README.write_text(new_text, encoding="utf-8")
print("inserted. new length:", len(new_text.splitlines()))
