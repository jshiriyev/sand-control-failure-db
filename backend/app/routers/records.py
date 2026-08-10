"""POST /records (submit) and GET /records/{id} (fetch, org-scoped)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.deps.auth import get_current_org
from backend.app.deps.db import get_db
from backend.app.schemas.ingest import RecordCreated, RecordIngest
from backend.app.schemas.record_out import RecordOut
from backend.app.services.record_ingest import build_record_response, create_record, get_well_owned_by
from db.models import Organization

router = APIRouter(prefix="/records", tags=["records"])


@router.post("", response_model=RecordCreated, status_code=status.HTTP_201_CREATED)
def submit_record(
    payload: RecordIngest,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> RecordCreated:
    well = create_record(db, org, payload)
    return RecordCreated(id=well.id)


@router.get("/{record_id}", response_model=RecordOut)
def fetch_record(
    record_id: int,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> RecordOut:
    well = get_well_owned_by(db, record_id, org.id)
    if well is None:
        # Same 404 whether the record doesn't exist or belongs to another
        # organization -- no existence leak across orgs.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return build_record_response(well)
