# Adapted from aspose.org: knowledge/email/python/merged/snippets/snippet_008.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_property_stream_parsers_reject_misaligned_payloads(self) -> None:

        with self.assertRaises(MsgError):

            MsgReader.parse_top_level_property_stream(b"\x00" * 33)

        with self.assertRaises(MsgError):

            MsgReader.parse_subobject_property_stream_data(b"\x00" * 9)

        with self.assertRaises(MsgError):

            MsgReader.parse_subobject_property_stream_data(b"\x00" * 25)