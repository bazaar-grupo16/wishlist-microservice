"""
Public exports for wishlist schemas.
"""

from src.schemas.wishlist import (
    AddItemRequest,
    CheckItemResponse,
    WishlistItemCreatedResponse,
    WishlistItemDetail,
    WishlistListResponse,
)

__all__ = [
    "AddItemRequest",
    "CheckItemResponse",
    "WishlistItemCreatedResponse",
    "WishlistItemDetail",
    "WishlistListResponse",
]
