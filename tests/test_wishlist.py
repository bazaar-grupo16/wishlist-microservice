"""
Integration tests for the wishlist endpoints.

All tests run against a real PostgreSQL instance — no mocking.
Each test uses fresh uuid4() values to avoid collisions between runs.
"""

import uuid

from fastapi.testclient import TestClient

from src.core.catalog_client import CatalogClient
from src.core.dependencies import get_catalog_client
from src.main import app


# ── helpers ────────────────────────────────────────────────────────────────

def _user_headers(user_id: uuid.UUID | None = None, invalid: bool = False) -> dict:
    if invalid:
        return {"X-User-ID": "not-a-uuid"}
    if user_id is None:
        user_id = uuid.uuid4()
    return {"X-User-ID": str(user_id)}


def _add(client: TestClient, user_id: uuid.UUID, product_id: uuid.UUID):
    return client.post(
        "/items",
        json={"product_id": str(product_id)},
        headers={"X-User-ID": str(user_id)},
    )


# ── POST /items ──────────────────────────────────────────────────────────────

class TestAddItem:
    def test_add_item_returns_201(self, client: TestClient) -> None:
        user_id = uuid.uuid4()
        product_id = uuid.uuid4()
        response = _add(client, user_id, product_id)
        assert response.status_code == 201
        body = response.json()
        assert body["product_id"] == str(product_id)
        assert body["user_id"] == str(user_id)
        assert "id" in body
        assert "added_at" in body

    def test_add_item_missing_user_header_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/items",
            json={"product_id": str(uuid.uuid4())},
        )
        assert response.status_code == 401

    def test_add_item_invalid_user_id_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/items",
            json={"product_id": str(uuid.uuid4())},
            headers={"X-User-ID": "not-a-uuid"},
        )
        assert response.status_code == 401

    def test_add_item_duplicate_returns_409(self, client: TestClient) -> None:
        user_id = uuid.uuid4()
        product_id = uuid.uuid4()
        _add(client, user_id, product_id)
        response = _add(client, user_id, product_id)
        assert response.status_code == 409


# ── DELETE /items/{product_id} ───────────────────────────────────────────────

class TestRemoveItem:
    def test_remove_item_returns_204(self, client: TestClient) -> None:
        user_id = uuid.uuid4()
        product_id = uuid.uuid4()
        _add(client, user_id, product_id)
        response = client.delete(
            f"/items/{product_id}",
            headers={"X-User-ID": str(user_id)},
        )
        assert response.status_code == 204

    def test_remove_item_not_found_returns_404(self, client: TestClient) -> None:
        user_id = uuid.uuid4()
        product_id = uuid.uuid4()
        response = client.delete(
            f"/items/{product_id}",
            headers={"X-User-ID": str(user_id)},
        )
        assert response.status_code == 404

    def test_remove_item_missing_user_header_returns_401(self, client: TestClient) -> None:
        response = client.delete(f"/items/{uuid.uuid4()}")
        assert response.status_code == 401

    def test_remove_item_only_removes_own_item(self, client: TestClient) -> None:
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        product_id = uuid.uuid4()
        _add(client, user_a, product_id)
        _add(client, user_b, product_id)

        # user_b removes the item from their own wishlist
        response = client.delete(
            f"/items/{product_id}",
            headers={"X-User-ID": str(user_b)},
        )
        assert response.status_code == 204

        # user_a still has the item
        check = client.get(
            f"/items/{product_id}/check",
            headers={"X-User-ID": str(user_a)},
        )
        assert check.json()["in_wishlist"] is True


# ── GET /items ────────────────────────────────────────────────────────────────

class TestListItems:
    def test_list_empty_wishlist(self, client: TestClient) -> None:
        response = client.get(
            "/items",
            headers={"X-User-ID": str(uuid.uuid4())},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_list_missing_user_header_returns_401(self, client: TestClient) -> None:
        response = client.get("/items")
        assert response.status_code == 401

    def test_list_catalog_unavailable_degraded_mode(self, client: TestClient) -> None:
        # Override the catalog client with one that points to an unreachable URL
        app.dependency_overrides[get_catalog_client] = lambda: CatalogClient(
            "http://localhost:0"
        )
        try:
            user_id = uuid.uuid4()
            _add(client, user_id, uuid.uuid4())
            response = client.get(
                "/items",
                headers={"X-User-ID": str(user_id)},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["total"] == 1
            item = body["items"][0]
            assert item["catalog_available"] is False
            assert item["name"] is None
        finally:
            app.dependency_overrides.pop(get_catalog_client, None)

    def test_list_catalog_available_maps_fields_correctly(self, client: TestClient) -> None:
        product_id = uuid.uuid4()

        class _FakeCatalogClient:
            def get_product(self, pid: str) -> dict:
                return {
                    "data": {
                        "id": pid,
                        "title": "Campera de cuero",
                        "price": 150.0,
                        "stock": 10,
                        "status": "active",
                        "images": ["https://cdn.example.com/img.jpg"],
                    }
                }

        app.dependency_overrides[get_catalog_client] = lambda: _FakeCatalogClient()
        try:
            user_id = uuid.uuid4()
            _add(client, user_id, product_id)
            response = client.get(
                "/items",
                headers={"X-User-ID": str(user_id)},
            )
            assert response.status_code == 200
            item = response.json()["items"][0]
            assert item["catalog_available"] is True
            assert item["name"] == "Campera de cuero"
            assert item["price"] == 150.0
            assert item["image_url"] == "https://cdn.example.com/img.jpg"
            assert item["in_stock"] is True
            assert item["is_available"] is True
        finally:
            app.dependency_overrides.pop(get_catalog_client, None)

    def test_list_only_returns_own_items(self, client: TestClient) -> None:
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        _add(client, user_a, uuid.uuid4())
        _add(client, user_a, uuid.uuid4())
        _add(client, user_b, uuid.uuid4())

        response = client.get(
            "/items",
            headers={"X-User-ID": str(user_a)},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        for item in body["items"]:
            assert item["user_id"] == str(user_a)


# ── GET /items/{product_id}/check ────────────────────────────────────────────

class TestCheckItem:
    def test_check_item_in_wishlist_returns_true(self, client: TestClient) -> None:
        user_id = uuid.uuid4()
        product_id = uuid.uuid4()
        _add(client, user_id, product_id)
        response = client.get(
            f"/items/{product_id}/check",
            headers={"X-User-ID": str(user_id)},
        )
        assert response.status_code == 200
        assert response.json()["in_wishlist"] is True

    def test_check_item_not_in_wishlist_returns_false(self, client: TestClient) -> None:
        user_id = uuid.uuid4()
        product_id = uuid.uuid4()
        response = client.get(
            f"/items/{product_id}/check",
            headers={"X-User-ID": str(user_id)},
        )
        assert response.status_code == 200
        assert response.json()["in_wishlist"] is False

    def test_check_item_missing_user_header_returns_401(self, client: TestClient) -> None:
        response = client.get(f"/items/{uuid.uuid4()}/check")
        assert response.status_code == 401

    def test_check_item_user_isolation(self, client: TestClient) -> None:
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        product_id = uuid.uuid4()
        _add(client, user_a, product_id)

        response = client.get(
            f"/items/{product_id}/check",
            headers={"X-User-ID": str(user_b)},
        )
        assert response.status_code == 200
        assert response.json()["in_wishlist"] is False
