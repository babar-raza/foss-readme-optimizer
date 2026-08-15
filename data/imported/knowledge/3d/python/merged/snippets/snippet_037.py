# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_037.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_import_multiple_files(self):

        options = ColladaLoadOptions()

        

        examples_dir = os.path.join(os.path.dirname(__file__), '..', 'examples', 'collada')

        

        if os.path.exists(examples_dir):

            dae_files = glob.glob(os.path.join(examples_dir, '*.dae'))[:5]

            

            for dae_file in dae_files:

                try:

                    scene = Scene()

                    scene.open(dae_file, options)

                    

                    self.assertIsNotNone(scene.root_node)

                    self.assertTrue(len(scene.root_node.child_nodes) > 0 or 

                                  len(scene.root_node._entities) > 0,

                                  f"No nodes or entities found in {os.path.basename(dae_file)}")

                except Exception as e:

                    self.fail(f"Failed to import {os.path.basename(dae_file)}: {str(e)}")

        else:

            self.skipTest(f"Examples directory not found: {examples_dir}")