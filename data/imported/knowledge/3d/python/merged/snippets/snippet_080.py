# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_080.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_pbr_material_creation(self):

        from aspose.threed.shading import PbrMaterial

        from aspose.threed.utilities import Vector3



        albedo = Vector3(0.5, 0.6, 0.7)

        material = PbrMaterial('TestMaterial', albedo)



        self.assertEqual(material.name, 'TestMaterial')

        self.assertEqual(material.albedo, albedo)

        self.assertEqual(material.metallic_factor, 0.0)

        self.assertEqual(material.roughness_factor, 0.0)

        self.assertEqual(material.transparency, 0.0)