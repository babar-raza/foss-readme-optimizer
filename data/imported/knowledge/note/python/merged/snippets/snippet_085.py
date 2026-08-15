# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_085.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

from aspose.note import Document

doc = Document("testfiles/SimpleTable.one")
print(doc.DisplayName)
pages = list(doc)
print(len(pages))

# pages are direct children of Document
for page in pages:
    print(page.Title.TitleText.Text)
