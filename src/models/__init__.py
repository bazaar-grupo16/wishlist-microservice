"""
ORM models for the wishlist service.
"""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.core.utils import utc_now


class WishlistItem(Base):
    """A single product saved in a user's wishlist."""

    __tablename__ = "wishlist_items"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "user_id", "product_id", name="uq_wishlist_user_product"
        ),
    )
