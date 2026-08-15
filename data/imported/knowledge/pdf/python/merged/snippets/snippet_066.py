# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_066.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_build_freetext_wraps_by_glyph_metrics():

    # Same word count, same box: wide 'W' words need more lines than narrow

    # 'i' words under real Helvetica metrics (a flat estimate would tie).

    wide = build_appearance(

        "FreeText",

        (0, 0, 60, 200),

        {"Contents": "WW WW WW WW WW", "DA": "/Helv 12 Tf 0 g"},

    )

    narrow = build_appearance(

        "FreeText",

        (0, 0, 60, 200),

        {"Contents": "ii ii ii ii ii", "DA": "/Helv 12 Tf 0 g"},

    )

    assert narrow is not None and wide is not None

    assert narrow.content.count(b" Tj") < wide.content.count(b" Tj")