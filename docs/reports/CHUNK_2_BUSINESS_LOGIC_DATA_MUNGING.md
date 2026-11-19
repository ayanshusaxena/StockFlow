# StockFlow Business Logic and Data Munging Report

## Scope

This report records the SKU lookup, replenishment ordering, and CSV inventory import work implemented for the StockFlow master execution cycle. It documents current behavior from source code; it does not define a forecast model or a general-purpose import API.

## SKU lookup

`backend/app/services/sku_lookup.py` provides `build_sku_index` and `find_by_sku`. Building an index costs **O(n)** time and memory for *n* products; an average lookup is **O(1)** by normalized SKU. SKU input is stripped and uppercased. Duplicate normalized SKU keys (for example, `el-001` and `EL-001`) raise `DuplicateSKUError` instead of silently selecting one product. A missing lookup returns no product. The database product lookup endpoint also uses the unique indexed SKU column and returns 404 for missing/inactive products.

## Replenishment prioritisation

`backend/app/services/replenishment.py` orders eligible balance rows with Python `heapq`. The priority tuple is deterministic: largest positive deficit (`reorder_level - quantity`) first, then greater reorder level, then SKU, store code, product ID, and balance ID. Rows with no positive deficit are not candidates. The suggested target is `max(2 * reorder_level - quantity, 0)`, a simple replenishment rule rather than a demand forecast. The API supports store filtering and `out`/`low` urgency filtering. Ties, empty input, and edge values are covered by business logic tests.

## CSV import workflow and policy

The preview and commit endpoints accept a raw UTF-8 CSV request body (`text/csv`); UTF-8 with BOM is accepted. Input is capped at 5 MiB and 5,000 data rows. Header names are trimmed and normalized; required fields are `SKU`, a store value (`Store`, `Store Code`, or `Store Name`), and `Quantity`. `Reorder Level` is optional. SKU and store references are resolved against active database records. Quantities and reorder levels must be whole, nonnegative integers. The importer detects repeated product/store pairs and reports row-numbered errors. The lookup index avoids rescanning every product for each CSV row.

Preview returns accepted and rejected row details and a `can_commit` result. Commit policy is **all-or-nothing**: any rejected row, or no accepted rows, prevents all balance and history writes. A valid commit treats quantity as an absolute inventory snapshot, optionally updates reorder level, and creates one `csv_import` activity row for each imported balance. Balance updates and activity rows share a database transaction. Commit requires an `Idempotency-Key`; identical retries replay the stored result, while reuse with changed content conflicts. Import activity is tied to its store/product for filtering. CSV imports do not create fabricated sale/restock movement records.

## Verification evidence

- `backend/tests/test_business_logic.py`: SKU normalization/missing/duplicate behavior and replenishment order, deterministic ties, empty queue, and edge cases.
- `backend/tests/test_csv_import.py`: parsing, preview and commit, row errors, duplicate pairs, bad headers/values, store filtering, all-or-nothing behavior, idempotent replay/conflict, and transaction rollback on a database failure.
- Full backend suite after implementation: **49 passed** using the isolated local PostgreSQL 18 test cluster (`stockflow_test`).

## Limitations

Store-name matching is based on the current store records and accepted header aliases; the importer does not infer ambiguous references. Preview results are not a reservation: inventory can change between preview and commit, so the commit transaction uses locks and applies the validated snapshot when committed. The suggested replenishment target is intentionally heuristic and should be revisited when a business-approved policy or demand data exists.
