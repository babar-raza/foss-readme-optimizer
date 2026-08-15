# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_096.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_color_convenience_setter():

    doc, page = _new_page()

    ann = page.annotations.add("Circle", (0, 0, 50, 50), "")

    ann.color = (0.2, 0.4, 0.6)

    a = _roundtrip(doc).pages[0].annotations[0]

    assert a.color == pytest.approx((0.2, 0.4, 0.6))