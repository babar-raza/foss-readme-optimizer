# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_039.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_tokenizer():

    with open('examples/fbx7400ascii/box.fbx', 'r') as f:

        content = f.read()



    tokenizer = FbxTokenizer(content)

    tokens = tokenizer.tokenize()



    print(f"Tokenized {len(tokens)} tokens")

    for i, token in enumerate(tokens[:20]):

        print(f"  {i}: {token}")



    return tokens