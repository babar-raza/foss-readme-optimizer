# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_013.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_preserve_empty_lines(self):

        # ExStart:PreserveEmptyLines

        source = "# Title\n\n\nParagraph after two blank lines.\n"



        load_options = aw.loading.MarkdownLoadOptions()

        load_options.preserve_empty_lines = True



        doc = aw.Document(io.BytesIO(source.encode("utf-8")), load_options)

        # ExEnd:PreserveEmptyLines



        paragraph_texts = [p.get_text().strip() for p in doc.sections[0].body.paragraphs]

        assert paragraph_texts[-4:] == ["Title", "", "", "Paragraph after two blank lines."]