"""The clients' behaviour around the calls: the token, errors, rate limits,
retries, redirects and the iterators. Offline, through the fake transport."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Dict, List

import httpx
import pytest

import microdramalist._client as client_module
from microdramalist import (
    AsyncMicroDramaList,
    AuthenticationError,
    BadRequestError,
    MicroDramaList,
    MicroDramaListError,
    NotFoundError,
    RateLimitError,
)

from .conftest import LICENSE, Answer, FakeAPI


def sync(fake: FakeAPI, **kw: Any) -> MicroDramaList:
    return MicroDramaList(http_client=fake.sync_client(), **kw)


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> List[float]:
    """Records the retry waits instead of sleeping them."""
    waits: List[float] = []
    monkeypatch.setattr(client_module.time, "sleep", waits.append)
    return waits


# ------------------------------------------------------------------- token


def test_sends_bearer_token_on_data_endpoints() -> None:
    fake = FakeAPI(Answer(body={"platforms": [], **LICENSE}))
    sync(fake, token="mdl_abc").get_stats_platforms()
    assert fake.calls[0].headers["Authorization"] == "Bearer mdl_abc"


def test_never_sends_token_to_free_endpoints() -> None:
    fake = FakeAPI(Answer(body=[]))
    sync(fake, token="mdl_abc").search_dramas("ceo")
    assert "Authorization" not in fake.calls[0].headers


def test_reads_token_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MICRODRAMALIST_TOKEN", "mdl_env")
    fake = FakeAPI(Answer(body={"weeks": [], **LICENSE}))
    mdl = sync(fake)
    assert mdl.has_token
    mdl.list_chart_weeks()
    assert fake.calls[0].headers["Authorization"] == "Bearer mdl_env"


def test_raises_before_request_without_token() -> None:
    fake = FakeAPI()
    with pytest.raises(AuthenticationError, match="settings#api-tokens"):
        sync(fake).get_stats_platforms()
    assert fake.calls == []


def test_free_endpoints_work_without_token() -> None:
    fake = FakeAPI(Answer(body=[]))
    assert sync(fake).search_dramas("ceo") == []


# ---------------------------------------------------------------- requests


def test_leaves_out_empty_and_none_parameters() -> None:
    fake = FakeAPI(Answer(body={"page": 1, "perPage": 50, "dramas": [], "nextPage": None, **LICENSE}))
    sync(fake, token="t").list_dramas(genre="", platform=None, language="eng")
    assert dict(fake.calls[0].url.params) == {"language": "eng"}


def test_encodes_path_segments() -> None:
    fake = FakeAPI(Answer(body={}))
    sync(fake).get_drama("mdid-a/b?c")
    assert fake.calls[0].url.raw_path == b"/api/v1/dramas/mdid-a%2Fb%3Fc"


@pytest.mark.parametrize(
    ("since", "sent"),
    [
        (datetime(2026, 10, 10, tzinfo=timezone.utc), "2026-10-10T00:00:00+00:00"),
        (datetime(2026, 10, 10), "2026-10-10T00:00:00+00:00"),  # naive = UTC
        (date(2026, 10, 10), "2026-10-10"),
        ("2026-10-10T00:00:00Z", "2026-10-10T00:00:00Z"),
    ],
)
def test_since_formats(since: Any, sent: str) -> None:
    fake = FakeAPI(Answer(body={"since": "", "events": [], "next": "", "complete": True, **LICENSE}))
    sync(fake, token="t").list_changes(since=since)
    assert fake.calls[0].url.params["since"] == sent


def test_posts_show_request_as_json() -> None:
    fake = FakeAPI(Answer(body={"matched": True, "alreadyAdded": False}))
    sync(fake).request_show("https://www.reelshort.com/movie/x-1")
    assert fake.calls[0].method == "POST"
    assert json.loads(fake.calls[0].content) == {"url": "https://www.reelshort.com/movie/x-1"}


def test_custom_base_url() -> None:
    fake = FakeAPI(Answer(body=[]))
    sync(fake, base_url="http://localhost:3000/").search_dramas("x")
    assert str(fake.calls[0].url) == "http://localhost:3000/api/v1/search?q=x"


def test_follows_merge_redirect() -> None:
    """An id merged into another drama answers 301 to the surviving one."""
    fake = FakeAPI(
        Answer(status=301, headers={"Location": "https://microdramalist.com/api/v1/dramas/mdid-new"}),
        Answer(body={"id": "mdid-new"}),
    )
    assert sync(fake).get_drama("mdid-old") == {"id": "mdid-new"}
    assert fake.calls[1].url.path == "/api/v1/dramas/mdid-new"


def test_default_client_follows_redirects() -> None:
    mdl = MicroDramaList()
    assert mdl._http.follow_redirects
    mdl.close()


# ------------------------------------------------------------------ errors


@pytest.mark.parametrize(
    ("status", "cls", "error"),
    [
        (400, BadRequestError, "platform: a platform slug, as /api/v1/stats/platforms lists"),
        (401, AuthenticationError, "unknown or revoked API token"),
        (404, NotFoundError, "not found"),
        (500, MicroDramaListError, "internal error"),
    ],
)
def test_maps_status_to_exception(status: int, cls: type, error: str) -> None:
    fake = FakeAPI(Answer(status=status, body={"error": error}))
    with pytest.raises(cls) as info:
        sync(fake, token="t").get_stats_genres()
    assert info.value.status == status
    assert str(info.value) == error


def test_reads_feed_plain_text_errors() -> None:
    fake = FakeAPI(Answer(status=400, text="platform: a platform slug, as /api/v1/stats/platforms lists"))
    with pytest.raises(BadRequestError, match="platform slug"):
        sync(fake).new_dramas_feed(platform="!")


def test_wraps_network_failure_as_status_0() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    mdl = MicroDramaList(http_client=httpx.Client(transport=httpx.MockTransport(boom)))
    with pytest.raises(MicroDramaListError) as info:
        mdl.search_dramas("x")
    assert info.value.status == 0


# ------------------------------------------------------------- rate limits

HEADERS: Dict[str, str] = {
    "X-RateLimit-Limit": "60",
    "X-RateLimit-Remaining": "59",
    "X-RateLimit-Reset": "1791000000",
    "X-RateLimit-Daily-Limit": "10000",
    "X-RateLimit-Daily-Remaining": "9999",
}


def test_exposes_last_rate_limit() -> None:
    fake = FakeAPI(Answer(body={"weeks": [], **LICENSE}, headers=HEADERS))
    mdl = sync(fake, token="t")
    assert mdl.last_rate_limit is None
    mdl.list_chart_weeks()
    assert mdl.last_rate_limit == {
        "limit": 60,
        "remaining": 59,
        "reset": 1791000000,
        "dailyLimit": 10000,
        "dailyRemaining": 9999,
    }


def test_retries_429_after_retry_after(no_sleep: List[float]) -> None:
    fake = FakeAPI(
        Answer(status=429, body={"error": "rate limit exceeded (per minute)"}, headers={"Retry-After": "2"}),
        Answer(body={"weeks": [], **LICENSE}),
    )
    assert sync(fake, token="t").list_chart_weeks()["weeks"] == []
    assert no_sleep == [2.25]
    assert len(fake.calls) == 2


def test_raises_at_once_on_daily_limit(no_sleep: List[float]) -> None:
    fake = FakeAPI(
        Answer(
            status=429,
            body={"error": "rate limit exceeded (per day)"},
            headers={"Retry-After": "40000", "X-RateLimit-Daily-Remaining": "0"},
        )
    )
    with pytest.raises(RateLimitError) as info:
        sync(fake, token="t").list_chart_weeks()
    assert info.value.retry_after == 40000
    assert info.value.rate_limit is not None and info.value.rate_limit["dailyRemaining"] == 0
    assert no_sleep == [] and len(fake.calls) == 1


def test_gives_up_after_max_retries(no_sleep: List[float]) -> None:
    fake = FakeAPI(Answer(status=429, body={"error": "x"}, headers={"Retry-After": "1"}))
    with pytest.raises(RateLimitError):
        sync(fake, token="t", max_retries=1).list_chart_weeks()
    assert len(fake.calls) == 2


async def test_async_retries_429(monkeypatch: pytest.MonkeyPatch) -> None:
    waits: List[float] = []

    async def fake_sleep(s: float) -> None:
        waits.append(s)

    monkeypatch.setattr(client_module.asyncio, "sleep", fake_sleep)
    fake = FakeAPI(
        Answer(status=429, body={"error": "x"}, headers={"Retry-After": "1"}),
        Answer(body={"weeks": [], **LICENSE}),
    )
    async with AsyncMicroDramaList(token="t", http_client=fake.async_client()) as mdl:
        assert (await mdl.list_chart_weeks())["weeks"] == []
    assert waits == [1.25]


# --------------------------------------------------------------- iterators


def drama(id: str) -> Dict[str, Any]:
    return {
        "id": id,
        "slug": id,
        "url": "",
        "title": id,
        "language": None,
        "genres": [],
        "episodeCount": None,
        "releaseYear": None,
        "platforms": [],
        "firstSeen": "",
    }


def event(id: str, at: str) -> Dict[str, Any]:
    return {"type": "updated", "id": id, "url": "", "platform": None, "at": at}


def pages() -> FakeAPI:
    return FakeAPI(
        Answer(body={"page": 1, "perPage": 50, "dramas": [drama("a"), drama("b")], "nextPage": 2, **LICENSE}),
        Answer(body={"page": 2, "perPage": 50, "dramas": [drama("c")], "nextPage": None, **LICENSE}),
    )


def changes() -> FakeAPI:
    return FakeAPI(
        Answer(
            body={
                "since": "T0",
                "events": [event("a", "T1"), event("b", "T2")],
                "next": "T2",
                "complete": False,
                **LICENSE,
            }
        ),
        Answer(
            body={
                "since": "T2",
                "events": [event("b", "T2"), event("c", "T3")],
                "next": "T3",
                "complete": True,
                **LICENSE,
            }
        ),
    )


def test_iter_dramas_follows_next_page() -> None:
    fake = pages()
    ids = [d["id"] for d in sync(fake, token="t").iter_dramas(genre="Revenge")]
    assert ids == ["a", "b", "c"]
    assert [c.url.params["page"] for c in fake.calls] == ["1", "2"]
    assert fake.calls[1].url.params["genre"] == "Revenge"


def test_iter_changes_yields_boundary_events_once() -> None:
    fake = changes()
    ids = [e["id"] for e in sync(fake, token="t").iter_changes(since="T0")]
    assert ids == ["a", "b", "c"]
    assert [c.url.params["since"] for c in fake.calls] == ["T0", "T2"]


def test_iter_changes_stops_without_progress() -> None:
    fake = FakeAPI(
        Answer(body={"since": "T1", "events": [event("a", "T1")], "next": "T1", "complete": False, **LICENSE})
    )
    assert len(list(sync(fake, token="t").iter_changes(since="T1"))) == 1
    assert len(fake.calls) == 2


async def test_async_iterators() -> None:
    fake = pages()
    async with AsyncMicroDramaList(token="t", http_client=fake.async_client()) as mdl:
        assert [d["id"] async for d in mdl.iter_dramas()] == ["a", "b", "c"]
    fake = changes()
    async with AsyncMicroDramaList(token="t", http_client=fake.async_client()) as mdl:
        assert [e["id"] async for e in mdl.iter_changes(since="T0")] == ["a", "b", "c"]
