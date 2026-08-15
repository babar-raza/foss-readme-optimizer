# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_045.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_attachment_fixture_exports_filename_only(self) -> None:

        from aspose.note import Document

        from aspose.note.saving import PdfSaveOptions



        from tests._pdf_goldens import build_pdf_manifest



        source = fixture_path("AttachedFileWithTag.one")

        if source is None:

            raise unittest.SkipTest("AttachedFileWithTag.one not found")



        ensure_output_dirs()

        generated_pdf = failure_pdf_path("attached_file_with_tag.inline")



        buf = io.BytesIO()

        Document(source).Save(buf, PdfSaveOptions())

        generated_pdf.write_bytes(buf.getvalue())



        manifest = build_pdf_manifest(generated_pdf, fixture_name="AttachedFileWithTag.one")

        text = manifest["pages"][0]["text"]



        self.assertNotIn("[Attachment]", text)

        self.assertIn("TestOneNoteSaveAsTiffByFormat.tiff", text)

        self.assertNotIn("Важно, Дела", text)