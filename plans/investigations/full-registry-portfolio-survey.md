# Full-Registry Portfolio Survey — All 25 Repositories, Human-Visitor Lens

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md`
> artifact_role: analysis_or_evidence_only
> Method: `tools/survey_full_registry.py` — GET-only `gh api` (repo core, community profile,
> languages, releases, README) against every entry in `data/products.json`, then the
> **shipped** `gap_detector` + a deterministic visitor-experience heuristic run against each
> real README. Zero mutation, zero clone. Evidence: `evidence/full-registry-github-survey/`
> (25 repos × ~5 files + `portfolio-survey-summary.json`).

## Why this survey exists

Every prior investigation artifact this sprint (current-state, proofs, coverage matrix) was
grounded in the **3 enabled pilots**. But `data/products.json` lists **25 real repositories,
all `active: true`**, across **11 GitHub orgs** and **6 platforms** — that is the actual
portfolio the system is meant to serve. Before deciding how the plan should proceed, this
survey asks the question a repository-presentation system must ultimately answer for every
one of these: **does a human land here and understand, trust, and start using the product?**
— not merely "does it have four specific links."

## Headline finding: the shipped 4-element check and real visitor experience are decoupled

| Repo | 4-element compliant (shipped gap_detector) | Visitor-experience score /8 |
|---|:-:|:-:|
| `aspose-3d-foss/…Java` (the plan's own "zero-gap" pilot) | **True** | **6/8** |
| `aspose-cells-foss/…Python` | False (fails 3/4) | **8/8** |
| `aspose-pdf-foss/…Java` (our dry-run pilot) | False (fails 1/4) | **8/8** |
| `aspose-email-foss/…Cpp` | False (fails 4/4) | **4/8** (lowest) |
| `aspose-email-foss/…Net` | False (fails 4/4) | **4/8** (lowest) |

Across all 25 repos, **compliance with the shipped 4-element check has no visible relationship
to visitor-experience quality** (full table: `evidence/full-registry-github-survey/portfolio-
survey-summary.json`). This is not a new principle — `plans/master.md` decision #10 already
flags 3d/java as "not the quality standard" and `RDM-014` already states span presence is not
proof of completeness — but this survey is the **first portfolio-scale empirical confirmation**
of it, across real product families the sponsor actually needs served, not one caveated pilot.

**What actually separates the best from the worst READMEs**, reading the raw text:
- **`cells-python`** and **`pdf-java`** (both 8/8): clear one-line product description with a
  concrete verb ("creating, reading, and modifying Excel files" / "working with PDF documents"),
  license + build + package-registry badges up front, a features list in plain bullets, a
  runnable example, and a docs/support path — genuinely different prose and structure from each
  other (proof that `BIZ-006`/no-common-template is achievable in practice, not just principle).
- **`email-cpp`** and **`email-net`** (both 4/8, the floor): the product explanation itself is
  actually *good* ("Aspose.Email FOSS for C++ is a dependency-free C++17 library for
  deterministic binary email container and message processing…") — these are **not** bot-
  template or thin READMEs. What's missing is **trust and navigation infrastructure**: no
  visible license statement, no badges, no docs link, no support/contribution path. A visitor
  who reads the opening understands the product fine, then has nowhere to go next and no signal
  the license is settled.

**Reframing consequence:** the sponsor's original "shameless promotion" concern (which drove
retiring the `callout` span, decision #9) is **not currently visible as an active problem
anywhere in this 25-repo portfolio** — `promo_before_product_explanation` is `False` for all
25. The acute, portfolio-wide gap is **trust/navigation completeness** (license visibility,
docs links, support paths — `RDM-005..016` territory), not promotional overreach. The retired
`callout` was a risk the *tool itself* introduced, not a pattern found in real product-agent
output today.

## Finding: ecosystem-parser coverage — 84% of the portfolio is unreachable today

| Platform | Repos in registry | Repos with a shipped parser |
|---|--:|--:|
| java | 4 | 3 enabled (parser: `ecosystems/maven.py`) |
| python | **10** | **0** |
| net | **5** | **0** |
| cpp | **3** | **0** |
| typescript | 2 | 0 |
| go | 1 | 0 |

Only Maven/Java has a parser. **21 of 25 repos (84%) — including all 10 Python repos, the
largest single platform in the registry — have zero deterministic manifest-fact extraction
available.** For any of them, the shipped tool cannot currently produce a `RepositoryFacts`
that includes real package coordinates, so it could not run in `full` mode honestly today.
This was already flagged qualitatively in the current-state reconstruction; this survey
supplies the scale and — critically — the **priority order by repo count**: Python (10) is
the highest-leverage next parser, not an arbitrary "whichever's next."

## Finding: license-recognition failure is a real, cross-family, structural pattern

**7 of 25 repos (28%)** have LICENSE content GitHub's community-profile API does not
recognize: **all 5 `cells` family repos** (cpp/java/net/python/typescript — every language
variant of one product, including `cells-java`, one of our two enabled `full`-mode pilots),
plus `3d-typescript` and `words-python`. This is bigger than the single nested-`License/
LICENSE.txt` finding surfaced earlier against `cells-java` alone — it is a **family-wide
convention** (the whole `cells` product line places its license somewhere GitHub doesn't
recognize), and it recurs independently in two unrelated families. That shape — consistent
within a family, inconsistent across families — is exactly a **product-agent convention
issue**, not a per-repo accident, and it is a **repository-file (class A)** fix: relocating or
adding a top-level `LICENSE` is squarely inside the system's proven push-blocked-clone
capability, unlike most other findings in this survey. This makes it a strong, low-risk
candidate for early community-file work rather than something that needs product-agent
handoff to resolve.

## Findings inventory (portfolio-wide, all read-only, zero mutation)

| # | Finding | Scope | Evidence |
|---|---|---|---|
| PF-1 | 4-element compliance and visitor experience are uncorrelated (best scorers fail 3-4/4 elements; the plan's own "zero-gap" pilot scores mid-pack) | all 25 | headline table above |
| PF-2 | Ecosystem parsers exist for 1 of 6 platforms; 84% of repos unreachable for real fact extraction | 21/25 repos | parser-coverage table |
| PF-3 | License-recognition failure is family-wide, not one-off (`cells` = 5/5; also `3d-typescript`, `words-python`) | 7/25 repos, 4 families | community-profile files |
| PF-4 | No repo shows promotion before product explanation — the retired-callout risk is not present in real product-agent output today | 25/25 clean | `visitor_experience` field, all repos |
| PF-5 | The weakest READMEs (`email` family, 4/8) have good product explanations but missing trust/navigation infrastructure (license, docs, support) — a different defect class than promo-link gaps | email-cpp, email-net (4/8); font/page/slides-java/slides-net/tex cluster at 5/8 | README text quoted above |
| PF-6 | The strongest READMEs (`cells-python`, `pdf-java`) are genuinely product-specific, not templated — empirical proof `BIZ-006` is achievable | 2/25, best-in-class | README text quoted above |
| PF-7 | All 25 GET calls succeeded; no repo is archived, disabled, or unreachable on GitHub | 25/25 | `portfolio-survey-summary.json` |
| PF-8 | Registry already has a working `overrides` mechanism (`cells-typescript`: `product_name`/`license` override), proving the registry schema anticipates per-repo variance | 1 repo, existing capability | `data/products.json` |

## How this should change plan direction (recommendation, not yet applied)

1. **Ecosystem-parser priority for the roadmap: Python first**, not alphabetical or
   Java-adjacent. 10 of 25 repos depend on it — more than double any other unserved platform.
   This should be reflected as an explicit ordering note when the roadmap (Tranche 5) is
   written, superseding any assumption that “add more ecosystems” is undifferentiated backlog.
2. **License-file recognition repair is a high-value, low-risk early community-file target**
   (Phase 23 / `SURF-007`) — it is class-A (repository-file), already provably within the
   system's safe push-blocked-clone capability, affects 28% of the portfolio, and is a
   structural pattern rather than 7 unrelated one-offs. Worth pulling forward relative to
   other community-file work (CONTRIBUTING/CODE_OF_CONDUCT) if the roadmap prioritizes by
   impact.
3. **The presentation-standard research (Phase 20 / `DOC-003/004`, still `DEFERRED_WITHOUT_
   DESIGN` per the coverage matrix) now has real before-state data to ground it** — 25 real
   READMEs scored on the same visitor-experience axes n8n/leading-FOSS study would use, rather
   than only the 14-README gap-audit corpus from 2026-07-17. This doesn't close the Phase-20
   gap (external research is still undone) but means Phase 21's eventual quality criteria can
   be validated against this portfolio's actual distribution, not assumed.
4. **`BIZ-001`/promotional-overreach risk should be de-prioritized relative to `RDM-005..016`
   completeness work** in whatever ordering the roadmap gives Phase 21 — the evidence says the
   live risk in this portfolio is trust/navigation gaps, not promotional dominance.
5. **Rollout-wave ordering (`PIL-009`, "small waves")** now has decision-support data: the
   sponsor could choose to wave-expand into already-strong repos first (lower risk, faster
   proof of the "no unsupported writes / no template cloning" gates) or into the weakest repos
   first (highest value-add). This survey doesn't decide that — it's a sponsor call — but the
   visitor-score distribution (`4/8` floor at `email` family, `8/8` ceiling at `cells-python`/
   `pdf-java`) is now available to inform it.
6. **No coverage-matrix classification changes are required by this survey** — `CORE-024`
   ("test against remaining corpus") remains `DEFERRED_WITHOUT_DESIGN` (this was analysis, not
   the insertion-point regression testing that requirement asks for) — but this survey's
   evidence should be cited when that roadmap card is written, since the corpus is now
   characterized.

## Method limitations (stated honestly)

The `visitor_experience` scorer is a **deterministic keyword/structure heuristic**, not a
human panel or an LLM judgment — it is a cheap, reproducible proxy (explicitly the kind of
"deterministic worker over autonomous LLM agent" preference this investigation has favored
throughout) good enough to reveal the *decoupling* between mechanical compliance and real
quality, not to serve as a production quality gate itself. Phase 20's actual presentation
standard is still the right place to define the real acceptance criteria. `install_keywords`
platform matching is shallow (string containment) and could be fooled by a README that
mentions a package manager name without a working command; this survey did not cross-check
install commands against live package registries at portfolio scale (that was done for the 3
pilots only, in the earlier current-state investigation, and surfaced the real `cells-java`
broken-Maven-Central finding).
