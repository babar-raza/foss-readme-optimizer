# Upstream issues — Aspose.TeX FOSS for Python

**Repository:** `aspose-tex-foss/Aspose.TeX-FOSS-for-Python`
**Revision examined:** `2f4bfab3863e66ef32868f5464685eb4c2d36911` ("Release 26.5", 2026-06-02)
**Status:** Package is completely non-importable. No working revision, tag, release, or branch
exists to fall back to. **Not currently reusable as a source for an accurate README or for any
downstream consumer.**

This finding was produced twice, independently: once during routine README-generation source
verification, and a second time by a dedicated, deliberately unbiased re-investigation run
specifically to confirm or refute the first result without assuming its conclusion. Both runs
used different tooling and reached the same numbers. A third, older internal record
(`plans/investigations/evidence/l8-vpy-03-python-external-blockers/README.md`, dated 2026-08-01)
independently documented the same commit and the same failure counts before either of these two
runs began.

## Bottom line

`import aspose_tex` fails immediately — the package cannot be imported at all, let alone used.
This is not a partial or edge-case defect: every documented entry point (`TeXJob`, `PdfDevice`,
`DviDevice`, `SvgDevice`, `create_input_source`, etc.) is unreachable because the package's own
top-level `__init__.py` cannot finish loading.

## Root cause: indentation is collapsed to one space throughout the source tree

Every logical line's leading whitespace has been mechanically flattened to a **single ASCII
space**, regardless of true nesting depth. This is not a hypothesis — it is a direct byte-level
observation, confirmed identical across three independent fetch methods:

1. A fresh `git clone` of the repository (performed live, not a cached copy).
2. Raw HTTPS blob fetches directly from `raw.githubusercontent.com` at the pinned commit SHA,
   bypassing git entirely — byte-identical to the clone after line-ending normalization.
3. A separately pre-existing local clone at the same commit — a third corroborating data point.

Example (`src/aspose_tex/_engine/box_builder.py`, lines 59–77 — a `for` / `if` / `elif` nest that
requires 4 / 8 / 12 / 16-space indentation to be valid Python):

```
59	 total_w = 0
60	 max_h = 0
61	 max_d = 0
62	 for node in nodes:
63	 if isinstance(node, CharNode):
64	 m = font_manager.get_metrics(node.font_name)
65	 if m is not None:
66	 cm = m.char_metrics(node.char)
...
72	 elif isinstance(node, (HlistNode, VlistNode)):
```

Every line here — the `for` body, the nested `if`, the doubly-nested `if` — has exactly one
leading space. Python's parser cannot distinguish nesting levels that are supposed to be at
different depths, so it fails with `IndentationError`.

Because the collapse is applied uniformly with no regard for structure, it is:

- **Fatal** whenever a block needs a genuinely deeper indent to be distinguished from its parent
  (any function body followed immediately by a nested block, any `for`/`if` containing a further
  nested `if`).
- **Silently "passes" `ast.parse()`** whenever a block happens to be a flat sequence of statements
  with no further nesting — but the file is corrupted in exactly the same way; it just doesn't
  happen to trip the parser. **None of the files that currently parse should be read as
  "confirmed correct."**

## Scope: repository-wide, not an isolated file

Running `ast.parse()` / `python -m compileall` over every `.py` file in the repository:

| Location | Total `.py` files | Fail to parse | Parse OK (see caveat above) |
|---|---|---|---|
| `src/` | 45 | **35 (77.8%)** | 10 |
| `tests/` | 73 | **66 (90.4%)** | 7 |
| `run_hello.py` (root) | 1 | **1** | 0 |
| **Total** | **119** | **102 (85.7%)** | 17 |

Failing `src/` files (all `IndentationError: expected an indented block after ...`):

`_engine/box_builder.py`, `_engine/box_primitives.py`, `_engine/box_registers.py`,
`_engine/code_arrays.py`, `_engine/conditionals.py`, `_engine/dimparser.py`,
`_engine/expansion.py`, `_engine/group.py`, `_engine/inserts.py`,
`_engine/internal_quantities.py`, `_engine/interpreter.py`, `_engine/io_primitives.py`,
`_engine/leaders.py`, `_engine/linebreak.py`, `_engine/marks.py`, `_engine/math_shell.py`,
`_engine/named_parameters.py`, `_engine/nodes.py`, `_engine/page_builder.py`,
`_engine/par_primitives.py`, `_engine/registers.py`, `_fonts/encoding.py`,
`_fonts/font_manager.py`, `_fonts/font_metrics.py`, `_fonts/math_family_registry.py`,
`_fonts/pfb_parser.py`, `_fonts/tfm_parser.py`, `_fonts/type1_outlines.py`,
`_input/catcode.py`, `_input/reader.py`, `_input/tokenizer.py`, `_output/dvi_writer.py`,
`_output/pdf_writer.py`, `_output/svg_writer.py`, `presentation/__init__.py`.

