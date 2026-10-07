from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crop_seasons.schemas import (
    CropSeasonCreate,
    CropSeasonPublic,
    CropSeasonUpdate,
    validate_date_order,
)
from app.plots.router import owned_plot
from app.users.auth import AuthContext, require_auth
from db import CropSeason, Farm, Plot, get_db, utc_now

router = APIRouter(prefix="/api/v1", tags=["crop-seasons"])


def owned_season(season_id: UUID, owner_id: str, session: Session) -> CropSeason:
    season = session.scalar(
        select(CropSeason)
        .join(Plot, CropSeason.plot_id == Plot.id)
        .join(Farm, Plot.farm_id == Farm.id)
        .where(CropSeason.id == str(season_id), Farm.owner_id == owner_id)
    )
    if season is None:
        raise HTTPException(status_code=404, detail="Crop season not found.")
    return season


@router.post("/plots/{plot_id}/crop-seasons", response_model=CropSeasonPublic, status_code=201)
def create_season(
    plot_id: UUID,
    payload: CropSeasonCreate,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> CropSeason:
    plot = owned_plot(plot_id, auth.user.id, session)
    now = utc_now()
    season = CropSeason(
        **payload.model_dump(), plot_id=plot.id, created_at=now, updated_at=now
    )
    session.add(season)
    session.commit()
    session.refresh(season)
    return season


@router.get("/plots/{plot_id}/crop-seasons", response_model=list[CropSeasonPublic])
def list_seasons(
    plot_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> list[CropSeason]:
    plot = owned_plot(plot_id, auth.user.id, session)
    return list(
        session.scalars(
            select(CropSeason)
            .where(CropSeason.plot_id == plot.id)
            .order_by(CropSeason.start_date.desc(), CropSeason.id)
        )
    )


@router.get("/crop-seasons/{season_id}", response_model=CropSeasonPublic)
def get_season(
    season_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> CropSeason:
    return owned_season(season_id, auth.user.id, session)


@router.patch("/crop-seasons/{season_id}", response_model=CropSeasonPublic)
def update_season(
    season_id: UUID,
    payload: CropSeasonUpdate,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> CropSeason:
    season = owned_season(season_id, auth.user.id, session)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return season

    try:
        validate_date_order(
            changes.get("start_date", season.start_date),
            changes.get("expected_end_date", season.expected_end_date),
            changes.get("actual_start_date", season.actual_start_date),
            changes.get("actual_end_date", season.actual_end_date),
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    for field, value in changes.items():
        setattr(season, field, value)
    season.updated_at = utc_now()
    session.commit()
    session.refresh(season)
    return season


@router.delete("/crop-seasons/{season_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_season(
    season_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> None:
    season = owned_season(season_id, auth.user.id, session)
    session.delete(season)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Crop season has dependent records.") from error
