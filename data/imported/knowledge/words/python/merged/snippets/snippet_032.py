# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_032.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

import io
import aspose.words_foss as aw

with io.FileIO("input.docx") as stream:
    doc = aw.Document(stream)              # DOCX / DOC / RTF from magic bytes

opts = aw.LoadOptions()
opts.load_format = aw.LoadFormat.MARKDOWN  # needed for .md, which has no magic bytes
with io.FileIO("input.md") as stream:
    doc = aw.Document(stream, opts)
