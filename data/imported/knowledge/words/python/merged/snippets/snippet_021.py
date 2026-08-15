# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_021.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_pretty_format_off(self):

        # ExStart:PrettyFormatOff

        save_options = aw.saving.OoxmlSaveOptions()

        save_options.pretty_format = False



        self.convert(

            "test_full_article.docx",

            "OoxmlSaveOptions.compact.docx",

            save_options=save_options,

        )

        # ExEnd:PrettyFormatOff



        output = Path(ARTIFACTS_DIR) / "OoxmlSaveOptions.compact.docx"

        with zipfile.ZipFile(output) as zf:

            doc_xml = zf.read("word/document.xml").decode("utf-8")

        assert len(doc_xml.splitlines()) == 1, "Compact mode: whole part on one line"