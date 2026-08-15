# Adapted from aspose.org: knowledge/email/python/merged/snippets/snippet_004.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_writer_rejects_duplicate_sibling_names_under_cfb_comparison_rules(self) -> None:

        root = CFBStorage(ROOT_ENTRY_NAME)

        root.add_stream(CFBStream("ab", b"left"))

        root.add_stream(CFBStream("AB", b"right"))



        with self.assertRaises(CFBError):

            CFBWriter.to_bytes(CFBDocument(root=root))