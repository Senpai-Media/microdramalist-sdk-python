"""The MicroDramaList API clients, synchronous and asynchronous.

One method per operation in spec/openapi.yaml, named by its operationId in
snake_case, plus iterators for the paged and the since-based endpoints. Both
clients share _Base (the token, URLs, parameters, errors and the retry
rule); only the waiting and the I/O differ, so the two method lists below
are deliberately parallel -- tests/test_spec.py runs every spec example
through both.

Two kinds of endpoint (the spec's description):
  free -- get_drama, search_dramas, request_show, new_dramas_feed: no token,
          limited per address (30 a minute for reads);
  data -- everything else: a personal token from
          https://microdramalist.com/settings#api-tokens, sent as
          ``Authorization: Bearer mdl_...``; 60 a minute and 10,000 a UTC
          day per token.
The spec's one other operation, requestPlatform, needs the site's browser
sign-in cookie rather than a token, so it is left out on purpose.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import date, datetime, timezone
from typing import Any, AsyncIterator, Dict, Iterator, List, Mapping, Optional, Set, Tuple, Union
from urllib.parse import quote

import httpx

from ._errors import (
    AuthenticationError,
    BadRequestError,
    MicroDramaListError,
    NotFoundError,
    RateLimitError,
)
from ._version import __version__
from .types import (
    ChangeEvent,
    ChangesResponse,
    ChartWeekResponse,
    ChartWeeksResponse,
    Drama,
    DramaChartResponse,
    DramasResponse,
    GenresResponse,
    Interval,
    ListedDrama,
    MatchesResponse,
    NewDramasResponse,
    PlatformsResponse,
    RateLimit,
    SearchResult,
    ShowRequestReply,
    TagSource,
    TimelineResponse,
    WatchResponse,
)

DEFAULT_BASE_URL = "https://microdramalist.com"
"""The API's one origin; absolute URLs in responses always use it."""

TOKEN_ENV = "MICRODRAMALIST_TOKEN"
"""The environment variable read when no token is passed."""

Since = Union[str, datetime, date, None]  # noqa: UP007 -- kept in step with types.py's typing style


def _int_header(headers: httpx.Headers, name: str) -> Optional[int]:
    value = headers.get(name)
    if value is None or not value.strip():
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _rate_limit(headers: httpx.Headers) -> Optional[RateLimit]:
    rl: RateLimit = {
        "limit": _int_header(headers, "X-RateLimit-Limit"),
        "remaining": _int_header(headers, "X-RateLimit-Remaining"),
        "reset": _int_header(headers, "X-RateLimit-Reset"),
        "dailyLimit": _int_header(headers, "X-RateLimit-Daily-Limit"),
        "dailyRemaining": _int_header(headers, "X-RateLimit-Daily-Remaining"),
    }
    return None if all(v is None for v in rl.values()) else rl


def _since(value: Since) -> Optional[str]:
    """A since parameter as the API reads it: an ISO 8601 time or date."""
    if isinstance(value, datetime):
        # A naive datetime is taken as UTC, the API's clock.
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _error_message(response: httpx.Response) -> str:
    """The API's ``error`` message, or the text body (the feed), or the status line."""
    try:
        body = response.json()
        if isinstance(body, dict) and isinstance(body.get("error"), str):
            return body["error"]
    except ValueError:
        pass  # Not JSON: the feed answers errors as plain text.
    return response.text.strip() or f"HTTP {response.status_code} {response.reason_phrase}".strip()


_ChangeKey = Tuple[str, str, Optional[str], str]


def _change_key(e: ChangeEvent) -> _ChangeKey:
    return (e["type"], e["id"], e.get("platform"), e["at"])


def _path_id(value: str) -> str:
    return quote(value, safe="")


