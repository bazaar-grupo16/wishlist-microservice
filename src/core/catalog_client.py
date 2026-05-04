"""
HTTP client for the catalog service.

Never raises — any error is logged and returns None so the wishlist
can still respond in degraded mode.
"""

import logging

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 3.0


class CatalogClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def get_product(self, product_id: str) -> dict | None:
        url = f"{self._base_url}/api/v1/products/{product_id}"
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.warning("catalog unavailable for product %s: %s", product_id, exc)
            return None
