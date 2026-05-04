"""
Repository layer for wishlist persistence.

All database operations live here. No HTTP, no business logic — just SQL.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.exceptions import WishlistItemAlreadyExistsError, WishlistItemNotFoundError
from src.models import WishlistItem


class WishlistRepository:
    def add(self, db: Session, user_id: uuid.UUID, product_id: uuid.UUID) -> WishlistItem:
        item = WishlistItem(user_id=user_id, product_id=product_id)
        db.add(item)
        try:
            db.commit()
            db.refresh(item)
        except IntegrityError:
            db.rollback()
            raise WishlistItemAlreadyExistsError
        return item

    def remove(self, db: Session, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
        item = db.scalar(
            select(WishlistItem).where(
                WishlistItem.user_id == user_id,
                WishlistItem.product_id == product_id,
            )
        )
        if item is None:
            raise WishlistItemNotFoundError
        db.delete(item)
        db.commit()

    def list_by_user(self, db: Session, user_id: uuid.UUID) -> list[WishlistItem]:
        return list(
            db.scalars(
                select(WishlistItem)
                .where(WishlistItem.user_id == user_id)
                .order_by(WishlistItem.added_at.desc())
            )
        )

    def exists(self, db: Session, user_id: uuid.UUID, product_id: uuid.UUID) -> bool:
        return db.scalar(
            select(WishlistItem).where(
                WishlistItem.user_id == user_id,
                WishlistItem.product_id == product_id,
            )
        ) is not None
