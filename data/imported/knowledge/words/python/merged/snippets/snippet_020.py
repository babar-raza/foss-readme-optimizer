# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_020.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_set_pretty_format(self):

        # ExStart:SetPrettyFormat

        save_options = aw.saving.OoxmlSaveOptions()

        save_options.pretty_format = True



        self.convert(

            "test_full_article.docx",

            "OoxmlSaveOptions.pretty_format.docx",

            save_options=save_options,

        )

        # ExEnd:SetPrettyFormat



        output = Path(ARTIFACTS_DIR) / "OoxmlSaveOptions.pretty_format.docx"

        with zipfile.ZipFile(output) as zf:

            doc_xml = zf.read("word/document.xml").decode("utf-8")

        assert "\r\n\t" in doc_xml, "XML should be indented"

        assert len(doc_xml.splitlines()) > 1, "Pretty mode: XML should span many lines"