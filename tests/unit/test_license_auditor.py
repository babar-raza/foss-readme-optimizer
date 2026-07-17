from readme_agent.license.auditor import classify_license_text, detect_license


class TestClassifyLicenseText:
    def test_mit(self):
        assert classify_license_text("MIT License\n\nCopyright...") == "MIT"

    def test_apache(self):
        text = "Apache License\nVersion 2.0, January 2004"
        assert classify_license_text(text) == "Apache-2.0"

    def test_unrecognized_text_returns_none(self):
        assert classify_license_text("Some proprietary terms nobody wrote down properly.") is None


class TestDetectLicense:
    def test_github_api_spdx_wins_when_present(self, tmp_path):
        state = detect_license("MIT", None)
        assert state.detected == "MIT"
        assert state.source == "github_api"

    def test_noassertion_falls_through_to_file(self, tmp_path):
        license_file = tmp_path / "LICENSE"
        license_file.write_text("MIT License\n\nPermission is hereby granted...", encoding="utf-8")

        state = detect_license("NOASSERTION", license_file)

        assert state.detected == "MIT"
        assert state.source == "file_content"

    def test_real_cells_scenario_null_github_but_file_says_mit(self, tmp_path):
        """The confirmed real case: GitHub's classifier reports null for
        aspose-cells-foss/Aspose.Cells-FOSS-for-Java (non-standard
        License/LICENSE.txt path), but the file itself states MIT."""
        nested = tmp_path / "License"
        nested.mkdir()
        license_file = nested / "LICENSE.txt"
        license_file.write_text(
            "This repository includes the MIT license. See below.\n\nMIT License\n...",
            encoding="utf-8",
        )

        state = detect_license(None, license_file)

        assert state.detected == "MIT"
        assert state.source == "file_content"

    def test_no_github_and_no_file_does_not_crash(self):
        state = detect_license(None, None)
        assert state.detected is None
        assert state.source == "undetected"

    def test_missing_file_path_does_not_crash(self, tmp_path):
        state = detect_license(None, tmp_path / "does-not-exist.txt")
        assert state.detected is None
        assert state.source == "undetected"

    def test_file_with_unrecognizable_content_does_not_crash(self, tmp_path):
        license_file = tmp_path / "LICENSE"
        license_file.write_text("All rights reserved, terms unclear.", encoding="utf-8")

        state = detect_license(None, license_file)

        assert state.detected is None
        assert state.source == "undetected"
