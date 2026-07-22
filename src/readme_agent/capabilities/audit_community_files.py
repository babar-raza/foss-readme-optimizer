"""Community-files auditor (Wave 7e) -- domain `community_files_presentation`.
Class 1 per `docs/github-surface-control.md` (LICENSE, CONTRIBUTING,
CODE_OF_CONDUCT, SECURITY, SUPPORT, templates): repository-file managed, a
real eventual write path exists -- but this capability stops at audit +
prepared candidate content, never a write, matching this sub-wave's own
scope (7g registers this project's first real `local_write` capability, not
this one).

Correlates two signals that are NOT the same thing (`docs/github-surface-
control.md` finding PF-3, live-verified across this project's own registry:
7 of 25 repos, including the `cells-java` pilot, have real license content
GitHub's Community Profile API does not recognize): local file *presence*
(via the already-proven `inspection.file_inventory.scan()`, same clone
mechanics `orchestrator.inspect_repo()` already uses) and GitHub's own
*recognition* of that file (`GET /repos/{org}/{repo}/community/profile`).

Prepared candidate content is deliberately narrow: only `CODE_OF_CONDUCT.md`
gets real candidate text, the unmodified Contributor Covenant v2.1 (fetched
directly from its canonical source, `EthicalSource/contributor_covenant`'s
`release` branch, 2026-07-20 -- not LLM-generated, not hand-authored prose,
per `GOV-015`). `CONTRIBUTING.md`/`SECURITY.md`/`SUPPORT.md` have no single
canonical template GitHub itself publishes the way the Contributor Covenant
is for `CODE_OF_CONDUCT.md` -- fabricating boilerplate for those would be
inventing content this project cannot stand behind, so a missing file among
those three is reported as a finding only, with no `prepared_candidates`
entry, rather than an invented template dressed up as a proven source."""

from readme_agent import env, paths
from readme_agent.capabilities.domains import COMMUNITY_FILES_PRESENTATION
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.github_api.client import get_community_profile
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.inspection.file_inventory import scan
from readme_agent.license.auditor import detect_license
from readme_agent.registry.loader import require_listed

CAPABILITY_ID = "audit_community_files"

# Verbatim Contributor Covenant v2.1, fetched directly from its canonical
# source (raw.githubusercontent.com/EthicalSource/contributor_covenant/
# release/content/version/2/1/code_of_conduct.md, 2026-07-20) -- the
# `[INSERT CONTACT METHOD]` placeholder is the official template's own
# convention, left verbatim: every adopting project fills it in itself.
# Soft-wrapped at <=100 cols (a single `\n` inside a CommonMark paragraph
# renders as a space, not a line break, so this renders identically to the
# source's own long single-line paragraphs -- wording and order are
# unchanged from the fetched original, only line-wrapping differs).
_CONTRIBUTOR_COVENANT_2_1 = """# Contributor Covenant Code of Conduct

## Our Pledge

We as members, contributors, and leaders pledge to make participation in our community a
harassment-free experience for everyone, regardless of age, body size, visible or invisible
disability, ethnicity, sex characteristics, gender identity and expression, level of experience,
education, socio-economic status, nationality, personal appearance, race, caste, color, religion,
or sexual identity and orientation.

We pledge to act and interact in ways that contribute to an open, welcoming, diverse, inclusive,
and healthy community.

## Our Standards

Examples of behavior that contributes to a positive environment for our community include:

* Demonstrating empathy and kindness toward other people
* Being respectful of differing opinions, viewpoints, and experiences
* Giving and gracefully accepting constructive feedback
* Accepting responsibility and apologizing to those affected by our mistakes, and learning from
  the experience
* Focusing on what is best not just for us as individuals, but for the overall community

Examples of unacceptable behavior include:

* The use of sexualized language or imagery, and sexual attention or advances of any kind
* Trolling, insulting or derogatory comments, and personal or political attacks
* Public or private harassment
* Publishing others' private information, such as a physical or email address, without their
  explicit permission
* Other conduct which could reasonably be considered inappropriate in a professional setting

## Enforcement Responsibilities

Community leaders are responsible for clarifying and enforcing our standards of acceptable
behavior and will take appropriate and fair corrective action in response to any behavior that
they deem inappropriate, threatening, offensive, or harmful.

Community leaders have the right and responsibility to remove, edit, or reject comments, commits,
code, wiki edits, issues, and other contributions that are not aligned to this Code of Conduct,
and will communicate reasons for moderation decisions when appropriate.

## Scope

This Code of Conduct applies within all community spaces, and also applies when an individual is
officially representing the community in public spaces. Examples of representing our community
include using an official e-mail address, posting via an official social media account, or acting
as an appointed representative at an online or offline event.

## Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported to the
community leaders responsible for enforcement at [INSERT CONTACT METHOD]. All complaints will be
reviewed and investigated promptly and fairly.

All community leaders are obligated to respect the privacy and security of the reporter of any
incident.

## Enforcement Guidelines

Community leaders will follow these Community Impact Guidelines in determining the consequences
for any action they deem in violation of this Code of Conduct:

### 1. Correction

**Community Impact**: Use of inappropriate language or other behavior deemed unprofessional or
unwelcome in the community.

**Consequence**: A private, written warning from community leaders, providing clarity around the
nature of the violation and an explanation of why the behavior was inappropriate. A public
apology may be requested.

### 2. Warning

**Community Impact**: A violation through a single incident or series of actions.

**Consequence**: A warning with consequences for continued behavior. No interaction with the
people involved, including unsolicited interaction with those enforcing the Code of Conduct, for
a specified period of time. This includes avoiding interactions in community spaces as well as
external channels like social media. Violating these terms may lead to a temporary or permanent
ban.

### 3. Temporary Ban

**Community Impact**: A serious violation of community standards, including sustained
inappropriate behavior.

**Consequence**: A temporary ban from any sort of interaction or public communication with the
community for a specified period of time. No public or private interaction with the people
involved, including unsolicited interaction with those enforcing the Code of Conduct, is allowed
during this period. Violating these terms may lead to a permanent ban.

### 4. Permanent Ban

**Community Impact**: Demonstrating a pattern of violation of community standards, including
sustained inappropriate behavior, harassment of an individual, or aggression toward or
disparagement of classes of individuals.

**Consequence**: A permanent ban from any sort of public interaction within the community.

## Attribution

This Code of Conduct is adapted from the [Contributor Covenant][homepage], version 2.1,
available at [https://www.contributor-covenant.org/version/2/1/code_of_conduct.html][v2.1].

Community Impact Guidelines were inspired by [Mozilla's code of conduct enforcement
ladder][Mozilla CoC].

For answers to common questions about this code of conduct, see the FAQ at
[https://www.contributor-covenant.org/faq][FAQ]. Translations are available at
[https://www.contributor-covenant.org/translations][translations].

[homepage]: https://www.contributor-covenant.org
[v2.1]: https://www.contributor-covenant.org/version/2/1/code_of_conduct.html
[Mozilla CoC]: https://github.com/mozilla/diversity
[FAQ]: https://www.contributor-covenant.org/faq
[translations]: https://www.contributor-covenant.org/translations
"""

