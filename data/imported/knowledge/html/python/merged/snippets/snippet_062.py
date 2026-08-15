# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_062.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_word_spacing_inherits(self) -> None:

        """word-spacing is an inherited property (CSS Level 4 Appendix A)."""

        doc, parent, child = _doc_with_parent_child()

        parent.style.set_property("word-spacing", "4px")



        child_style = child.get_computed_style()

        assert child_style.get_property_value("word-spacing") == "4px"