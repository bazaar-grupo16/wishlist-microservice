"""
FastAPI dependencies for dependency injection.

Add shared dependencies here (e.g. database sessions, auth context).
"""

from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from src.core.catalog_client import CatalogClient
from src.core.config import get_settings
from src.core.database import SessionLocal


def _get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and ensure it is closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_user_id(x_user_id: Annotated[str | None, Header()] = None) -> UUID:
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="Missing X-User-ID header")
    try:
        return UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid X-User-ID header")


def get_catalog_client() -> CatalogClient:
    return CatalogClient(get_settings().CATALOG_SERVICE_URL)


# Re-usable annotated dependencies for route signatures.
DbSession = Annotated[Session, Depends(_get_db)]
UserID = Annotated[UUID, Depends(_get_user_id)]
