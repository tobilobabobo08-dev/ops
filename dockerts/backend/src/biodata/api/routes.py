"""API routes mounted under ``/api/v1``."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from biodata import service
from biodata.db import get_session
from biodata.schemas import (
    BioRecordCreate,
    BioRecordPage,
    BioRecordRead,
    NamePhoneCreate,
    NamePhonePage,
    NamePhoneRead,
    RequestResponseCreate,
    RequestResponsePage,
    RequestResponseRead,
)

router = APIRouter(tags=["bio-records"])

SessionDep = Annotated[Session, Depends(get_session)]
IdempotencyKeyDep = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
        description="Client generated key making this write replay-safe.",
    ),
]


@router.post(
    "/bio-records",
    response_model=BioRecordRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {"description": "Replay of an identical earlier request."},
        status.HTTP_409_CONFLICT: {"description": "Idempotency key reused with a different body."},
    },
)
def create_bio_record(
    payload: BioRecordCreate,
    idempotency_key: IdempotencyKeyDep,
    session: SessionDep,
    response: Response,
) -> BioRecordRead:
    """Create a biodata record, idempotently on ``Idempotency-Key``."""
    try:
        record, created = service.create_record(session, payload, idempotency_key)
    except service.IdempotencyKeyReuseError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return BioRecordRead.model_validate(record)


@router.get("/bio-records", response_model=BioRecordPage)
def list_bio_records(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BioRecordPage:
    """Return a page of records ordered by ``created_at`` descending."""
    items, total = service.list_records(session, limit=limit, offset=offset)
    return BioRecordPage(
        items=[BioRecordRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/bio-records/{record_id}", response_model=BioRecordRead)
def get_bio_record(record_id: uuid.UUID, session: SessionDep) -> BioRecordRead:
    """Return a single record by id."""
    try:
        record = service.get_record(session, record_id)
    except service.RecordNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    return BioRecordRead.model_validate(record)


@router.post(
    "/contacts",
    response_model=NamePhoneRead,
    status_code=status.HTTP_201_CREATED,
    tags=["contacts"],
)
def create_contact(payload: NamePhoneCreate, session: SessionDep) -> NamePhoneRead:
    """Add a name and phone number entry."""
    record = service.create_name_phone(session, payload)
    return NamePhoneRead.model_validate(record)


@router.get(
    "/contacts",
    response_model=NamePhonePage,
    tags=["contacts"],
)
def list_contacts(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NamePhonePage:
    """List collected name and phone number entries."""
    items, total = service.list_name_phone(session, limit=limit, offset=offset)
    return NamePhonePage(
        items=[NamePhoneRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/request-responses",
    response_model=RequestResponseRead,
    status_code=status.HTTP_201_CREATED,
    tags=["request-responses"],
)
def create_request_response_log(
    payload: RequestResponseCreate, session: SessionDep
) -> RequestResponseRead:
    """Save a request-response log entry to the database."""
    log_entry = service.log_request_response(session, payload)
    return RequestResponseRead.model_validate(log_entry)


@router.get(
    "/request-responses",
    response_model=RequestResponsePage,
    tags=["request-responses"],
)
def list_request_response_logs(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RequestResponsePage:
    """List logged request-response entries from the database."""
    items, total = service.list_request_response_logs(session, limit=limit, offset=offset)
    return RequestResponsePage(
        items=[RequestResponseRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
