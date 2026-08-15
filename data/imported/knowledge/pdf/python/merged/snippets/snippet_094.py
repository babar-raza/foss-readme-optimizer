# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_094.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_every_known_subtype_roundtrips(subtype):

    doc, page = _new_page()

    page.annotations.add(

        subtype, (5, 5, 55, 55), f"c-{subtype}", properties={"NM": f"id-{subtype}"}

    )

    a = _roundtrip(doc).pages[0].annotations[0]

    assert a.subtype == subtype

    assert a.contents == f"c-{subtype}"

    assert a.get_property("NM") == f"id-{subtype}"