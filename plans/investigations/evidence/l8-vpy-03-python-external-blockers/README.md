# L8-VPY-03 Python Product-Source Blockers

This evidence records the two external product-source conditions that prevent the final two
Python repositories from reaching verified README approval. Ten of the twelve dynamically loaded
Python repositories are `NO_OP_PROVEN`; these two are not counted as approved.

## Aspose.HTML FOSS for Python

- Repository: `aspose-html-foss/Aspose.HTML-FOSS-for-Python`
- Upstream revision: `c2356ec872fd7d64c14a0ae8cc043eea1a03847e`
- First failing boundary: verified source acquisition
- Root cause: `pyproject.toml` declares the nonexistent PEP 517 backend
  `setuptools.backends.legacy:build`.
- PyPI result on 2026-08-01: `aspose-html-foss` returned HTTP 404, so no published acquisition
  path can replace source-build verification.

The exact product correction is:

```diff
-build-backend = "setuptools.backends.legacy:build"
+build-backend = "setuptools.build_meta"
```

This one-line change was committed only in disposable local diagnostic clone
`runs/diagnostics/aspose-html-foss-python-backend-c2356ec8` at diagnostic revision
`546d7fea104b7e54c3123dba47ba745492daeb3e`. The canonical isolated verifier then built the
pinned source and executed the repository-authored public example
`HTMLDocument.parse("<main id='content'><h1>Hello</h1></main>")` with exit 0. This proves the
correction is sufficient locally; it does not claim the upstream repository is fixed.

Unblock condition: apply the exact one-line correction to the product repository through a
separately authorized product change, then rerun the canonical verified canary against the new
immutable upstream revision.

## Aspose.TeX FOSS for Python

- Repository: `aspose-tex-foss/Aspose.TeX-FOSS-for-Python`
- Upstream revision: `2f4bfab3863e66ef32868f5464685eb4c2d36911`
- First failing boundary: repository/package syntax and verified source acquisition
- PyPI results on 2026-08-01: both `aspose-tex` and `aspose-tex-foss` returned HTTP 404.
- Current tree: 119 Python files; 102 are syntax-invalid because required indentation is absent.
  The failures comprise 35 files under `src/`, 66 under `tests/`, and `run_hello.py`.
- Deterministic syntax-error inventory SHA-256:
  `ef94d7e76fc1bd197fdd40e5cd687d6882ab9fb1c13d63402d31d74590f684ff`.
- Git history contains only the metadata-only initial commit `311455e` and release commit
  `2f4bfab`; no prior authoritative implementation can be restored.

This is not safely repairable by README machinery or inferred bulk indentation. The product owner
or originating product-development generator must republish the authoritative correctly indented
source and tests. Aspose.org prose can help locate intended APIs, but it cannot establish executable
source truth or reconstruct exact program structure.

Unblock condition: publish an authoritative, syntax-valid product revision, after which the normal
package, public-API, example, product-truth, composition, review, and no-op gates must all rerun.

## Safety and status

No product remote was written. The HTML diagnostic commit exists only beneath ignored `runs/`.
Neither repository is approved, and neither blocker may be replaced with generic or unverified
README prose. The active umbrella mission can continue on later platforms because both remaining
Python boundaries require product-repository authority or corrected upstream source.
