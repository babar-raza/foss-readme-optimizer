# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_075.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_unset_on_background_color_acts_as_initial(self) -> None:

        """background-color: unset returns '' (non-inherited → initial)."""

        doc, _parent, child = _doc_with_parent_child()

        child.style.set_property("background-color", "unset")



        child_style = child.get_computed_style()

        assert child_style.get_property_value("background-color") == "", (

            "unset on non-inherited property must act as initial ('' here)"

        )