class _Base:
    """What both clients share: configuration, request building, errors, retries."""

    def __init__(
        self,
        token: Optional[str],
        base_url: Optional[str],
        max_retries: int,
        max_retry_wait: float,
    ) -> None:
        self._token = token if token is not None else (os.environ.get(TOKEN_ENV) or None)
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._max_retries = max_retries
        self._max_retry_wait = max_retry_wait
        #: The rate-limit headers of the last answer, or None before the
        #: first request or when it carried none.
        self.last_rate_limit: Optional[RateLimit] = None

    @property
    def has_token(self) -> bool:
        """Whether the client has a token, so the data endpoints can be called."""
        return bool(self._token)

    def _headers(self, auth: bool, text: bool) -> Dict[str, str]:
        if auth and not self._token:
            raise AuthenticationError(
                f"this endpoint needs an API token: create one at {DEFAULT_BASE_URL}/settings#api-tokens "
                f"and pass it as MicroDramaList(token=...) or set {TOKEN_ENV}",
                401,
            )
        headers = {
            "Accept": "application/rss+xml, text/plain" if text else "application/json",
            "User-Agent": f"microdramalist-python/{__version__}",
        }
        if auth:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    @staticmethod
    def _params(query: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
        # Empty means "all" to the API, so it is the same as leaving it out.
        return {k: v for k, v in (query or {}).items() if v is not None and v != ""}

    def _retry_after(self, response: httpx.Response, attempt: int) -> Optional[float]:
        """Seconds to wait before retrying a 429, or None to raise instead."""
        retry_after = _int_header(response.headers, "Retry-After")
        if attempt < self._max_retries and retry_after is not None and retry_after <= self._max_retry_wait:
            # Retry-After is whole seconds; a little over, so the window has turned.
            return retry_after + 0.25
        return None

    def _result(self, response: httpx.Response, text: bool) -> Any:
        rate_limit = _rate_limit(response.headers)
        self.last_rate_limit = rate_limit
        if response.is_success:
            return response.text if text else response.json()
        message = _error_message(response)
        status = response.status_code
        if status == 429:
            raise RateLimitError(message, _int_header(response.headers, "Retry-After"), rate_limit)
        cls = {400: BadRequestError, 401: AuthenticationError, 404: NotFoundError}.get(status, MicroDramaListError)
        raise cls(message, status, rate_limit)


class MicroDramaList(_Base):
    """The synchronous client.

    >>> mdl = MicroDramaList()                    # token from MICRODRAMALIST_TOKEN
    >>> mdl.search_dramas("billionaire")[0]["title"]

    Use it as a context manager (or call close()) to release its connections.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        max_retry_wait: float = 60.0,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        """Create a client.

        token: a personal API token (``mdl_...``); defaults to the
            MICRODRAMALIST_TOKEN environment variable. Only the data
            endpoints need it.
        max_retries: how many times a 429 is retried after waiting its
            Retry-After (0 turns retries off).
        max_retry_wait: the longest Retry-After, in seconds, worth waiting
            for; a longer one (the daily limit waits until UTC midnight)
            raises RateLimitError at once.
        http_client: an httpx.Client of your own (proxies, transports);
            it should follow redirects, as the default one does.
        """
        super().__init__(token, base_url, max_retries, max_retry_wait)
        self._owns_client = http_client is None
        # follow_redirects: an id merged into another drama answers 301 to it.
        self._http = http_client or httpx.Client(timeout=timeout, follow_redirects=True)

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    def __enter__(self) -> MicroDramaList:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Mapping[str, Any]] = None,
        json: Any = None,
        auth: bool = False,
        text: bool = False,
    ) -> Any:
        headers = self._headers(auth, text)
        attempt = 0
        while True:
            try:
                response = self._http.request(
                    method, self.base_url + path, params=self._params(query), json=json, headers=headers
                )
            except httpx.HTTPError as exc:
                raise MicroDramaListError(f"request to {path} failed: {exc}", 0) from exc
            wait = self._retry_after(response, attempt) if response.status_code == 429 else None
            if wait is None:
                return self._result(response, text)
            self.last_rate_limit = _rate_limit(response.headers)
            time.sleep(wait)
            attempt += 1

    # ---------------------------------------------------------------- free

    def get_drama(self, id: str) -> Drama:
        """One drama by its public id (``mdid-...``). An id merged into another drama answers that drama."""
        return self._request("GET", f"/api/v1/dramas/{_path_id(id)}")

    def search_dramas(self, q: str) -> List[SearchResult]:
        """Up to 20 published dramas whose title contains ``q``, or an exact lookup of an ``mdid-`` id."""
        return self._request("GET", "/api/v1/search", query={"q": q})

    def request_show(self, url: str) -> ShowRequestReply:
        """Ask MicroDramaList to add a show by its page URL on an app it covers (20 an hour per address)."""
        return self._request("POST", "/api/v1/show-requests", json={"url": url})

    def new_dramas_feed(
        self, *, platform: Optional[str] = None, genre: Optional[str] = None, language: Optional[str] = None
    ) -> str:
        """New dramas of the last 7 days as RSS 2.0 XML (a string). Free."""
        query = {"platform": platform, "genre": genre, "language": language}
        return self._request("GET", "/feeds/new.xml", query=query, text=True)

    # ----------------------------------------------------- catalogue stats

    def get_stats_platforms(self) -> PlatformsResponse:
        """Every app tracked, with its size, largest first. Token."""
        return self._request("GET", "/api/v1/stats/platforms", auth=True)

    def get_stats_genres(
        self, *, platform: Optional[str] = None, language: Optional[str] = None, tags: Optional[TagSource] = None
    ) -> GenresResponse:
        """Stories per genre tag in a scope, the 200 largest. Token."""
        query = {"platform": platform, "language": language, "tags": tags}
        return self._request("GET", "/api/v1/stats/genres", query=query, auth=True)

    def get_stats_timeline(
        self,
        *,
        genre: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        tags: Optional[TagSource] = None,
        interval: Optional[Interval] = None,
    ) -> TimelineResponse:
        """A genre, or a whole app, over time: snapshots and firstSeen. Token."""
        query = {"genre": genre, "platform": platform, "language": language, "tags": tags, "interval": interval}
        return self._request("GET", "/api/v1/stats/timeline", query=query, auth=True)

    # -------------------------------------------------------------- dramas

    def list_dramas(
        self,
        *,
        genre: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        sort: Optional[str] = None,
        page: Optional[int] = None,
    ) -> DramasResponse:
        """One page (50) of published dramas; ``sort`` is ``new`` (default) or ``popular``. Token."""
        query = {"genre": genre, "platform": platform, "language": language, "sort": sort, "page": page}
        return self._request("GET", "/api/v1/dramas", query=query, auth=True)

    def iter_dramas(
        self,
        *,
        genre: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        sort: Optional[str] = None,
    ) -> Iterator[ListedDrama]:
        """Every drama list_dramas would page through (up to page 200). Token."""
        page: Optional[int] = 1
        while page is not None:
            res = self.list_dramas(genre=genre, platform=platform, language=language, sort=sort, page=page)
            yield from res["dramas"]
            page = res["nextPage"]

    def list_new_dramas(
        self,
        *,
        genre: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        days: Optional[int] = None,
        page: Optional[int] = None,
    ) -> NewDramasResponse:
        """One page (50) of dramas first seen in the last ``days`` (1 to 31, default 7). Token."""
        query = {"genre": genre, "platform": platform, "language": language, "days": days, "page": page}
        return self._request("GET", "/api/v1/new", query=query, auth=True)

    def iter_new_dramas(
        self,
        *,
        genre: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        days: Optional[int] = None,
    ) -> Iterator[ListedDrama]:
        """Every drama list_new_dramas would page through. Token."""
        page: Optional[int] = 1
        while page is not None:
            res = self.list_new_dramas(genre=genre, platform=platform, language=language, days=days, page=page)
            yield from res["dramas"]
            page = res["nextPage"]

    def list_changes(self, *, since: Since = None) -> ChangesResponse:
        """Dramas created, updated and pulled since a time (default 24 hours ago, at most 31 days
        back), oldest first, up to 1,000 a call. Token."""
        return self._request("GET", "/api/v1/changes", query={"since": _since(since)}, auth=True)

    def iter_changes(self, *, since: Since = None) -> Iterator[ChangeEvent]:
        """Every change since a time, following ``next`` until ``complete``. Token.

        A call starts at its ``since`` inclusively, so the events at the
        boundary time come back on the next call too; they are yielded once.
        """
        cursor: Since = since
        boundary: Set[_ChangeKey] = set()
        while True:
            res = self.list_changes(since=cursor)
            fresh = [e for e in res["events"] if _change_key(e) not in boundary]
            yield from fresh
            # Done, or no progress (a full page all at the boundary time):
            # stop rather than ask for the same page forever.
            if res["complete"] or not fresh:
                return
            boundary = {_change_key(e) for e in res["events"] if e["at"] == res["next"]}
            cursor = res["next"]

    def get_drama_watch(self, id: str) -> WatchResponse:
        """Where to watch a drama: every live listing of it and of its versions. Token."""
        return self._request("GET", f"/api/v1/dramas/{_path_id(id)}/watch", auth=True)

    def get_drama_matches(self, id: str) -> MatchesResponse:
        """One show across apps: its versions and each one's listings. Token."""
        return self._request("GET", f"/api/v1/dramas/{_path_id(id)}/matches", auth=True)

    # -------------------------------------------------------------- charts

    def get_drama_chart(self, id: str) -> DramaChartResponse:
        """A drama's history on the weekly Top 20. Token."""
        return self._request("GET", f"/api/v1/dramas/{_path_id(id)}/chart", auth=True)

    def list_chart_weeks(self) -> ChartWeeksResponse:
        """Every frozen week of the Top 20, newest first. Token."""
        return self._request("GET", "/api/v1/charts/weekly", auth=True)

    def get_chart_week(self, week: str = "latest") -> ChartWeekResponse:
        """One week's Top 20: an ISO week such as ``2026-W40``, or ``latest`` (the default). Token."""
        return self._request("GET", f"/api/v1/charts/weekly/{_path_id(week)}", auth=True)


class AsyncMicroDramaList(_Base):
    """The asynchronous client: the same methods as MicroDramaList, awaited.

    >>> async with AsyncMicroDramaList() as mdl:
    ...     chart = await mdl.get_chart_week()
    """

    def __init__(
        self,
        token: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        max_retry_wait: float = 60.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """Create a client; the arguments are MicroDramaList's."""
        super().__init__(token, base_url, max_retries, max_retry_wait)
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def __aenter__(self) -> AsyncMicroDramaList:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Mapping[str, Any]] = None,
        json: Any = None,
        auth: bool = False,
        text: bool = False,
    ) -> Any:
        headers = self._headers(auth, text)
        attempt = 0
        while True:
            try:
                response = await self._http.request(
                    method, self.base_url + path, params=self._params(query), json=json, headers=headers
                )
            except httpx.HTTPError as exc:
                raise MicroDramaListError(f"request to {path} failed: {exc}", 0) from exc
            wait = self._retry_after(response, attempt) if response.status_code == 429 else None
            if wait is None:
                return self._result(response, text)
            self.last_rate_limit = _rate_limit(response.headers)
            await asyncio.sleep(wait)
            attempt += 1

    # ---------------------------------------------------------------- free

    async def get_drama(self, id: str) -> Drama:
        """One drama by its public id (``mdid-...``)."""
        return await self._request("GET", f"/api/v1/dramas/{_path_id(id)}")

    async def search_dramas(self, q: str) -> List[SearchResult]:
        """Up to 20 published dramas whose title contains ``q``, or an exact lookup of an ``mdid-`` id."""
        return await self._request("GET", "/api/v1/search", query={"q": q})

    async def request_show(self, url: str) -> ShowRequestReply:
        """Ask MicroDramaList to add a show by its page URL on an app it covers."""
        return await self._request("POST", "/api/v1/show-requests", json={"url": url})

    async def new_dramas_feed(
        self, *, platform: Optional[str] = None, genre: Optional[str] = None, language: Optional[str] = None
    ) -> str:
        """New dramas of the last 7 days as RSS 2.0 XML (a string). Free."""
        query = {"platform": platform, "genre": genre, "language": language}
        return await self._request("GET", "/feeds/new.xml", query=query, text=True)

    # ----------------------------------------------------- catalogue stats

    async def get_stats_platforms(self) -> PlatformsResponse:
        """Every app tracked, with its size, largest first. Token."""
        return await self._request("GET", "/api/v1/stats/platforms", auth=True)

    async def get_stats_genres(
        self, *, platform: Optional[str] = None, language: Optional[str] = None, tags: Optional[TagSource] = None
    ) -> GenresResponse:
        """Stories per genre tag in a scope, the 200 largest. Token."""
        query = {"platform": platform, "language": language, "tags": tags}
        return await self._request("GET", "/api/v1/stats/genres", query=query, auth=True)

    async def get_stats_timeline(
        self,
        *,
        genre: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        tags: Optional[TagSource] = None,
        interval: Optional[Interval] = None,
    ) -> TimelineResponse:
        """A genre, or a whole app, over time. Token."""
        query = {"genre": genre, "platform": platform, "language": language, "tags": tags, "interval": interval}
        return await self._request("GET", "/api/v1/stats/timeline", query=query, auth=True)

    # -------------------------------------------------------------- dramas

    async def list_dramas(
        self,
        *,
        genre: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        sort: Optional[str] = None,
        page: Optional[int] = None,
    ) -> DramasResponse:
        """One page (50) of published dramas. Token."""
        query = {"genre": genre, "platform": platform, "language": language, "sort": sort, "page": page}
        return await self._request("GET", "/api/v1/dramas", query=query, auth=True)

    async def iter_dramas(
        self,
        *,
        genre: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        sort: Optional[str] = None,
    ) -> AsyncIterator[ListedDrama]:
        """Every drama list_dramas would page through. Token."""
        page: Optional[int] = 1
        while page is not None:
            res = await self.list_dramas(genre=genre, platform=platform, language=language, sort=sort, page=page)
            for drama in res["dramas"]:
                yield drama
            page = res["nextPage"]

    async def list_new_dramas(
        self,
        *,
        genre: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        days: Optional[int] = None,
        page: Optional[int] = None,
    ) -> NewDramasResponse:
        """One page (50) of dramas first seen in the last ``days``. Token."""
        query = {"genre": genre, "platform": platform, "language": language, "days": days, "page": page}
        return await self._request("GET", "/api/v1/new", query=query, auth=True)

    async def iter_new_dramas(
        self,
        *,
        genre: Optional[str] = None,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        days: Optional[int] = None,
    ) -> AsyncIterator[ListedDrama]:
        """Every drama list_new_dramas would page through. Token."""
        page: Optional[int] = 1
        while page is not None:
            res = await self.list_new_dramas(genre=genre, platform=platform, language=language, days=days, page=page)
            for drama in res["dramas"]:
                yield drama
            page = res["nextPage"]

    async def list_changes(self, *, since: Since = None) -> ChangesResponse:
        """Dramas created, updated and pulled since a time. Token."""
        return await self._request("GET", "/api/v1/changes", query={"since": _since(since)}, auth=True)

    async def iter_changes(self, *, since: Since = None) -> AsyncIterator[ChangeEvent]:
        """Every change since a time, following ``next`` until ``complete``; boundary events once. Token."""
        cursor: Since = since
        boundary: Set[_ChangeKey] = set()
        while True:
            res = await self.list_changes(since=cursor)
            fresh = [e for e in res["events"] if _change_key(e) not in boundary]
            for event in fresh:
                yield event
            if res["complete"] or not fresh:
                return
            boundary = {_change_key(e) for e in res["events"] if e["at"] == res["next"]}
            cursor = res["next"]

    async def get_drama_watch(self, id: str) -> WatchResponse:
        """Where to watch a drama. Token."""
        return await self._request("GET", f"/api/v1/dramas/{_path_id(id)}/watch", auth=True)

    async def get_drama_matches(self, id: str) -> MatchesResponse:
        """One show across apps. Token."""
        return await self._request("GET", f"/api/v1/dramas/{_path_id(id)}/matches", auth=True)

    # -------------------------------------------------------------- charts

    async def get_drama_chart(self, id: str) -> DramaChartResponse:
        """A drama's history on the weekly Top 20. Token."""
        return await self._request("GET", f"/api/v1/dramas/{_path_id(id)}/chart", auth=True)

    async def list_chart_weeks(self) -> ChartWeeksResponse:
        """Every frozen week of the Top 20, newest first. Token."""
        return await self._request("GET", "/api/v1/charts/weekly", auth=True)

    async def get_chart_week(self, week: str = "latest") -> ChartWeekResponse:
        """One week's Top 20 (``latest`` by default). Token."""
        return await self._request("GET", f"/api/v1/charts/weekly/{_path_id(week)}", auth=True)
