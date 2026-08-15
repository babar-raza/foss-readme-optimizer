# Adapted from aspose.org: knowledge/email/python/merged/snippets/snippet_006.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_branded_namespace_exports_publishable_modules(self) -> None:

        self.assertIs(branded_msg.MapiMessage, MapiMessage)

        self.assertIs(branded_msg.MsgReader, MsgReader)

        self.assertIs(branded_msg.MsgWriter, MsgWriter)

        self.assertIs(branded_msg.PropertyId, PropertyId)

        self.assertIs(branded_cfb.CFBReader, CFBReader)

        self.assertIs(branded_cfb.CFBWriter, CFBWriter)