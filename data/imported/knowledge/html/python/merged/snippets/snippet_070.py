# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_070.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_inherit_keyword_on_root_returns_initial(self) -> None:

        """inherit on a root element (no parent) returns initial value ('')."""

        doc = Document()

        el = doc.create_element("div")

        doc.append_child(el)

        el.style.set_property("color", "inherit")



        style = el.get_computed_style()

        assert style.get_property_value("color") == ""