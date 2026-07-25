# Draft live-PR authorization records -- for human review only

Three draft `AuthorizationRecordV1` files for the Java Level-5 pilots, prepared per your request
("Draft records for my review only"). Each validates cleanly against the real schema
(`readme_agent.authorization.schema.AuthorizationRecordV1`).

**Deliberately NOT placed under `config/authorization/`.** They started there and were moved here
after they broke a real negative-control test
(`tests/unit/test_effect_ledger.py::test_the_real_open_presentation_pr_capability_is_blocked_for_every_repo_today`),
which runs live (no monkeypatching) against the real `config/authorization/` directory and asserts
it is empty for `aspose-cells-foss/Aspose.Cells-FOSS-for-Java` today. That confirmed, concretely,
what the files' own header comments already warned: `authorized_for()` only checks
`effect_classes` and `expiration`, not the `approving_identity` placeholder text -- so a file sitting
in the real `config/authorization/` directory is live-authoritative the moment it's readable on
disk, committed or not. Keeping the drafts here instead avoids that until you've actually approved
them.

## To approve one

1. Edit the file: replace `approving_identity` with your real identity, adjust `expiration` /
   `max_change_size` / anything else you want different.
2. Move it to `config/authorization/<the same filename>` (the org__repo naming already matches
   what `authorization/registry.py::_config_path()` expects).
3. For `aspose-pdf-foss__Aspose.PDF-FOSS-for-Java.yml` specifically: also flip its `products.json`
   entry's `mode` from `dry_run` to `full` -- the authorization record alone is not sufficient for
   that repo (`open_presentation_pr.py::execute()` separately requires `mode == "full"`).
4. Tell me to commit it (or commit it yourself).

## Files

- `aspose-cells-foss__Aspose.Cells-FOSS-for-Java.yml` -- already has one real, human-confirmed live
  PR (#1, master.md decision #52) opened before this authorization-record gate existed.
- `aspose-3d-foss__Aspose.3D-FOSS-for-Java.yml` -- `mode: full`, never live-PR'd yet.
- `aspose-pdf-foss__Aspose.PDF-FOSS-for-Java.yml` -- still `mode: dry_run`; see step 3 above.
