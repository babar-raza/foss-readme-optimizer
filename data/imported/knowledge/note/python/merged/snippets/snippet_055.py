# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_055.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_textrun_does_not_expose_run_boundaries(self) -> None:

        from aspose.note import TextRun



        run = TextRun(Text="segment")



        self.assertFalse(hasattr(run, "Start"))

        self.assertFalse(hasattr(run, "End"))