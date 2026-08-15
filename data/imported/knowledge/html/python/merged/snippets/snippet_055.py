# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_055.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_inline_only_resolves(self) -> None:

        """Inline-only declaration resolves without a stylesheet."""

        doc = Document()

        el = doc.create_element("div")

        doc.append_child(el)

        el.style.set_property("color", "green")

        style = el.get_computed_style()

        assert style.get_property_value("color") == "green"