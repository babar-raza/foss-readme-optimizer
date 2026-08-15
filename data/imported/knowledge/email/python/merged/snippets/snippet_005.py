# Adapted from aspose.org: knowledge/email/python/merged/snippets/snippet_005.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_reader_rejects_invalid_signature_and_byte_order(self) -> None:

        root = CFBStorage(ROOT_ENTRY_NAME)

        root.add_stream(CFBStream("Payload", b"abc"))

        payload = bytearray(CFBWriter.to_bytes(CFBDocument(root=root)))



        bad_signature = bytes(b"\x00" + payload[1:])

        with self.assertRaises(CFBError):

            CFBReader(bad_signature)



        struct.pack_into("<H", payload, 0x1C, 0xFEFF)

        with self.assertRaises(CFBError):

            CFBReader(bytes(payload))