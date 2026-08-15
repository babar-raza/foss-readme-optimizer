# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_015.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_image_documents_to_all_formats(self):

        for filename in IMAGE_FILES:

            stem = Path(filename).stem

            self.convert_to_all_formats(filename, f"Images.{stem}")