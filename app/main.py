from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.crop_seasons.router import router as crop_seasons_router
from app.farms.router import router as farms_router
from app.operations.router import router as operations_router
from app.plots.router import router as plots_router
from app.reminders.router import router as reminders_router
from app.users.router import router as users_router
from db import engine

app = FastAPI(title="Farm Management API", version="0.1.0")
app.include_router(users_router)
app.include_router(farms_router)
app.include_router(plots_router)
app.include_router(crop_seasons_router)
app.include_router(operations_router)
app.include_router(reminders_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from error

    return {"status": "ok", "database": "connected"}
