"""
Service layer: orchestrates repository + catalog client.
"""

import uuid

from sqlalchemy.orm import Session

from src.core.catalog_client import CatalogClient
from src.models import WishlistItem
from src.repositories import WishlistRepository

_repo = WishlistRepository()


class WishlistService:
    def __init__(self, catalog_client: CatalogClient) -> None:
        self._catalog = catalog_client

    def add_item(self, db: Session, user_id: uuid.UUID, product_id: uuid.UUID) -> WishlistItem:
        return _repo.add(db, user_id, product_id)

    def remove_item(self, db: Session, user_id: uuid.UUID, product_id: uuid.UUID) -> None:
        _repo.remove(db, user_id, product_id)

    def check_item(self, db: Session, user_id: uuid.UUID, product_id: uuid.UUID) -> bool:
        return _repo.exists(db, user_id, product_id)

    def get_wishlist(self, db: Session, user_id: uuid.UUID) -> list[dict]:
        items = _repo.list_by_user(db, user_id)
        result = []
        for item in items:
            product = self._catalog.get_product(str(item.product_id))
            if product is not None:
                result.append({
                    "id": item.id,
                    "user_id": item.user_id,
                    "product_id": item.product_id,
                    "added_at": item.added_at,
                    "name": product.get("name"),
                    "price": product.get("price"),
                    "image_url": product.get("image_url"),
                    "in_stock": product.get("in_stock"),
                    "is_available": product.get("is_available"),
                    "catalog_available": True,
                })
            else:
                result.append({
                    "id": item.id,
                    "user_id": item.user_id,
                    "product_id": item.product_id,
                    "added_at": item.added_at,
                    "name": None,
                    "price": None,
                    "image_url": None,
                    "in_stock": None,
                    "is_available": None,
                    "catalog_available": False,
                })
        return result
