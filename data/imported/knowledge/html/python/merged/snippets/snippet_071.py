# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_071.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_initial_on_inherited_resets_to_empty(self) -> None:

        """color: initial ignores parent color and returns initial value ('')."""

        doc, parent, child = _doc_with_parent_child()

        parent.style.set_property("color", "red")

        child.style.set_property("color", "initial")



        child_style = child.get_computed_style()

        assert child_style.get_property_value("color") == "", (

            "initial must return the CSS initial value ('' in this implementation)"

        )