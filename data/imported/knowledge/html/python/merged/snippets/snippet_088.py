# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_088.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_pointer_events_inherits(self) -> None:

        doc, parent, child = _doc_with_parent_child()

        parent.style.set_property("pointer-events", "none")

        assert child.get_computed_style().get_property_value("pointer-events") == "none"