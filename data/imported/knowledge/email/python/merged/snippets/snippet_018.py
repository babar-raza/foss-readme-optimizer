# Adapted from aspose.org: knowledge/email/python/merged/snippets/snippet_018.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_loaded_messages_do_not_gain_new_defaults_on_save(self) -> None:

        root = MsgStorage(name=ROOT_ENTRY_NAME, role=MESSAGE_ROLE)

        root.add_storage(MsgStorage(name=NAMED_PROPERTY_MAPPING_STORAGE_NAME, role=NAMED_PROPERTY_MAPPING_ROLE))

        root.add_stream(MsgStream(PROPERTY_STREAM_NAME, _top_level_property_stream()))

        source = MapiMessage.from_msg_document(MsgDocument(root=root))

        reread = MapiMessage.from_msg_document(MsgDocument.from_reader(MsgReader(CFBReader(source.to_bytes()))))



        self.assertIsNone(reread.get_property_value(PropertyId.MESSAGE_CLASS))

        self.assertIsNone(reread.get_property_value(PropertyId.SENDER_ADDRESS_TYPE))