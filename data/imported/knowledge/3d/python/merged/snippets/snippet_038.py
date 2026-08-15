# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_038.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_simple():

    content = '''

; Test

FBXHeaderExtension:  {

    FBXHeaderVersion: 1003

    Version: 7400

    Creator: "Test"

}

'''

    tokenizer = FbxTokenizer(content)

    tokens = tokenizer.tokenize()



    print(f"Tokenized {len(tokens)} tokens")

    for i, token in enumerate(tokens):

        print(f"  {i}: {token}")