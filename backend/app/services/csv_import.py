import csv
import hashlib
import io
from dataclasses import dataclass
from pathlib import PurePath

from sqlalchemy import select, tuple_
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models import ActivityHistory, ImportBatch, InventoryBalance, Product, Store
from app.models.product import utc_now
from app.schemas.inventory import ImportAcceptedRow, ImportRejectedRow
from app.services.errors import ConflictError, DatabaseOperationError
from app.services.sku_lookup import DuplicateSKUError, build_sku_index


MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_ROWS = 5000
MAX_STORED_QUANTITY = 2_147_483_647
REQUIRED_COLUMNS = {"sku", "store", "quantity"}


@dataclass
class _Accepted:
    output: ImportAcceptedRow
    balance: InventoryBalance
    reorder_provided: bool


@dataclass
class ParsedImport:
    file_name: str
    accepted: list[_Accepted]
    rejected: list[ImportRejectedRow]
    total_rows: int

    def preview(self) -> dict[str, object]:
        return {
            "file_name": self.file_name,
            "policy": "all_or_nothing",
            "total_rows": self.total_rows,
            "accepted_count": len(self.accepted),
            "rejected_count": len(self.rejected),
            "can_commit": bool(self.accepted) and not self.rejected,
            "accepted_rows": [row.output.model_dump() for row in self.accepted],
            "rejected_rows": self.rejected,
        }


