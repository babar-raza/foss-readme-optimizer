# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_099.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_annotations_add(document):

    """Add annotations and verify count and properties."""

    page = document.pages[0]

    assert len(page.annotations) == 0



    annot = page.annotations.add("Text", (100, 100, 200, 200), "Hello")

    assert len(page.annotations) == 1

    assert annot.contents == "Hello"

    assert annot.rect == (100, 100, 200, 200)

    assert annot.subtype == "Text"



    annot2 = page.annotations.add("Text", (50, 50, 150, 150), "World", title="QA")

    assert len(page.annotations) == 2

    assert annot2.contents == "World"

    assert annot2.title == "QA"