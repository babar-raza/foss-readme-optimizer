# Threat model: path safety

The attestor treats both bundle roots as **untrusted input** -- a bundle could be corrupted,
tampered with, or adversarially crafted, and the module must never crash, never read outside the
bundle root, and never silently accept a hostile declaration as valid evidence.

## Two failure domains, on purpose

1. **Malformed contract** (a programmer/caller error, detected before any bundle content is ever
   touched): a `DeclaredArtifactV1.relative_path` containing `..`, a leading `/`, a drive letter,
   backslashes, control characters, an empty/`.`/`..` segment, more than 32 segments, or more than
   1024 characters raises `pydantic.ValidationError` at `ReplayAttestationContractV1` construction.
   Backslashes are **rejected outright, never normalized** -- silent normalization is exactly how a
   `a\..\..\x`-style string could slip past a naive check.
2. **Hostile/corrupted bundle content** (never raises -- always folds into a `passed=False` proof):
   everything discovered while actually walking or resolving paths inside a bundle.

This split matters: the attestor's whole purpose is to examine potentially-adversarial evidence, so
it must be total over bundle content (never crash on it) while still being strict about what the
*caller* is allowed to declare.

## Path resolution (`_resolve_declared_path`)

For a declared artifact's `relative_path`, resolved beneath `root`:

1. Walk each path component except the last; `os.lstat` each one (not `Path.stat`, which follows
   symlinks); reject if any component is a symlink or not a directory.
2. `os.lstat` the final component; reject if it is a symlink or not a regular file.
3. `resolved.relative_to(root.resolve())` inside `try/except ValueError` -- a second, independent
   containment check on top of the component-wise walk.

Any rejection surfaces as an `unsafe_paths` entry (an `escaping_symlink` finding), never an
exception -- a hostile bundle is expected input, not a crash trigger.

## Bundle-wide walk (`_walk_bundle`)

`os.walk(..., followlinks=False)` does **not** itself provide containment -- with `followlinks=False`
it simply won't *recurse into* a symlinked directory, but the symlinked directory name still
appears in `dirnames`, and its contents (if any were somehow enumerated) would be invisible rather
than flagged. The walk therefore `os.lstat`s every directory entry explicitly and prunes/flags any
symlink before `os.walk` would otherwise leave it ambiguous. Every file entry is also `os.lstat`'d;
non-regular or symlinked files are recorded as `unsafe_paths`, never hashed or read.

`evidence.file_inventory.enumerate_files` was deliberately **not** reused for this walk -- it calls
`Path.stat()` (follows symlinks), so a symlinked file pointing outside the bundle would pass its
`stat.S_ISREG` check and be silently hashed. The walk here uses `os.lstat` throughout instead.

## Self-declaration parsing (`_parse_sha256sums`)

The bundle's own `sha256sums.txt` is parsed strictly: each line must be `<64-hex-digest>  <relpath>`
(two spaces); malformed lines are skipped, not trusted; a relative path declared twice is recorded
as a `duplicate_declared_paths` entry (bundle corruption, `passed=False`) rather than silently
letting the last declaration win. **A recomputed hash is always compared against the bundle's own
declaration** (`hash_declaration_mismatches`) -- the module never trusts a stored digest without
independently recomputing it from the actual bytes.

## Bounds

`max_inventory_files` (default 5,000), `max_inventory_bytes` (default 1 GiB), and per-artifact
`max_bytes` (default 8 MiB, contract-capped at `max_artifact_bytes`, default 32 MiB) bound the walk
and every read -- an oversized bundle or artifact fails closed (`walk_error =
"inventory_bounds_exceeded"`, or the artifact is treated as unsafe) rather than exhausting memory.

## Redaction

Every human-readable `failures` string and `ReplayDriftFindingV1.detail` is passed through
`redact_secret_like_values` before being embedded in the proof (pattern-only redaction -- never
`env.secret_values()`, which reads live process environment and would make the proof
non-deterministic across processes). No artifact content is ever embedded in the proof beyond
digests and declared paths -- `SealedTransactionIdentityV1.component_digests` stores hashes, never
resolved values.

## What is explicitly out of scope

The attestor never executes artifact content (no `eval`, no dynamic import, no subprocess), never
writes to either bundle, and never inspects a live target repository -- product-effect proof is
sealed-evidence-only, never a live git/filesystem check against the repo the pipeline was
supposedly acting on (see `test_29a/b/c` for the enforcement of this boundary).
