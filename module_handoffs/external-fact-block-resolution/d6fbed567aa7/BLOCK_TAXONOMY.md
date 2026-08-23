# Block class taxonomy

`ExternalFactBlockClassV1` -- 13 values. Every non-`unknown` value is understood as a
refinement of the existing `supervisor.task.BlockedCategory`'s `"infra_external"` side
(`src/readme_agent/supervisor/task.py:34`); this module never touches `"agent_fixable"`
and never imports from `supervisor/`.

| Value | Meaning |
|---|---|
| `repository_clone_failure` | The product repository itself could not be cloned/fetched. |
| `git_lfs_object_unavailable` | Git LFS pointer(s) resolved but the backing object content was unavailable. |
| `package_registry_unavailable` | The package registry endpoint itself was unreachable. |
| `package_version_unresolved` | The registry was reachable but the specific package/version could not be resolved. |
| `toolchain_unavailable` | The build/verification toolchain (compiler, interpreter, SDK) was not present. |
| `dependency_resolution_failure` | Toolchain and registry were fine, but resolving the dependency graph itself failed. |
| `example_runtime_unavailable` | The environment needed to execute a README example was unavailable. |
| `source_package_mismatch` | A published package/artifact does not match the source it claims to derive from. |
| `network_rate_limited` | A remote endpoint enforced a rate limit. |
| `corrupt_local_cache` | A local cache used by the pipeline was corrupt (distinct from a network failure -- see `DEPENDENCY_INVALIDATION.md`). |
| `unsupported_platform_verifier` | No verifier exists for the current platform/ecosystem combination at all (distinct from `toolchain_unavailable`, where a verifier exists but its toolchain isn't installed). |
| `external_authentication_unavailable` | A required external credential/authentication context was unavailable. |
| `unknown` | Neither a structured `diagnostic_code` nor a `detail` substring match was found. Never guessed into a specific class. |

## Classification function

`classify_external_fact_block_class(*, diagnostic_code, detail)`:

1. Exact-match `diagnostic_code` against `_DIAGNOSTIC_CODE_TO_BLOCK_CLASS` (12 entries,
   this module's own vocabulary -- an upstream tool's real diagnostic codes need
   translating onto this vocabulary at integration time, which is explicitly out of
   scope here).
2. Only if no code is given or none matches: a bounded, ordered substring scan of
   `detail.casefold()` against `_DETAIL_SUBSTRING_TO_BLOCK_CLASS` (12 entries). Order
   encodes real precedence -- e.g. `"git lfs"` is checked before `"clone failed"` since
   an LFS failure message often also mentions "clone".
3. Otherwise: `"unknown"`. Never a fuzzy/best-guess class.

`resolve_external_fact_block()` always calls this internally from
`block.diagnostic_code` / `block.detail` -- there is no way for a caller to bypass
classification with a self-asserted class, since `ExternalFactBlockV1` has no
`block_class` field.
