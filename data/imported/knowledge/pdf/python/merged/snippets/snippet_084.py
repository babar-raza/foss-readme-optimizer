# Adapted from aspose.org: knowledge/pdf/python/merged/snippets/snippet_084.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_generated_appearance_survives_save_load():

    doc = _new_page_doc()

    ann = doc.pages[0].annotations.add(

        "Circle", (100, 100, 200, 160), "", properties={"C": [0, 0, 1]}

    )

    ann.generate_appearance()

    buf = io.BytesIO()

    doc.save(buf)

    buf.seek(0)

    reopened = Document()

    reopened.load_from(buf)

    assert reopened.pages[0].annotations[0].has_appearance