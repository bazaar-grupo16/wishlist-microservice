"""
Domain exceptions for the wishlist service.

These are raised by the repository and service layers and converted
to HTTP responses at the API layer — keeping business logic free of
HTTP concerns.
"""


class WishlistItemNotFoundError(Exception):
    """Raised when a wishlist item does not exist for the given user + product."""


class WishlistItemAlreadyExistsError(Exception):
    """Raised when the same product is added to a user's wishlist more than once."""
