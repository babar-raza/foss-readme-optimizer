# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_052.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_later_rule_wins_same_specificity(self) -> None:

        """When specificity is equal, the later source-order rule wins."""

        doc = Document()

        el = doc.create_element("div")

        doc.append_child(el)



        sheet = CSSStyleSheet()

        # Two type-selector rules with equal specificity (0,0,1).

        sheet.replace_sync("div { color: red } div { color: blue }")

        doc.attach_style_sheet(sheet)



        style = el.get_computed_style()

        assert style.get_property_value("color") == "blue", (

            "Later source-order rule must win when specificity is equal"

        )