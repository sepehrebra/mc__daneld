from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crop_seasons.schemas import valid_date
from app.operations.schemas import OperationCreate, OperationPublic
from app.plots.router import owned_plot
from app.users.auth import AuthContext, require_auth
from db import CropSeason, Farm, Operation, Plot, get_db, utc_now

router = APIRouter(prefix="/api/v1", tags=["operations"])


def owned_operation(operation_id: UUID, owner_id: str, session: Session) -> Operation:
    operation = session.scalar(
        select(Operation)
        .join(Plot, Operation.plot_id == Plot.id)
        .join(Farm, Plot.farm_id == Farm.id)
        .where(Operation.id == str(operation_id), Farm.owner_id == owner_id)
    )
    if operation is None:
        raise HTTPException(status_code=404, detail="Operation not found.")
    return operation


def checked_date_range(date_from: str | None, date_to: str | None) -> tuple[str | None, str | None]:
    try:
        start = valid_date(date_from)
        end = valid_date(date_to)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=422, detail="date_from cannot exceed date_to.")
    return start, end


def operation_list(
    session: Session,
    owner_id: str,
    *,
    plot_id: str | None,
    date_from: str | None,
    date_to: str | None,
) -> list[Operation]:
    start, end = checked_date_range(date_from, date_to)
    query = (
        select(Operation)
        .join(Plot, Operation.plot_id == Plot.id)
        .join(Farm, Plot.farm_id == Farm.id)
        .where(Farm.owner_id == owner_id)
    )
    if plot_id is not None:
        query = query.where(Operation.plot_id == plot_id)
    if start is not None:
        query = query.where(Operation.scheduled_date >= start)
    if end is not None:
        query = query.where(Operation.scheduled_date <= end)
    return list(
        session.scalars(
            query.order_by(Operation.scheduled_date, Operation.scheduled_time, Operation.id)
        )
    )


@router.post("/plots/{plot_id}/operations", response_model=OperationPublic, status_code=201)
def create_operation(
    plot_id: UUID,
    payload: OperationCreate,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> Operation:
    plot = owned_plot(plot_id, auth.user.id, session)
    if payload.crop_season_id is not None:
        season_id = session.scalar(
            select(CropSeason.id).where(
                CropSeason.id == str(payload.crop_season_id), CropSeason.plot_id == plot.id
            )
        )
        if season_id is None:
            raise HTTPException(status_code=422, detail="Crop season does not belong to plot.")

    now = utc_now()
    operation = Operation(
        **payload.model_dump(exclude={"crop_season_id"}),
        plot_id=plot.id,
        crop_season_id=str(payload.crop_season_id) if payload.crop_season_id else None,
        created_by=auth.user.id,
        status="planned",
        created_at=now,
        updated_at=now,
    )
    session.add(operation)
    session.commit()
    session.refresh(operation)
    return operation


@router.get("/plots/{plot_id}/operations", response_model=list[OperationPublic])
def list_plot_operations(
    plot_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[Operation]:
    plot = owned_plot(plot_id, auth.user.id, session)
    return operation_list(
        session,
        auth.user.id,
        plot_id=plot.id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/operations", response_model=list[OperationPublic])
def list_operations(
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
    plot_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[Operation]:
    if plot_id is not None:
        owned_plot(plot_id, auth.user.id, session)
    return operation_list(
        session,
        auth.user.id,
        plot_id=str(plot_id) if plot_id else None,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/operations/{operation_id}", response_model=OperationPublic)
def get_operation(
    operation_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> Operation:
    return owned_operation(operation_id, auth.user.id, session)
