"""The MicroDramaList API client for Python.

>>> from microdramalist import MicroDramaList
>>> mdl = MicroDramaList()            # token from MICRODRAMALIST_TOKEN
>>> mdl.get_chart_week()["entries"][0]["title"]

Getting a token: docs/getting-started.md, or
https://microdramalist.com/settings#api-tokens.
"""

from ._client import DEFAULT_BASE_URL, TOKEN_ENV, AsyncMicroDramaList, MicroDramaList
from ._errors import (
    AuthenticationError,
    BadRequestError,
    MicroDramaListError,
    NotFoundError,
    RateLimitError,
)
from ._version import __version__

__all__ = [
    "MicroDramaList",
    "AsyncMicroDramaList",
    "MicroDramaListError",
    "BadRequestError",
    "AuthenticationError",
    "NotFoundError",
    "RateLimitError",
    "DEFAULT_BASE_URL",
    "TOKEN_ENV",
    "__version__",
]
