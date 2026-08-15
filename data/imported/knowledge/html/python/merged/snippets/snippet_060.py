# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_060.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_local_color_overrides_inherited(self) -> None:

        """Child local color rule beats parent inherited value."""

        doc, parent, child = _doc_with_parent_child()

        sheet = CSSStyleSheet()

        sheet.replace_sync("div { color: red } span { color: navy }")

        doc.attach_style_sheet(sheet)



        child_style = child.get_computed_style()

        assert child_style.get_property_value("color") == "navy"