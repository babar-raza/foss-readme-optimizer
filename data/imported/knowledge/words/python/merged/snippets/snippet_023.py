# Adapted from aspose.org: knowledge/words/python/merged/snippets/snippet_023.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_set_compression_level(self):

        # ExStart:SetCompressionLevel

        save_options = aw.saving.OoxmlSaveOptions()

        save_options.compression_level = aw.saving.CompressionLevel.MAXIMUM



        self.convert(

            "test_full_article.docx",

            "OoxmlSaveOptions.max_compression.docx",

            save_options=save_options,

        )

        # ExEnd:SetCompressionLevel
