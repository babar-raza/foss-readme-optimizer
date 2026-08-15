# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_072.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_initial_on_non_inherited_returns_empty(self) -> None:

        """background-color: initial returns '' (the CSS initial value here)."""

        doc, _parent, child = _doc_with_parent_child()

        child.style.set_property("background-color", "initial")



        child_style = child.get_computed_style()

        assert child_style.get_property_value("background-color") == ""