def _column_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def parse_inventory_csv(session: Session, content: bytes, file_name: str) -> ParsedImport:
    if len(content) > MAX_IMPORT_BYTES:
        raise ConflictError("CSV file exceeds the 5 MiB import limit.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ConflictError("CSV must be UTF-8 encoded.") from exc
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        raw_headers = reader.fieldnames or []
        canonical_headers = [_column_key(header) for header in raw_headers]
    except csv.Error as exc:
        raise ConflictError("CSV header could not be parsed.") from exc

    # Accept the UI's Store column and explicit Store Code; reject ambiguous duplicates.
    aliases = {"storecode": "store", "storename": "store"}
    canonical_headers = [aliases.get(header, header) for header in canonical_headers]
    if len(canonical_headers) != len(set(canonical_headers)):
        raise ConflictError("CSV contains duplicate or ambiguous column headings.")
    missing = REQUIRED_COLUMNS - set(canonical_headers)
    if missing:
        raise ConflictError(f"CSV is missing required columns: {', '.join(sorted(missing))}.")
    if not raw_headers:
        raise ConflictError("CSV must include a header row.")

    products = session.scalars(select(Product).where(Product.is_active.is_(True))).all()
    stores = session.scalars(select(Store).where(Store.is_active.is_(True))).all()
    try:
        product_by_sku = build_sku_index(products)
    except DuplicateSKUError as exc:
        raise ConflictError("Active products contain duplicate SKUs; import cannot be resolved safely.") from exc

    store_by_ref: dict[str, Store | None] = {}
    for store in stores:
        for reference in (store.code.strip().casefold(), store.name.strip().casefold()):
            prior = store_by_ref.get(reference)
            if reference in store_by_ref and (prior is None or prior.id != store.id):
                store_by_ref[reference] = None
            else:
                store_by_ref[reference] = store

    balances = session.scalars(
        select(InventoryBalance).options(
            joinedload(InventoryBalance.product), joinedload(InventoryBalance.store)
        )
    ).all()
    balance_by_pair = {(balance.product_id, balance.store_id): balance for balance in balances}

    accepted: list[_Accepted] = []
    rejected: list[ImportRejectedRow] = []
    seen_pairs: set[tuple[int, int]] = set()
    total_rows = 0
    try:
        for row_number, raw_row in enumerate(reader, start=2):
            total_rows += 1
            if total_rows > MAX_IMPORT_ROWS:
                raise ConflictError(f"CSV exceeds the {MAX_IMPORT_ROWS}-row import limit.")
            values = {
                header: (raw_row.get(raw_header) or "").strip()
                for raw_header, header in zip(raw_headers, canonical_headers, strict=True)
            }
            errors: list[str] = []
            if None in raw_row:
                errors.append("Row has more values than the header.")
            if not any(values.values()):
                errors.append("Row is blank.")
            sku = values.get("sku", "").strip().upper()
            store_reference = values.get("store", "").strip().casefold()
            product = product_by_sku.get(sku)
            store = store_by_ref.get(store_reference)
            if not sku:
                errors.append("SKU is required.")
            elif product is None:
                errors.append(f"Unknown or inactive SKU '{sku}'.")
            if not store_reference:
                errors.append("Store is required.")
            elif store is None:
                errors.append(f"Unknown or inactive store '{values.get('store', '')}'.")

            quantity: int | None = None
            raw_quantity = values.get("quantity", "")
            try:
                if not raw_quantity or not raw_quantity.isdecimal():
                    raise ValueError
                quantity = int(raw_quantity)
                if quantity > MAX_STORED_QUANTITY:
                    raise ValueError
            except ValueError:
                errors.append("Quantity must be a whole number greater than or equal to zero.")

            reorder_level: int | None = None
            raw_reorder = values.get("reorderlevel", "")
            if raw_reorder:
                try:
                    if not raw_reorder.isdecimal():
                        raise ValueError
                    reorder_level = int(raw_reorder)
                    if reorder_level > MAX_STORED_QUANTITY:
                        raise ValueError
                except ValueError:
                    errors.append("Reorder Level must be a whole number greater than or equal to zero.")

            balance = None
            if product is not None and store is not None:
                pair = (product.id, store.id)
                if pair in seen_pairs:
                    errors.append("Duplicate SKU/store record in this CSV.")
                else:
                    seen_pairs.add(pair)
                    balance = balance_by_pair.get(pair)
                    if balance is None:
                        errors.append("No inventory balance exists for this SKU/store pair.")

            if errors:
                rejected.append(
                    ImportRejectedRow(row_number=row_number, values=values, errors=errors)
                )
                continue

            assert product is not None and store is not None and balance is not None
            assert quantity is not None
            accepted.append(
                _Accepted(
                    output=ImportAcceptedRow(
                        row_number=row_number,
                        sku=product.sku,
                        product_name=product.name,
                        store_code=store.code,
                        store_name=store.name,
                        old_quantity=balance.quantity,
                        new_quantity=quantity,
                        reorder_level=(
                            reorder_level if reorder_level is not None else balance.reorder_level
                        ),
                    ),
                    balance=balance,
                    reorder_provided=reorder_level is not None,
                )
            )
    except csv.Error as exc:
        raise ConflictError(f"CSV row near line {reader.line_num} could not be parsed.") from exc

    return ParsedImport(
        file_name=PurePath(file_name).name[:200] or "inventory.csv",
        accepted=accepted,
        rejected=rejected,
        total_rows=total_rows,
    )


def preview_inventory_csv(session: Session, content: bytes, file_name: str) -> dict[str, object]:
    with session.begin():
        parsed = parse_inventory_csv(session, content, file_name)
        return parsed.preview()


def _commit_inventory_csv(
    session: Session, content: bytes, file_name: str, idempotency_key: str
) -> dict[str, object]:
    with session.begin():
        if not idempotency_key.strip() or len(idempotency_key) > 128:
            raise ConflictError("Idempotency-Key must contain 1 to 128 characters.")
        idempotency_key = idempotency_key.strip()
        normalized_file_name = PurePath(file_name).name[:200] or "inventory.csv"
        request_hash = hashlib.sha256(
            normalized_file_name.encode("utf-8") + b"\0" + content
        ).hexdigest()
        inserted_key = session.scalar(
            postgresql_insert(ImportBatch)
            .values(
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
            .on_conflict_do_nothing(index_elements=[ImportBatch.idempotency_key])
            .returning(ImportBatch.idempotency_key)
        )
        if inserted_key is None:
            existing = session.get(ImportBatch, idempotency_key)
            if existing is None:
                raise ConflictError("Import result could not be safely recovered; retry with a new key.")
            if existing.request_hash != request_hash:
                raise ConflictError("Idempotency-Key was already used for a different CSV import.")
            if existing.result_payload is None:
                raise ConflictError("The original import is still being finalized; retry this request.")
            return existing.result_payload
        batch = session.get(ImportBatch, idempotency_key)

        parsed = parse_inventory_csv(session, content, file_name)
        if not parsed.accepted:
            raise ConflictError("CSV contains no importable data rows; nothing was changed.")
        if parsed.rejected:
            raise ConflictError(
                "Import is all-or-nothing: rejected rows must be corrected before any row is applied.",
                details=[
                    {
                        "row_number": row.row_number,
                        "errors": row.errors,
                        "values": row.values,
                    }
                    for row in parsed.rejected
                ],
            )

        pairs = sorted(
            {(row.balance.product_id, row.balance.store_id) for row in parsed.accepted}
        )
        locked_balances = session.scalars(
            select(InventoryBalance)
            .where(
                tuple_(InventoryBalance.product_id, InventoryBalance.store_id).in_(pairs)
            )
            .order_by(InventoryBalance.product_id, InventoryBalance.store_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).all()
        locked_by_pair = {
            (balance.product_id, balance.store_id): balance for balance in locked_balances
        }
        for row in parsed.accepted:
            key = (row.balance.product_id, row.balance.store_id)
            locked = locked_by_pair.get(key)
            if locked is None:
                raise ConflictError("A referenced inventory balance disappeared; preview the CSV again.")
            row.output.old_quantity = locked.quantity
            if not row.reorder_provided:
                row.output.reorder_level = locked.reorder_level
            row.balance = locked

        summary = parsed.preview()
        changed_units = 0
        now = utc_now()
        for row in parsed.accepted:
            balance = row.balance
            delta = row.output.new_quantity - balance.quantity
            changed_units += abs(delta)
            balance.quantity = row.output.new_quantity
            balance.reorder_level = row.output.reorder_level
            balance.updated_at = now
            session.add(
                ActivityHistory(
                    product_id=balance.product_id,
                    store_id=balance.store_id,
                    event_type="csv_import",
                    product_name=balance.product.name,
                    sku=balance.product.sku,
                    store_name=balance.store.name,
                    quantity_delta=delta,
                    note=f"CSV import {parsed.file_name} row {row.output.row_number}",
                    is_batch=True,
                    occurred_at=now,
                )
            )
        session.flush()
        result = {
            **summary,
            "imported_count": len(parsed.accepted),
            "changed_units": changed_units,
            "history_entries": len(parsed.accepted),
        }
        assert batch is not None
        batch.result_payload = result
        session.flush()
        return result


def commit_inventory_csv(
    session: Session, content: bytes, file_name: str, idempotency_key: str
) -> dict[str, object]:
    try:
        return _commit_inventory_csv(session, content, file_name, idempotency_key)
    except ConflictError:
        raise
    except SQLAlchemyError as exc:
        raise DatabaseOperationError() from exc
