# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_089.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_border_collapse_inherits(self) -> None:

        doc, parent, child = _doc_with_parent_child("table", "tr")

        parent.style.set_property("border-collapse", "collapse")

        assert child.get_computed_style().get_property_value("border-collapse") == "collapse"