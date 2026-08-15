# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_063.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_visibility_inherits(self) -> None:

        """visibility is an inherited property."""

        doc, parent, child = _doc_with_parent_child()

        parent.style.set_property("visibility", "hidden")



        child_style = child.get_computed_style()

        assert child_style.get_property_value("visibility") == "hidden"