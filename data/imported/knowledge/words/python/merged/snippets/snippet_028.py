# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_028.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

import aspose.words_foss as aw

doc = aw.Document("input.docx")  # or .doc, .rtf, .txt, .md
doc.save("output.md", aw.SaveFormat.MARKDOWN)
