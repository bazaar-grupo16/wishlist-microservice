"""
Pydantic schemas for request validation and response serialization.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class AddItemRequest(BaseModel):
    product_id: uuid.UUID


class WishlistItemCreatedResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    product_id: uuid.UUID
    added_at: datetime

    model_config = {"from_attributes": True}


class WishlistItemDetail(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    product_id: uuid.UUID
    added_at: datetime
    name: str | None = None
    price: float | None = None
    image_url: str | None = None
    in_stock: bool | None = None
    is_available: bool | None = None
    catalog_available: bool = False

    model_config = {"from_attributes": True}


class WishlistListResponse(BaseModel):
    items: list[WishlistItemDetail]
    total: int


class CheckItemResponse(BaseModel):
    in_wishlist: bool
