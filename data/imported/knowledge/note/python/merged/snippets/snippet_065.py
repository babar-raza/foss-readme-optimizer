# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_065.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_save_pdf_infers_format_from_path_extension(self) -> None:

        from aspose.note import Document



        doc = Document(self.path)

        output = Path("tests/out/pdf_export/inferred_extension_save.pdf")

        output.parent.mkdir(parents=True, exist_ok=True)

        self.addCleanup(output.unlink, missing_ok=True)



        doc.Save(output)



        self.assertTrue(output.read_bytes().startswith(b"%PDF"))