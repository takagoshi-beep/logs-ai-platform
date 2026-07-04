# Sprint32 E2E Validation Report


<!-- SNAPSHOT-BANNER -->
> **📌 Point-in-time snapshot.** This document records the state of the
> project as of the date/phase named in its title or body. It has not been
> updated since, and may not reflect the current code. Verify claims against
> the current source before relying on them. For the maintained, current
> architecture reference, see `docs/architecture.md` and `docs/system_manifest.md`.

## Summary

- Sync status: success
- Files processed: 3
- Tables imported: 11
- Rows imported: 12
- Validation status: ok
- Catalog items: 6
- Sync status last_synced_at: 2026-06-29T04:20:23.281008+00:00

## E2E Questions

- 売上トップ10は？: success=True, source=None
- ABC社との取引履歴: success=False, source=None
- バッグ商品の一覧: success=True, source=None
- 今月受注金額: success=False, source=None

## Notes

- This report is generated from the local validation harness.
- Real Google Drive OAuth and folder access require external credentials and folder IDs.
- Business answers include source_information when Storage metadata is available.
