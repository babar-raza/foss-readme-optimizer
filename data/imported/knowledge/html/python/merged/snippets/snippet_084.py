# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_084.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_letter_spacing_inherits(self) -> None:

        doc, parent, child = _doc_with_parent_child()

        parent.style.set_property("letter-spacing", "2px")

        assert child.get_computed_style().get_property_value("letter-spacing") == "2px"