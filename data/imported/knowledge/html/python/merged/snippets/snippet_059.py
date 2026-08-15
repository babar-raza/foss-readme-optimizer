# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_059.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_color_inherits_to_child(self) -> None:

        """Parent color: red propagates to child with no local color rule."""

        doc, parent, child = _doc_with_parent_child()

        sheet = CSSStyleSheet()

        sheet.replace_sync("div { color: red }")

        doc.attach_style_sheet(sheet)



        child_style = child.get_computed_style()

        assert child_style.get_property_value("color") == "red", (

            "color is an inherited property; child must receive parent value"

        )