# Adapted from aspose.org: knowledge/3d/python/merged/snippets/snippet_049.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_io_service_registration(self):

        service = IOService()

        exporter = Exporter()

        importer = Importer()

        detector = FormatDetector()

        

        service.register_exporter(exporter)

        service.register_importer(importer)

        service.register_detector(detector)

        

        self.assertIn(exporter, service._exporters)

        self.assertIn(importer, service._importers)

        self.assertIn(detector, service._detectors)