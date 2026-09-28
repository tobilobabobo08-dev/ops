"""Data access for :class:`~biodata.models.BioRecord`."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from biodata.models import BioRecord, NamePhoneCollection, RequestResponseLog


def get_by_id(session: Session, record_id: uuid.UUID) -> BioRecord | None:
    """Return the record with ``record_id`` or ``None``."""
    return session.get(BioRecord, record_id)


def get_by_idempotency_key(session: Session, key: str) -> BioRecord | None:
    """Return the record stored under ``key`` or ``None``."""
    stmt = select(BioRecord).where(BioRecord.idempotency_key == key)
    return session.execute(stmt).scalar_one_or_none()


def insert_if_absent(session: Session, values: dict[str, Any]) -> tuple[BioRecord, bool]:
    """Insert a record, tolerating a concurrent or replayed insert.

    Returns the stored record and whether this call created it.
    """
    payload = {"id": uuid.uuid4(), **values}
    bind = session.get_bind()
    dialect_name = bind.dialect.name if bind else ""

    if dialect_name == "postgresql":
        stmt = (
            pg_insert(BioRecord)
            .values(**payload)
            .on_conflict_do_nothing(index_elements=[BioRecord.idempotency_key])
            .returning(BioRecord.id)
        )
        created_id = session.execute(stmt).scalar_one_or_none()
        session.commit()

        if created_id is not None:
            record = get_by_id(session, created_id)
            if record is None:  # pragma: no cover - defensive
                raise RuntimeError("inserted record disappeared")
            return record, True

        existing = get_by_idempotency_key(session, str(values["idempotency_key"]))
        if existing is None:  # pragma: no cover - defensive
            raise RuntimeError("conflicting record disappeared")
        return existing, False
    else:
        existing = get_by_idempotency_key(session, str(values["idempotency_key"]))
        if existing is not None:
            return existing, False

        record = BioRecord(**payload)
        session.add(record)
        try:
            session.commit()
            return record, True
        except Exception:
            session.rollback()
            existing = get_by_idempotency_key(session, str(values["idempotency_key"]))
            if existing is not None:
                return existing, False
            raise


def list_records(session: Session, limit: int, offset: int) -> tuple[list[BioRecord], int]:
    """Return a page of records ordered by ``created_at`` descending, plus the total."""
    total = session.execute(select(func.count()).select_from(BioRecord)).scalar_one()
    stmt = (
        select(BioRecord)
        .order_by(BioRecord.created_at.desc(), BioRecord.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(session.execute(stmt).scalars().all())
    return items, total


def create_name_phone(session: Session, name: str, phone_number: str) -> NamePhoneCollection:
    """Create a new name and phone number entry in database."""
    record = NamePhoneCollection(name=name, phone_number=phone_number)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def list_name_phone(
    session: Session, limit: int = 20, offset: int = 0
) -> tuple[list[NamePhoneCollection], int]:
    """Return list of collected names and phone numbers."""
    total = session.execute(select(func.count()).select_from(NamePhoneCollection)).scalar_one()
    stmt = (
        select(NamePhoneCollection)
        .order_by(NamePhoneCollection.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(session.execute(stmt).scalars().all())
    return items, total


def create_request_response_log(
    session: Session,
    method: str,
    path: str,
    status_code: int,
    request_body: str | None = None,
    response_body: str | None = None,
) -> RequestResponseLog:
    """Log request and response details to database."""
    log_entry = RequestResponseLog(
        method=method,
        path=path,
        status_code=status_code,
        request_body=request_body,
        response_body=response_body,
    )
    session.add(log_entry)
    session.commit()
    session.refresh(log_entry)
    return log_entry


def list_request_response_logs(
    session: Session, limit: int = 20, offset: int = 0
) -> tuple[list[RequestResponseLog], int]:
    """Return logged request response pairs."""
    total = session.execute(select(func.count()).select_from(RequestResponseLog)).scalar_one()
    stmt = (
        select(RequestResponseLog)
        .order_by(RequestResponseLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(session.execute(stmt).scalars().all())
    return items, total
