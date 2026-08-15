# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_080.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_color_propagates_through_two_ancestor_levels(self) -> None:

        """grandparent color propagates via parent to child (two hops)."""

        doc, grandparent, parent, child = _doc_with_grandparent_parent_child()

        sheet = CSSStyleSheet()

        sheet.replace_sync("div { color: teal }")

        doc.attach_style_sheet(sheet)



        # The grandparent rule sets color: teal; parent inherits it; child inherits

        # from parent (which already resolved teal from grandparent).

        child_style = child.get_computed_style()

        assert child_style.get_property_value("color") == "teal"