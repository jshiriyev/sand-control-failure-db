"""Turns a validated RecordIngest payload into ORM rows in one transaction,
and reconstructs the nested shape back out for GET /records/{id}.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.app.schemas.ingest import RecordIngest
from backend.app.schemas.record_out import CompletionIntervalOut, ProductionIntervalOut, RecordOut
from db.mapping import build_record_out, flatten_bucket
from db.models import CompletionInterval, Organization, ProductionInterval, Well


def create_record(db: Session, org: Organization, payload: RecordIngest) -> Well:
    """One DB transaction: well -> its production_intervals -> their
    completion_intervals, `ordinal` set to submission order at each level.
    """
    well = Well(
        organization_id=org.id,
        submitted_at=payload.generated_at,
        raw_payload=payload.model_dump(mode="json"),
        **flatten_bucket(payload.well, scope="well"),
    )
    db.add(well)
    db.flush()  # assigns well.id for the FKs below

    for prod_ordinal, prod_payload in enumerate(payload.production_intervals, start=1):
        production_interval = ProductionInterval(
            well_id=well.id,
            ordinal=prod_ordinal,
            **flatten_bucket(prod_payload.fields, scope="production_interval"),
        )
        db.add(production_interval)
        db.flush()  # assigns production_interval.id

        for comp_ordinal, comp_bucket in enumerate(prod_payload.completion_intervals, start=1):
            completion_interval = CompletionInterval(
                production_interval_id=production_interval.id,
                ordinal=comp_ordinal,
                **flatten_bucket(comp_bucket, scope="completion_interval"),
            )
            db.add(completion_interval)

    db.commit()
    db.refresh(well)
    return well


def get_well_owned_by(db: Session, record_id: int, organization_id: int) -> Well | None:
    return db.query(Well).filter_by(id=record_id, organization_id=organization_id).first()


_WELL_STRUCTURAL_COLUMNS = {"id", "organization_id", "created_at", "updated_at", "submitted_at", "raw_payload"}
_PRODUCTION_STRUCTURAL_COLUMNS = {"id", "well_id", "ordinal", "created_at", "updated_at"}
_COMPLETION_STRUCTURAL_COLUMNS = {"id", "production_interval_id", "ordinal", "created_at", "updated_at"}


def _row_columns(row: Any, exclude: set[str]) -> dict[str, Any]:
    return {c.name: getattr(row, c.name) for c in row.__table__.columns if c.name not in exclude}


def build_record_response(well: Well) -> RecordOut:
    """Inverse of create_record: reads the ORM row tree back into the same
    nested Category -> Subcategory -> Parameter -> value shape the form
    exports, via db.mapping.build_record_out().
    """
    production_intervals_out = []
    for pi in well.production_intervals:
        completion_intervals_out = [
            CompletionIntervalOut(
                ordinal=ci.ordinal,
                fields=build_record_out(_row_columns(ci, _COMPLETION_STRUCTURAL_COLUMNS), scope="completion_interval"),
            )
            for ci in pi.completion_intervals
        ]
        production_intervals_out.append(
            ProductionIntervalOut(
                ordinal=pi.ordinal,
                fields=build_record_out(_row_columns(pi, _PRODUCTION_STRUCTURAL_COLUMNS), scope="production_interval"),
                completion_intervals=completion_intervals_out,
            )
        )
    return RecordOut(
        id=well.id,
        organization_id=well.organization_id,
        created_at=well.created_at,
        submitted_at=well.submitted_at,
        well=build_record_out(_row_columns(well, _WELL_STRUCTURAL_COLUMNS), scope="well"),
        production_intervals=production_intervals_out,
    )
