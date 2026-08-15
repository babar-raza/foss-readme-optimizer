# Adapted from aspose.org: knowledge/email/python/merged/snippets/snippet_013.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_email_message_conversion_round_trip(self) -> None:

        email_message = EmailMessage()

        email_message["Subject"] = "Converted"

        email_message["From"] = "Alice <alice@example.com>"

        email_message["To"] = "Bob <bob@example.com>"

        email_message["Message-ID"] = "<id@example.com>"

        email_message.set_content("Plain body")

        email_message.add_alternative("<p>HTML body</p>", subtype="html")

        email_message.add_attachment(b"payload", maintype="application", subtype="octet-stream", filename="a.bin")



        message = MapiMessage.from_email_message(email_message)

        projected = message.to_email_message()



        self.assertEqual(message.subject, "Converted")

        self.assertEqual(len(message.recipients), 1)

        self.assertEqual(len(message.attachments), 1)

        self.assertEqual(projected["Subject"], "Converted")

        self.assertEqual(projected["Message-ID"], "<id@example.com>")

        self.assertTrue(projected.is_multipart())