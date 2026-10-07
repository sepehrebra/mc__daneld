from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.farms.schemas import FarmCreate, FarmPublic, FarmUpdate
from app.users.auth import AuthContext, require_auth
from db import Farm, get_db, utc_now

router = APIRouter(prefix="/api/v1/farms", tags=["farms"])


def owned_farm(farm_id: UUID, owner_id: str, session: Session) -> Farm:
    farm = session.scalar(
        select(Farm).where(Farm.id == str(farm_id), Farm.owner_id == owner_id)
    )
    if farm is None:
        raise HTTPException(status_code=404, detail="Farm not found.")
    return farm


@router.post("", response_model=FarmPublic, status_code=status.HTTP_201_CREATED)
def create_farm(
    payload: FarmCreate,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> Farm:
    now = utc_now()
    farm = Farm(**payload.model_dump(), owner_id=auth.user.id, created_at=now, updated_at=now)
    session.add(farm)
    session.commit()
    session.refresh(farm)
    return farm


@router.get("", response_model=list[FarmPublic])
def list_farms(
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> list[Farm]:
    return list(
        session.scalars(
            select(Farm)
            .where(Farm.owner_id == auth.user.id)
            .order_by(Farm.created_at.desc(), Farm.id)
        )
    )


@router.get("/{farm_id}", response_model=FarmPublic)
def get_farm(
    farm_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> Farm:
    return owned_farm(farm_id, auth.user.id, session)


@router.patch("/{farm_id}", response_model=FarmPublic)
def update_farm(
    farm_id: UUID,
    payload: FarmUpdate,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> Farm:
    farm = owned_farm(farm_id, auth.user.id, session)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return farm

    latitude = changes.get("latitude", farm.latitude)
    longitude = changes.get("longitude", farm.longitude)
    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=422, detail="Latitude and longitude must be provided together."
        )

    for field, value in changes.items():
        setattr(farm, field, value)
    farm.updated_at = utc_now()
    session.commit()
    session.refresh(farm)
    return farm


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm(
    farm_id: UUID,
    auth: Annotated[AuthContext, Depends(require_auth)],
    session: Annotated[Session, Depends(get_db)],
) -> None:
    farm = owned_farm(farm_id, auth.user.id, session)
    session.delete(farm)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Farm has dependent records.") from error
