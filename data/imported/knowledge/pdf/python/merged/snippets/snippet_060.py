# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_060.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_build_ink_draws_each_path():

    gen = build_appearance(

        "Ink", (0, 0, 100, 100), {"InkList": [[0, 0, 50, 50], [10, 10, 60, 10, 60, 60]]}

    )

    assert gen is not None

    assert gen.content.count(b" m\n") == 2  # one moveto per path

    assert gen.content.count(b"\nS\n") == 2