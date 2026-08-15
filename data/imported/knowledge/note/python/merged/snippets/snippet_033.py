# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_033.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_note_tag_creation_time_uses_datetime_values(self) -> None:

        from aspose.note import NoteTag, TagStatus



        created_time = datetime(2024, 5, 6, 7, 8, tzinfo=timezone.utc)

        tag = NoteTag.CreateYellowStar("Created")

        tag.CreationTime = created_time



        self.assertEqual(tag.CreationTime, created_time)

        self.assertEqual(tag.Status, TagStatus.Open)



        updated_time = datetime(2024, 5, 7, 8, 9, tzinfo=timezone.utc)

        tag.CreationTime = updated_time



        self.assertEqual(tag.CreationTime, updated_time)