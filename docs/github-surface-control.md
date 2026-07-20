# GitHub surface control matrix

Every surface a GitHub repository page can show, classified into exactly one of the five
control classes (decision #19), verified against current official GitHub documentation and
confirmed by live inspection of real repositories during this project's investigation (own
25-repository registry plus six external reference repositories — see
`plans/investigations/reference-repository-benchmark.md` and
`plans/investigations/full-registry-portfolio-survey.md`). This document is the authority for
`schema_version: 3` policy work (Phases 21+) and supersedes ad hoc surface assumptions anywhere
else in the codebase or plan.

## The five control classes

1. **Repository-file managed** — content lives in a file in the repository; this project's own
   push-blocked work clone can read and (later) propose changes to it.
2. **GitHub API/settings managed** — a repository-level field GitHub exposes through a REST
   endpoint; changes are proposals until an explicit apply gate authorizes a remote write.
3. **Manual UI managed** — a setting only changeable through the GitHub web UI, with no
   documented write API; the system prepares an asset and instructions, never claims automation.
4. **Product-agent owned** — technical/publishing truth that belongs to the product agent, not
   this system; the system audits and hands off findings, never writes.
5. **GitHub generated** — computed by GitHub from repository content/history; never editable by
   any agent; audit-only.

No renderer or remote-write path may exist for classes 4 or 5 (`OWN-003`, `OWN-004`, `CORE-022`).

## Per-surface reference

