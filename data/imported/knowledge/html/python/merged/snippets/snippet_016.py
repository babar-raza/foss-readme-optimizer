# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_016.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_label_aliases():

    # At least 5 aliases verified against their documented canonical names.

    cases = [

        ("latin1",        "windows-1252"),

        ("iso-8859-1",    "windows-1252"),

        ("us-ascii",      "windows-1252"),

        ("shift-jis",     "shift_jis"),

        ("euc-kr",        "euc-kr"),

        ("csbig5",        "big5"),

        ("gb2312",        "gbk"),

    ]

    for label, expected in cases:

        assert get_canonical_name(label) == expected, (

            f"Expected {label!r} → {expected!r}, "

            f"got {get_canonical_name(label)!r}"

        )