"""Turns a validated RecordIngest payload into ORM rows in one transaction,
and reconstructs the nested shape back out for GET /records/{id}.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.app.schemas.ingest import RecordIngest
from backend.app.schemas.record_out import CompletionIntervalOut, RecordOut, SandBodyOut
from db.mapping import build_record_out, flatten_bucket
from db.models import CompletionInterval, Organization, SandBody, Well


def create_record(db: Session, org: Organization, payload: RecordIngest) -> Well:
    """One DB transaction: well -> its completion_intervals -> their
    sand_bodies, `ordinal` set to submission order at each level.
    """
    well = Well(
        organization_id=org.id,
        submitted_at=payload.generated_at,
        raw_payload=payload.model_dump(mode="json"),
        **flatten_bucket(payload.well, scope="well"),
    )
    db.add(well)
    db.flush()  # assigns well.id for the FKs below

    for comp_ordinal, comp_payload in enumerate(payload.completion_intervals, start=1):
        completion_interval = CompletionInterval(
            well_id=well.id,
            ordinal=comp_ordinal,
            **flatten_bucket(comp_payload.fields, scope="completion_interval"),
        )
        db.add(completion_interval)
        db.flush()  # assigns completion_interval.id

        for sb_ordinal, sb_bucket in enumerate(comp_payload.sand_bodies, start=1):
            sand_body = SandBody(
                completion_interval_id=completion_interval.id,
                ordinal=sb_ordinal,
                **flatten_bucket(sb_bucket, scope="sand_body"),
            )
            db.add(sand_body)

    db.commit()
    db.refresh(well)
    return well


def get_well_owned_by(db: Session, record_id: int, organization_id: int) -> Well | None:
    return db.query(Well).filter_by(id=record_id, organization_id=organization_id).first()


_WELL_STRUCTURAL_COLUMNS = {"id", "organization_id", "created_at", "updated_at", "submitted_at", "raw_payload"}
_COMPLETION_STRUCTURAL_COLUMNS = {"id", "well_id", "ordinal", "created_at", "updated_at"}
_SAND_BODY_STRUCTURAL_COLUMNS = {"id", "completion_interval_id", "ordinal", "created_at", "updated_at"}


def _row_columns(row: Any, exclude: set[str]) -> dict[str, Any]:
    return {c.name: getattr(row, c.name) for c in row.__table__.columns if c.name not in exclude}


def build_record_response(well: Well) -> RecordOut:
    """Inverse of create_record: reads the ORM row tree back into the same
    nested Category -> Subcategory -> Parameter -> value shape the form
    exports, via db.mapping.build_record_out().
    """
    completion_intervals_out = []
    for ci in well.completion_intervals:
        sand_bodies_out = [
            SandBodyOut(
                ordinal=sb.ordinal,
                fields=build_record_out(_row_columns(sb, _SAND_BODY_STRUCTURAL_COLUMNS), scope="sand_body"),
            )
            for sb in ci.sand_bodies
        ]
        completion_intervals_out.append(
            CompletionIntervalOut(
                ordinal=ci.ordinal,
                fields=build_record_out(_row_columns(ci, _COMPLETION_STRUCTURAL_COLUMNS), scope="completion_interval"),
                sand_bodies=sand_bodies_out,
            )
        )
    return RecordOut(
        id=well.id,
        organization_id=well.organization_id,
        created_at=well.created_at,
        submitted_at=well.submitted_at,
        well=build_record_out(_row_columns(well, _WELL_STRUCTURAL_COLUMNS), scope="well"),
        completion_intervals=completion_intervals_out,
    )
