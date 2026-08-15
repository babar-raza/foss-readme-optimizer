# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_069.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_inherit_keyword_on_inherited_property(self) -> None:

        """inherit on an already-inherited property also uses parent value."""

        doc, parent, child = _doc_with_parent_child()

        parent.style.set_property("color", "green")

        child.style.set_property("color", "inherit")



        child_style = child.get_computed_style()

        assert child_style.get_property_value("color") == "green"