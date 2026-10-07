from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.farms.router import owned_farm
from app.plots.schemas import PlotCreate, PlotPublic, PlotUpdate
from app.users.auth import AuthContext, require_auth
from db import Farm, Plot, get_db, utc_now

router = APIRouter(prefix="/api/v1", tags=["plots"])


def owned_plot(plot_id: UUID, owner_id: str, session: Session) -> Plot:
    plot = session.scalar(
        select(Plot)
        .join(Farm, Plot.farm_id == Farm.id)
        .where(Plot.id == str(plot_id), Farm.owner_id == owner_id)
    )
    if plot is None:
        raise HTTPException(status_code=404, detail="Plot not found.")
    return plot


@router.post("/farms/{farm_id}/plots", response_model=PlotPublic, status_code=201)
def create_plot(
    farm_id: UUID,
    payload: PlotCreate,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> Plot:
    farm = owned_farm(farm_id, auth.user.id, session)
    now = utc_now()
    plot = Plot(**payload.model_dump(), farm_id=farm.id, created_at=now, updated_at=now)
    session.add(plot)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Plot name or code already exists.") from error
    session.refresh(plot)
    return plot


@router.get("/farms/{farm_id}/plots", response_model=list[PlotPublic])
def list_plots(
    farm_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> list[Plot]:
    farm = owned_farm(farm_id, auth.user.id, session)
    return list(
        session.scalars(
            select(Plot)
            .where(Plot.farm_id == farm.id)
            .order_by(Plot.created_at.desc(), Plot.id)
        )
    )


@router.get("/plots/{plot_id}", response_model=PlotPublic)
def get_plot(
    plot_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> Plot:
    return owned_plot(plot_id, auth.user.id, session)


@router.patch("/plots/{plot_id}", response_model=PlotPublic)
def update_plot(
    plot_id: UUID,
    payload: PlotUpdate,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> Plot:
    plot = owned_plot(plot_id, auth.user.id, session)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return plot

    for field, value in changes.items():
        setattr(plot, field, value)
    plot.updated_at = utc_now()
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Plot name or code already exists.") from error
    session.refresh(plot)
    return plot


@router.delete("/plots/{plot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plot(
    plot_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> None:
    plot = owned_plot(plot_id, auth.user.id, session)
    session.delete(plot)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Plot has dependent records.") from error
