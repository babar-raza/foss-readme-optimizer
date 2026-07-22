"""Wave 8.7 (Item M): proves `policy_generator.generate_policy_profile()`'s
mechanical derivation is correct by reproducing the 3 real, already-onboarded
policy profiles as golden fixtures -- the strongest possible proof the
mechanism is sound before trusting it for the 22 not-yet-onboarded entries
it has never been validated against by a human."""

from pathlib import Path

import yaml

from readme_agent.registry.policy_generator import generate_policy_profile, platform_label

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICIES_DIR = REPO_ROOT / "config" / "policies"


class TestPlatformLabel:
    def test_derives_from_the_for_suffix(self):
        assert platform_label("Aspose.Cells-FOSS-for-Java") == "Java"
        assert platform_label("Aspose.Cells-FOSS-for-.NET") == ".NET"
        assert platform_label("Aspose.Email-FOSS-for-.Net") == ".Net"
        assert platform_label("Aspose.Cells-FOSS-for-Cpp") == "Cpp"
        assert platform_label("Aspose-PDF-FOSS-for-Go") == "Go"


class TestGeneratePolicyProfileGoldenFixtures:
    """Each existing real profile was authored for the org's one already-
    onboarded (Java) platform -- the generator must reproduce all three
    exactly, proving its mechanical derivation matches real, human-authored
    content before it's trusted for entries no human has reviewed yet."""

    def test_reproduces_aspose_3d_foss(self):
        expected = yaml.safe_load((POLICIES_DIR / "aspose-3d-foss.yml").read_text("utf-8"))
        generated = generate_policy_profile(
            profile_name="aspose-3d-foss",
            family="3d",
            family_name="Aspose.3D",
            platform="java",
            repo_name="Aspose.3D-FOSS-for-Java",
            detected_license="MIT",
        )
        assert generated == expected

    def test_reproduces_aspose_cells_foss(self):
        expected = yaml.safe_load((POLICIES_DIR / "aspose-cells-foss.yml").read_text("utf-8"))
        generated = generate_policy_profile(
            profile_name="aspose-cells-foss",
            family="cells",
            family_name="Aspose.Cells",
            platform="java",
            repo_name="Aspose.Cells-FOSS-for-Java",
            detected_license="MIT",
        )
        assert generated == expected

    def test_reproduces_aspose_pdf_foss(self):
        expected = yaml.safe_load((POLICIES_DIR / "aspose-pdf-foss.yml").read_text("utf-8"))
        generated = generate_policy_profile(
            profile_name="aspose-pdf-foss",
            family="pdf",
            family_name="Aspose.PDF",
            platform="java",
            repo_name="Aspose.PDF-FOSS-for-Java",
            detected_license="MIT",
        )
        assert generated == expected


class TestGeneratePolicyProfileNewPlatforms:
    """A sample of the 22 not-yet-onboarded entries, proving the mechanism
    generalizes correctly beyond the 3 golden Java fixtures -- distinct
    platforms (.NET, Cpp, Go, TypeScript) and the one family (email) whose
    real repo name uses different casing (".Net", not ".NET")."""

    def test_dotnet_platform(self):
        generated = generate_policy_profile(
            profile_name="aspose-cells-foss-net",
            family="cells",
            family_name="Aspose.Cells",
            platform="net",
            repo_name="Aspose.Cells-FOSS-for-.NET",
            detected_license="MIT",
        )
        org_link = generated["required_elements"]["products_org_link"]
        assert org_link["url"] == "https://products.aspose.org/cells/net/"
        assert org_link["label"] == "Aspose.Cells FOSS for .NET"

    def test_email_dot_net_casing_is_preserved_verbatim(self):
        """The registry itself is inconsistent (`Aspose.Cells-FOSS-for-.NET`
        vs. `Aspose.Email-FOSS-for-.Net`) -- the generator must reflect
        whatever the real repo name actually says, never a "corrected"
        casing that might not match the real product."""
        generated = generate_policy_profile(
            profile_name="aspose-email-foss-net",
            family="email",
            family_name="Aspose.Email",
            platform="net",
            repo_name="Aspose.Email-FOSS-for-.Net",
            detected_license="MIT",
        )
        assert (
            generated["required_elements"]["products_org_link"]["label"]
            == "Aspose.Email FOSS for .Net"
        )

    def test_go_platform(self):
        generated = generate_policy_profile(
            profile_name="aspose-pdf-foss-go",
            family="pdf",
            family_name="Aspose.PDF",
            platform="go",
            repo_name="Aspose-PDF-FOSS-for-Go",
            detected_license="MIT",
        )
        org_link = generated["required_elements"]["products_org_link"]
        assert org_link["url"] == "https://products.aspose.org/pdf/go/"
        assert org_link["label"] == "Aspose.PDF FOSS for Go"

    def test_shared_constants_are_identical_across_every_generated_profile(self):
        a = generate_policy_profile(
            profile_name="a",
            family="cells",
            family_name="Aspose.Cells",
            platform="cpp",
            repo_name="Aspose.Cells-FOSS-for-Cpp",
            detected_license="MIT",
        )
        b = generate_policy_profile(
            profile_name="b",
            family="words",
            family_name="Aspose.Words",
            platform="python",
            repo_name="Aspose.Words-FOSS-for-Python",
            detected_license="MIT",
        )
        assert a["secondary_links"] == b["secondary_links"]
        assert a["block"] == b["block"]
        assert (
            a["required_elements"]["relationship_explained"]
            == b["required_elements"]["relationship_explained"]
        )
