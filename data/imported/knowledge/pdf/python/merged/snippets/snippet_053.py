# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_053.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_be_non_cloud_style_is_ignored():

    # /BE with a solid style ("S") is not a cloud: the border stays straight.

    gen = build_appearance(

        "Square", _RECT, {"C": [0, 0, 0], "BE": {"S": N("S")}, "BS": {"W": 1}}

    )

    assert b" re" in gen.content

    assert b" c\n" not in gen.content