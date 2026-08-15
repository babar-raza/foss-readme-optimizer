# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_073.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_unset_on_color_acts_as_inherit(self) -> None:

        """color: unset on a child acts as inherit when parent has a color rule."""

        doc, parent, child = _doc_with_parent_child()

        parent.style.set_property("color", "green")

        child.style.set_property("color", "unset")



        child_style = child.get_computed_style()

        assert child_style.get_property_value("color") == "green", (

            "unset on inherited property must act as inherit"

        )