Crucially, `_input/catcode.py` — one of the 35 failing files — sits directly on the package's own
mandatory import chain (see below), so the corruption is not confined to some optional or
peripheral module; it blocks the package from loading at all.

## Directly reproducing the import failure

```
$ PYTHONPATH=<clone>/src python -c "import aspose_tex"
File ".../src/aspose_tex/__init__.py", line 7, in <module>
    from aspose_tex._input.reader import FileInputSource, InputSource, StringInputSource
File ".../src/aspose_tex/_input/__init__.py", line 3, in <module>
    from aspose_tex._input.catcode import Catcode, CatcodeTable
File ".../src/aspose_tex/_input/catcode.py", line 66
    table[c] = Catcode.LETTER
    ^^^^^
IndentationError: expected an indented block after 'for' statement on line 65
```

`aspose_tex/__init__.py` cannot finish its own import chain. There is no way to import the
package, and therefore no way to reach any documented class (`TeXJob`, `OutputDevice`,
`PdfDevice`, `DviDevice`, `SvgDevice`, `TeXOptions`, `create_input_source`, ...) through the
public API surface described in the repository's own README.

`pip install` from the clone also fails, but on a separate, secondary Windows packaging error
(`setuptools` wheel staging cannot find `dependency_links.txt`) — this is noted only for
completeness; it is not being relied on as evidence of the corruption. The direct-import failure
above is the primary, unambiguous proof.

## No alternate working source exists

- **PyPI**: `https://pypi.org/pypi/aspose-tex/json` → HTTP 404. `aspose-tex-foss` → also HTTP 404.
  The repository's own README instructs `pip install aspose-tex`, but no such package is
  published.
- **Git refs**: `git ls-remote --heads --tags` returns exactly one ref, `refs/heads/main`. No
  tags, no releases, no other branches exist to check out instead.
- **Git history**: exactly two commits total. The first (`311455e`, 2026-05-19, "Initial commit")
  adds only `.gitignore`, `LICENSE`, and a one-line `README.md` — **no code at all**. The second
  (`2f4bfab`, the current HEAD) adds the entire source tree in one shot, already corrupted. There
  is no earlier working commit to revert to.
- **Issue tracker**: issues are enabled on the repository, but zero issues and zero pull requests
  exist (open or closed, via `gh issue list --state all` / `gh pr list --state all`) — this defect
  has not yet been reported upstream through the tracker.

## What would resolve this

The corruption pattern (uniform collapse to one space, applied identically across `src/` and
`tests/`) is consistent with a lossy export/transform step upstream of this commit — for example,
a code generator or formatting tool that stripped or failed to preserve indentation before the
release commit was authored. It is **not** a pattern that can be safely or completely reconstructed
by inferring "intended" indentation after the fact: many blocks are ambiguous (a flat sequence of
statements at the wrong depth parses without complaint but cannot be verified to have the exact
nesting the original algorithm needs), and this repository has no earlier correctly-indented
commit to diff against or restore from.

**Recommended remediation, in order of preference:**

1. Re-publish the release from its original, correctly-indented source (the pre-export copy, CI
   artifact, or generator output that predates whatever step introduced the collapse) as a new
   commit or tag.
2. If no correctly-indented source survives anywhere, the affected modules need to be rewritten
   from the TeX/LaTeX processing specification the package implements — this is a product-team
   task, not something a README-generation or documentation agent can safely infer or repair.
3. Once a corrected revision is published, verification should include: `python -m compileall src
   tests` reporting zero syntax errors, a clean `import aspose_tex`, and the repository's own
   quick-start example (`from aspose_tex import TeXJob, DviDevice`) succeeding end-to-end.

## Independent verification trail

- Fresh clone, raw-HTTPS comparison files, and the `ast`-based scan script used for this report
  are preserved under this session's scratch directory (see the investigation's evidence pointers
  in `logs/2026-08-12.md`) and are reproducible by re-running the same three fetch methods against
  the same pinned commit — the commit hash is content-addressed and will not change while this
  finding remains open.
- Prior corroborating record: `plans/investigations/evidence/l8-vpy-03-python-external-blockers/README.md`
  (2026-08-01) — same commit, same 102/119 failure count, same PyPI 404 result, reached
  independently and before this report.

## Why this repository does not currently get a generated README

Per the project's working-condition-presentation policy, a repository whose *source itself* is
non-importable has no verified working content to present — there is nothing a documentation
pipeline can honestly show as "this works" (unlike a repository that imports fine but merely fails
packaging/installation, where verified example code can still be shown running directly against
the source tree). This repository is therefore excluded from README delivery, in any form, until a
corrected revision is published and re-verified — see `data/working_condition_exceptions.json` and
`plans/decisions/catalog.jsonl` decision #101 for how that boundary is drawn against the small
number of repositories that *do* qualify for a working-condition exception.
