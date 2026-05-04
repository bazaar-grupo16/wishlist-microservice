"""
Wishlist API router — /items.
"""

import uuid

from fastapi import APIRouter, Depends, status

from src.core.dependencies import DbSession, UserID, get_catalog_client
from src.exceptions import WishlistItemAlreadyExistsError, WishlistItemNotFoundError
from src.schemas import (
    AddItemRequest,
    CheckItemResponse,
    WishlistItemCreatedResponse,
    WishlistItemDetail,
    WishlistListResponse,
)
from src.services import WishlistService

router = APIRouter(tags=["wishlist"])


def _service(catalog_client=Depends(get_catalog_client)) -> WishlistService:
    return WishlistService(catalog_client)


@router.post(
    "/items",
    response_model=WishlistItemCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_item(
    body: AddItemRequest,
    db: DbSession,
    user_id: UserID,
    service: WishlistService = Depends(_service),
):
    from fastapi import HTTPException

    try:
        item = service.add_item(db, user_id, body.product_id)
    except WishlistItemAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Item already in wishlist")
    return item


@router.delete(
    "/items/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_item(
    product_id: uuid.UUID,
    db: DbSession,
    user_id: UserID,
    service: WishlistService = Depends(_service),
):
    from fastapi import HTTPException

    try:
        service.remove_item(db, user_id, product_id)
    except WishlistItemNotFoundError:
        raise HTTPException(status_code=404, detail="Item not found in wishlist")


@router.get("/items", response_model=WishlistListResponse)
def list_items(
    db: DbSession,
    user_id: UserID,
    service: WishlistService = Depends(_service),
):
    items = service.get_wishlist(db, user_id)
    return WishlistListResponse(
        items=[WishlistItemDetail(**i) for i in items],
        total=len(items),
    )


@router.get("/items/{product_id}/check", response_model=CheckItemResponse)
def check_item(
    product_id: uuid.UUID,
    db: DbSession,
    user_id: UserID,
    service: WishlistService = Depends(_service),
):
    return CheckItemResponse(in_wishlist=service.check_item(db, user_id, product_id))