# Files GitHub's Community Profile API actually reports recognition for
# (verified live, see github_api/client.py::get_community_profile's
# docstring) -- SECURITY/SUPPORT have no recognition signal at all, so they
# are deliberately excluded from this mapping rather than defaulted to
# "not recognized", which would misreport "no signal" as "a negative signal".
_RECOGNIZED_FILE_KEYS = {
    "LICENSE": "license",
    "CONTRIBUTING": "contributing",
    "CODE_OF_CONDUCT": "code_of_conduct",
}

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Audit community files",
    purpose="Read-only: local presence scan (LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, "
    "SUPPORT) via the already-cloned baseline, correlated against GitHub's Community Profile "
    "API recognition -- presence and recognition are not the same thing. Prepares real, "
    "proven-source candidate content (the Contributor Covenant v2.1) only for a missing "
    "CODE_OF_CONDUCT.md -- never a write, and never fabricated content for the other files.",
    category="community_files_presentation",
    owner="readme_agent.inspection.file_inventory",
    execution_type="read_only_audit",
    required_inputs={"org_repo": "string"},
    produced_outputs={
        "present_files": "object",
        "recognized_files": "object",
        "community_profile_health_percentage": "integer",
        "presence_recognition_gaps": "array",
        "missing_files": "array",
        "prepared_candidates": "object",
        "detected_license": "string",
    },
    preconditions=[
        "org_repo must be listed in data/products.json (mode is irrelevant -- read-only)"
    ],
    required_permissions=["read_only_local", "read_only_network"],
    side_effect_class="read_only_network",
    allowed_domains=[COMMUNITY_FILES_PRESENTATION],
    tools_used=[
        "gitsafety.clone.clone_baseline",
        "inspection.file_inventory.scan",
        "github_api.client.get_community_profile",
    ],
    failure_modes=["NotAllowlistedError if org_repo is not listed in data/products.json"],
    rollback_behavior="not applicable -- read-only, nothing to roll back, no write ever attempted",
    tests=["tests/unit/test_capabilities.py"],
)


def execute(org_repo: str) -> dict:
    entry = require_listed(org_repo)
    baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
    clone_baseline(entry, baseline_path)
    inventory = scan(baseline_path)

    present_files = {"LICENSE": inventory.license_path is not None}
    for canonical_name in ("CONTRIBUTING", "CODE_OF_CONDUCT", "SECURITY", "SUPPORT"):
        present_files[canonical_name] = canonical_name in inventory.community_paths

    token = env.gh_token()
    profile = get_community_profile(org_repo, token)
    profile_files = profile.get("files") or {}
    recognized_files = {
        canonical_name: profile_files.get(api_key) is not None
        for canonical_name, api_key in _RECOGNIZED_FILE_KEYS.items()
    }

    presence_recognition_gaps = sorted(
        name
        for name, present in present_files.items()
        if present and name in recognized_files and not recognized_files[name]
    )
    missing_files = sorted(name for name, present in present_files.items() if not present)

    prepared_candidates = {}
    if not present_files["CODE_OF_CONDUCT"]:
        prepared_candidates["CODE_OF_CONDUCT"] = {
            "filename": "CODE_OF_CONDUCT.md",
            "content": _CONTRIBUTOR_COVENANT_2_1,
            "source": "Contributor Covenant v2.1 (https://www.contributor-covenant.org/"
            "version/2/1/code_of_conduct/) -- verbatim, requires filling in the "
            "[INSERT CONTACT METHOD] placeholder before use",
        }

    # Wave 7f: reuses the already-proven license.auditor.detect_license() --
    # GitHub's own SPDX classification (from this same Community Profile API
    # response) first, falling back to classifying the LICENSE file's own
    # content, exactly like orchestrator.py's own pipeline already does.
    # Feeds cross_surface_validation's comparison against readme_
    # reconciliation's independently-derived `license_claim`.
    license_info = profile_files.get("license") or {}
    detected_license = detect_license(license_info.get("spdx_id"), inventory.license_path).detected

    return {
        "present_files": present_files,
        "recognized_files": recognized_files,
        "community_profile_health_percentage": profile.get("health_percentage"),
        "presence_recognition_gaps": presence_recognition_gaps,
        "missing_files": missing_files,
        "prepared_candidates": prepared_candidates,
        "detected_license": detected_license,
    }
