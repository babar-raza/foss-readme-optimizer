# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_065.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_list_style_position_inherits(self) -> None:

        """list-style-position inherits (part of the list category in Level 4)."""

        doc, parent, child = _doc_with_parent_child("ul", "li")

        parent.style.set_property("list-style-position", "inside")



        child_style = child.get_computed_style()

        assert child_style.get_property_value("list-style-position") == "inside"