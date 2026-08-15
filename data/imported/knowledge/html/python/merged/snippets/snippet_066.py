# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_066.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_background_color_does_not_inherit(self) -> None:

        """background-color is non-inherited; child gets '' when parent has it."""

        doc, parent, child = _doc_with_parent_child()

        parent.style.set_property("background-color", "red")



        child_style = child.get_computed_style()

        assert child_style.get_property_value("background-color") == "", (

            "background-color is non-inherited; must not appear on child"

        )