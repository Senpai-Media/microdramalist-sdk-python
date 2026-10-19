"""The exceptions the clients raise.

Every non-2xx answer becomes a MicroDramaListError carrying the HTTP status
and the API's own ``error`` message (the API answers ``{"error": "..."}`` in
English, except the RSS feed, whose errors are plain text); the common
statuses get a subclass to catch.
"""

from __future__ import annotations

from typing import Optional

from .types import RateLimit


class MicroDramaListError(Exception):
    """Any error answer from the API, or a network failure (status 0)."""

    def __init__(self, message: str, status: int, rate_limit: Optional[RateLimit] = None) -> None:
        super().__init__(message)
        self.message = message
        #: The HTTP status; 0 when the request never got an answer.
        self.status = status
        #: The rate-limit headers of the failed response, when it had them.
        self.rate_limit = rate_limit


class BadRequestError(MicroDramaListError):
    """400: a parameter was refused; the message names it and what it accepts."""


class AuthenticationError(MicroDramaListError):
    """401: no token, or an unknown, revoked or disabled one.

    Also raised before any request when a data endpoint is called on a
    client without a token.
    """


class NotFoundError(MicroDramaListError):
    """404: no published drama with this id, or no chart for this week."""


class RateLimitError(MicroDramaListError):
    """429: over the per-minute or per-day limit.

    ``retry_after`` is the seconds the server asked to wait (until UTC
    the window's end for the hourly limit, up to an hour).
    """

    def __init__(self, message: str, retry_after: Optional[int], rate_limit: Optional[RateLimit]) -> None:
        super().__init__(message, 429, rate_limit)
        self.retry_after = retry_after
