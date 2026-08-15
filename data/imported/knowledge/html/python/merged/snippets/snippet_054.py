# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_054.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_no_rule_no_property(self) -> None:

        """Element with no matching rules has no color in computed style."""

        doc = Document()

        el = doc.create_element("span")

        doc.append_child(el)

        style = el.get_computed_style()

        assert style.get_property_value("color") == ""