# GitHub App Hosted Qualification

Status: `IMPLEMENTED_BUT_WAITING_HUMAN_APP_PROVISIONING`.

The control revision and disposable-staging gate are published. GitHub App registration,
private-key generation, and installation cannot be performed by the available `gh` CLI or by a
normal user PAT. The exact minimal owner action is recorded in `provisioning-request.json`.

This request deliberately installs a private App only on the three private disposable staging
repositories consumed by the frozen cohort. The control repository stores the Client ID and
private-key secret but does not need an App installation for this effect-only proof. This request
does not install the App on an Aspose product organization, authorize a product effect, enable a
webhook without a receiver, or grant any maturity credit.

The hosted workflow path is now explicit: it admits only `github_app_staging_effect`, restores the
checksum-bound frozen cohort on each clean effect runner, resolves the immutable target before
minting authority, and mints a repository-scoped App token only in the effect job. The local ACT
path retains its separate `staging_pat` provider; neither route falls back to ambient tokens.

Codex continues focused hosted-workflow verification and the verification-latency task while the
owner provisions the App. Live qualification resumes by validating repository variables/secrets
and the observed installation scope; the owner's statement alone is not treated as proof.
