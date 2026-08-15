# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_048.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_line_none_ending_draws_only_the_shaft():

    gen = build_appearance(

        "Line", _RECT, {"L": [10, 40, 100, 40], "LE": [N("None"), N("None")]}

    )

    assert gen.content.count(b"\nS\n") == 1  # shaft only
