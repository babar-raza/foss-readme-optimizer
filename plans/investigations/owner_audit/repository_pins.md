# Repository pins observed at audit start

Read-only GitHub commit searches on 2026-08-19 returned these default-branch commits. The optimizer
audit began at `6d112bbf...`; while it was running, main advanced through `d71f38b6...`,
`05ef1e5...`, and `91d9479...`:

| Repository | SHA | Latest change |
|---|---|---|
| `babar-raza/foss-readme-optimizer` | `91d9479b1e1fa12a9af41c1692b6f8f421db5f76` | Read-only acquisition-boundary evidence; preceding `05ef1e5...` safely makes SEO vocabulary shape bounded fallback title bytes |
| `aspose-3d-foss/Aspose.3D-FOSS-for-Python` | `ee05c1ba9153ef5916b7a108406c794f2e464d01` | Mermaid topology repair after README refresh |
| `aspose-note-foss/Aspose.Note-FOSS-for-Python` | `41de2e8ab478b5aeff3663f7f7cbf83b19fdf676` | README refresh run `rr-20260815T191258Z-2545f6e86187` |
| `aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python` | `06eca5c01e13ed6d59a640f1cf330c1c5a57d151` | Verified README refresh |

The three target repository tips already contain refreshed READMEs. Therefore a source-versus-
knowledge audit must distinguish:

1. repository implementation/package truth;
2. the pre-refresh README, recoverable from parent/history when needed;
3. the currently published refreshed README;
4. the imported knowledge snapshot and its declared `repo_sha`;
5. Aspose.org candidate/run evidence;
6. optimizer candidate/run evidence.

Treating the current README as the original input would contaminate preservation and quality
comparisons. All downstream audit reports must state which of these document identities they use.

The first owner-audit tranche remains pinned to `6d112bbf...` for code-path reproducibility. Later
commits add and repair a control-repository post-commit push hook; `eaf5eef6...` resolves the five
pre-existing suite failures after checking semantic outputs; `05ef1e5...` removes the unsafe SEO
fact-ID citation and adds one bounded visible SEO consumer; `91d9479...` records read-only intake
evidence and the setup.py silent-empty dependency gap. Current reported baseline is 4,214 passed,
1 skipped, 1 xfailed, 0 failed. The first-tranche knowledge/check/reconciliation/review conclusions
remain open except for the specifically closed SEO provenance issue.

## Sealed replay anchors

| Product | Refresh commit | Pre-refresh replay SHA | Notes |
|---|---|---|---|
| 3D/Python | `9fad4565c65e7e876b77acd4bcd9d58ef779498b` (followed by review/fix commits) | `ab1a2267a0ba6302311d0c7c4ad01494974c7d76` | This is also the `base_sha` recorded by the imported 3D knowledge delta. |
| Note/Python | `41de2e8ab478b5aeff3663f7f7cbf83b19fdf676` | `6d97a522a9ed24708687911f1aabb76e2dea2da7` | Imported knowledge is pinned to the pre-refresh SHA. |
| Barcode/Python | `06eca5c01e13ed6d59a640f1cf330c1c5a57d151` | `53f2c3350b8171f2c8275e7b1a178f218695ac45` | Imported knowledge is pinned to the pre-refresh SHA. |

These anchors are for read-only, sealed replay. They must not be confused with the current target
tips used for preservation/no-op checks.