| Surface | Class | Authoritative source | Location | Permission | Apply behavior | Rollback | Evidence required |
|---|---|---|---|---|---|---|---|
| README content/structure | 1 | Product facts + this system's presentation policy | `README.md` in repo | Repo write (push-blocked clone only) | Prepared patch; human applies | Previous accepted blob | Diff, validation report, facts hash |
| README illustration/hero | 1 | This system, from product facts | Image file, repo-relative path | Repo write (push-blocked clone) | Prepared patch | Asset hash + prior state | Checksum, provenance, claims reviewed |
| `LICENSE` | 1 | Legal/product-agent decision | Repo root (GitHub only recognizes specific names/locations — see below) | Repo write (push-blocked clone) | Prepared patch | Previous file state | File presence + community-profile API confirmation |
| `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, issue/PR templates | 1 | Policy-driven per repo (`SURF-006`) | Repo root or `.github/` (GitHub-documented locations) | Repo write (push-blocked clone) | Prepared patch | Previous file state | File presence + community-profile API confirmation |
| Repository description | 2 | Product facts | `PATCH /repos/{owner}/{repo}` (`description` field) | `repo` scope, admin/write | Dry-run proposal; apply gate required | Recorded before-value | Before/after, permission, rollback plan |
| Homepage/website | 2 | Policy (canonical destination per product) | `PATCH /repos/{owner}/{repo}` (`homepage` field) | Same as description | Dry-run proposal; apply gate required | Recorded before-value | Before/after |
| Topics | 2 | Product facts + policy | `PUT /repos/{owner}/{repo}/topics` (separate endpoint from description/homepage) | Same as description | Dry-run proposal; apply gate required | Recorded before-value | Before/after, normalization check |
| Approved feature settings (Issues/Discussions/Wiki/Projects) | 2 | Explicit business justification only — never "because it exists" | `PATCH /repos/{owner}/{repo}` | Same as description | Dry-run proposal; apply gate required | Recorded before-value | Justification recorded per setting |
| Social-preview image | 3 | This system prepares; operator applies | Repository Settings UI (no documented write API as of this verification) | N/A (manual) | Prepared asset + instructions; status stays `PREPARED_FOR_MANUAL_APPLY` until operator evidence supplied | Previous asset (if recorded) | Asset validation, operator screenshot as apply evidence |
| Releases | 4 | Product agent | GitHub Releases feature | N/A — no write handler | Audit/handoff only | N/A | Handoff finding, evidence |
| Packages | 4 | Product agent | GitHub Packages feature | N/A — no write handler | Audit/handoff only | N/A | Handoff finding, evidence |
| Release/package-specific technical facts | 4 | Product agent | Varies (release notes, package metadata) | N/A | Handoff only | N/A | Finding cites source |
| Contributors | 5 | GitHub, computed from git history | Repo Insights / sidebar | N/A | Audit only, never editable | N/A | Observation recorded |
| Languages | 5 | GitHub Linguist, computed from repo files | Sidebar language bar | N/A | Audit only; legitimate remediation (e.g. `.gitattributes` `linguist-vendored`) is a class-1 change routed through normal repo-file gates | N/A | Anomaly explanation citing repo evidence |
| Stars, forks, watchers, activity, counts | 5 | GitHub | Sidebar | N/A | Observation only, never a quality gate | N/A | N/A |
| GitHub's page layout/tabs | 5 | GitHub | N/A | N/A | Never claimed as controllable | N/A | N/A |

## GitHub's native community-file surfacing — confirmed live, no UI work required

Verified directly on `github.com/n8n-io/n8n` (2026-07-18): below the repository header, GitHub
shows a quick-link row to README / Code of Conduct / Contributing / License / Security
**automatically**, driven entirely by which files exist and are recognized by the Community
Profile API (`GET /repos/{owner}/{repo}/community/profile`). Confirmed partially on
`apache/pdfbox` (Code of Conduct + Security shown; Contributing lacks a standalone file so gets
no quick-link, guidance lives inline in the README instead).

**This means the "professional tabbed profile" appearance some FOSS repos have is not a design
this system needs to build — it is a direct, automatic consequence of file presence and
recognition.** The system's entire obligation here is: (a) create/improve the recognized files
per policy (`SURF-007`), (b) place them where GitHub's documented recognition rules expect them,
(c) confirm recognition via the Community Profile API after applying a change. GitHub, not this
system, decides the tabs/links/layout/placement (`SURF-008`) — already correctly stated in the
Decision Ledger; this document supplies the live confirmation `RESEARCH-GATED` status required.

**License-file placement is the highest-value target.** Live evidence across the reference
repositories AND this project's own registry shows license *presence* and license
*recognition* are not the same thing: 7 of 25 registry repos (28%), including the `cells-java`
pilot this system has real write access to, have real license content GitHub's Community
Profile API does not recognize (`plans/investigations/full-registry-portfolio-survey.md`,
finding PF-3). This is a class-1, push-blocked-clone-eligible fix, not a product-agent handoff.

## Confirmed-empty surface: GitHub Packages

Checked live across every reference repository studied — n8n, iText, EPPlus, SheetJS, Apache
PDFBox — **all show 0 published GitHub Packages**, despite all being mature, widely-distributed
libraries with real external package-registry presence (npm, Maven Central, NuGet). No leading
project studied uses GitHub's native Packages feature for actual distribution. Consequence: this
system should never treat GitHub Packages population as a target; "does the product have
packages" is correctly answered by validating the README's install section against the real
external registry (Maven Central / NuGet / PyPI / npm), which is exactly what already-flagged
finding D-2 (`cells-java`'s broken Maven Central reference) addresses.

## Official GitHub documentation verified (source of the endpoint/permission facts above)

- Repository update API (`description`, `homepage`): <https://docs.github.com/en/rest/repos/repos>
- Topics use a separate endpoint ("replace all repository topics"):
  <https://docs.github.com/en/rest/repos/repos#replace-all-repository-topics>
- Community file recognition and surfacing:
  <https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors>
- Community Profile API (recognized README/license/code-of-conduct/contributing/templates):
  <https://docs.github.com/en/rest/metrics/community>
- Social-preview upload is a Settings UI action; no documented write API found as of this
  verification: <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview>
- Repository languages are computed from repository content, not directly settable:
  <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-repository-languages>

## What remains open

This document verifies the *mechanism* for every surface. It does not perform the live
before/after apply-gate proof for API/settings-managed surfaces (`SURF-004`/`SURF-005`) or the
product-facts/change-handoff schema freeze (`DOC-006`) — both remain scoped to Phase 21/22
implementation work, not documentation.
