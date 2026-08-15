# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_100.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_annotations_update(page_with_annotations):

    """Update annotation contents, rect, and title."""

    page = page_with_annotations

    annot = page.annotations[0]



    annot.contents = "Updated content"

    assert page.annotations[0].contents == "Updated content"



    annot.rect = (10, 20, 30, 40)

    assert page.annotations[0].rect == (10, 20, 30, 40)



    annot.title = "New Author"

    assert page.annotations[0].title == "New Author"

    assert page.annotations[0].author == "New Author"