# Adapted from aspose.org: knowledge/note/python/merged/snippets/snippet_037.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_parser_keeps_default_and_history_roots_separate(self) -> None:

        from aspose.note._internal.onestore.parser import parse_onestore_file



        parsed = parse_onestore_file(self.path)

        content_space = parsed.object_spaces[1]



        default_root = content_space.get_latest_root(1)

        self.assertIsNotNone(default_root)

        if default_root is None:

            raise AssertionError("expected default root")

        self.assertEqual(content_space.objects[default_root].jcid_name, "PageManifestNode")



        context_root_kinds = {

            revision.objects[revision.root_roles[1]].jcid_name

            for revision in content_space.revisions

            if revision.context_id is not None and 1 in revision.root_roles and revision.root_roles[1] in revision.objects

        }

        self.assertIn("VersionHistoryContent", context_root_kinds)