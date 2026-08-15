# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_035.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_unsupported_file_format_exception_exposes_read_only_enum(self) -> None:

        from aspose.note import FileFormat, UnsupportedFileFormatException



        error = UnsupportedFileFormatException(file_format="bogus-guid")

        self.assertIs(error.FileFormat, FileFormat.Unknown)



        with self.assertRaises(AttributeError):

            setattr(error, "FileFormat", FileFormat.OneNote2007)