# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_079.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_revert_on_text_align_on_root_returns_initial(self) -> None:

        """revert on root element (no parent) returns '' regardless of inherited status."""

        doc = Document()

        el = doc.create_element("div")

        doc.append_child(el)

        el.style.set_property("text-align", "revert")



        style = el.get_computed_style()

        assert style.get_property_value("text-align") == ""