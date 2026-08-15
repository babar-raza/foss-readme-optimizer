# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_083.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_child_local_rule_overrides_deep_inherited_value(self) -> None:

        """child local rule overrides value inherited from grandparent."""

        doc, grandparent, parent, child = _doc_with_grandparent_parent_child()

        grandparent.style.set_property("color", "blue")

        child.style.set_property("color", "orange")



        child_style = child.get_computed_style()

        assert child_style.get_property_value("color") == "orange"