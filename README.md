# MicroDramaList SDK for Python

The official Python client for the [MicroDramaList API](https://microdramalist.com/api-docs):
look up and search micro dramas, count the catalogue by genre, platform and
language, follow a genre over time, list what is new or what changed, see
where a show streams, and read the weekly MicroDramaList Top 20.

- Sync and async clients (`MicroDramaList`, `AsyncMicroDramaList`) on
  [httpx](https://www.python-httpx.org/).
- Responses are the API's JSON as plain dicts, typed with `TypedDict`s
  written from the API's [OpenAPI 3.1 spec](https://microdramalist.com/openapi.yaml),
  so they go straight into pandas, `json.dump` or a database.
- Handles the details: the bearer token, typed exceptions, rate-limit
  headers, waiting out a `429`, and iterators over paged results.

Python 3.10+. Also available: [the TypeScript SDK](https://github.com/Senpai-Media/microdramalist-sdk-typescript).

## Install

```sh
pip install git+https://github.com/Senpai-Media/microdramalist-sdk-python
# or
uv add git+https://github.com/Senpai-Media/microdramalist-sdk-python
```

## Quick start

The free endpoints need no account:

```python
from microdramalist import MicroDramaList

mdl = MicroDramaList()

results = mdl.search_dramas("billionaire")
drama = mdl.get_drama(results[0]["id"])
print(drama["title"], drama["genres"], [l["platform"] for l in drama["availableOn"]])
```

The data endpoints need a free personal token. **[Getting started](docs/getting-started.md)
walks through creating one.** Then:

```python
# Reads MICRODRAMALIST_TOKEN from the environment, or MicroDramaList(token="mdl_...").
with MicroDramaList() as mdl:
    platforms = mdl.get_stats_platforms()["platforms"]
    genres = mdl.get_stats_genres(platform="dramabox")["genres"]
    chart = mdl.get_chart_week("latest")

for entry in chart["entries"]:
    print(f"#{entry['rank']} {entry['title']} ({entry['move']})")
```

Async:

```python
import asyncio
from microdramalist import AsyncMicroDramaList


async def main():
    async with AsyncMicroDramaList() as mdl:
        chart = await mdl.get_chart_week()
        async for drama in mdl.iter_new_dramas(days=3):
            print(drama["title"])


asyncio.run(main())
```

Into pandas:

```python
import pandas as pd

df = pd.DataFrame(mdl.get_stats_genres(platform="reelshort")["genres"])
```

## Every method

| Method | Endpoint | Token |
| --- | --- | --- |
| `get_drama(id)` | `GET /api/v1/dramas/{id}`: one drama, every live listing | no |
| `search_dramas(q)` | `GET /api/v1/search`: up to 20 title matches, or an `mdid-` lookup | no |
| `request_show(url)` | `POST /api/v1/show-requests`: ask us to add a show by its app URL | no |
| `new_dramas_feed(platform=, genre=, language=)` | `GET /feeds/new.xml`: new dramas as RSS (a string) | no |
| `get_stats_platforms()` | `GET /api/v1/stats/platforms`: every app with its size | yes |
| `get_stats_genres(platform=, language=, tags=)` | `GET /api/v1/stats/genres`: stories per genre tag | yes |
| `get_stats_timeline(genre=, platform=, language=, tags=, interval=)` | `GET /api/v1/stats/timeline`: a genre or app over time | yes |
| `list_dramas(genre=, platform=, language=, sort=, page=)` | `GET /api/v1/dramas`: 50 a page | yes |
| `list_new_dramas(genre=, platform=, language=, days=, page=)` | `GET /api/v1/new`: first seen in the last days | yes |
| `list_changes(since=)` | `GET /api/v1/changes`: created, updated and pulled since a time | yes |
| `get_drama_watch(id)` | `GET /api/v1/dramas/{id}/watch`: where to watch it | yes |
| `get_drama_matches(id)` | `GET /api/v1/dramas/{id}/matches`: one show across apps | yes |
| `get_drama_chart(id)` | `GET /api/v1/dramas/{id}/chart`: its Top 20 history | yes |
| `list_chart_weeks()` | `GET /api/v1/charts/weekly`: every charted week | yes |
| `get_chart_week(week="latest")` | `GET /api/v1/charts/weekly/{week}`: one week's Top 20 | yes |

And three iterators that do the paging for you (`async for` on the async client):

```python
for drama in mdl.iter_dramas(genre="Revenge", platform="reelshort"):
    ...
for drama in mdl.iter_new_dramas(days=3):
    ...
for event in mdl.iter_changes(since="2026-10-10"):
    ...  # str, date or datetime
```

Words the API uses: a **title** is one drama page (one language or dub
version) and a **story** is the show behind its versions. **Platform tags**
are the genre tags an app gives a show itself; `tags="all"` adds the ones
MicroDramaList assigned. **firstSeen** is when our crawler first saw a
title, not a release date. Full reference: [microdramalist.com/api-docs](https://microdramalist.com/api-docs).

## Errors and rate limits

Every error is a `MicroDramaListError` with `.status` and the API's own
message; the common ones have their own class:

```python
from microdramalist import BadRequestError

try:
    mdl.get_stats_genres(platform="not-an-app")
except BadRequestError as err:
    print(err)  # platform: a platform slug, as /api/v1/stats/platforms lists
```

| Class | Status | When |
| --- | --- | --- |
| `BadRequestError` | 400 | A parameter was refused; the message says which and what it accepts. |
| `AuthenticationError` | 401 | No token, or an unknown, revoked or disabled one. |
| `NotFoundError` | 404 | No such drama, or no chart for that week. |
| `RateLimitError` | 429 | Over a limit; `.retry_after` is the seconds to wait. |

A token allows **60 requests a minute and 10,000 a day** (UTC). The client
waits out a per-minute `429` and retries (twice by default; set
`max_retries` and `max_retry_wait`), but raises at once on the daily
limit, whose `Retry-After` runs to midnight. `mdl.last_rate_limit` holds
the last answer's limits:

```python
mdl.get_stats_platforms()
print(
    mdl.last_rate_limit
)  # {'limit': 60, 'remaining': 59, 'reset': 1791..., 'dailyLimit': 10000, 'dailyRemaining': 9999}
```

## Options

```python
MicroDramaList(
    token="mdl_...",  # default: $MICRODRAMALIST_TOKEN
    base_url="https://microdramalist.com",  # the default
    timeout=30.0,
    max_retries=2,  # 429 retries; 0 turns them off
    max_retry_wait=60.0,  # seconds; a longer Retry-After raises instead
    http_client=None,  # your own httpx.Client (proxies, transports)
)
```

## Data license and credit

The data is [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/):
use it for anything, commercial included, and credit MicroDramaList with a
link. Every data response carries the credit line in `attribution`:

> Data from MicroDramaList (https://microdramalist.com)

For the whole catalogue at once, download the monthly data packs from
[microdramalist.com/data](https://microdramalist.com/data) and keep them
current with `iter_changes`.

## Examples

[`examples/`](examples) has runnable scripts: a genre's share on each app,
the latest chart, syncing changes, and a genre's weekly trend in pandas:
`MICRODRAMALIST_TOKEN=mdl_... python examples/latest_chart.py`.

## Development

```sh
uv sync
uv run pytest          # offline: a mock transport, and every example from the spec
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

`spec/openapi.yaml` is a copy of the API's spec; the tests check every
method of both clients against it. Refresh it with
`curl -fsSL https://microdramalist.com/openapi.yaml -o spec/openapi.yaml`
and run the tests.

## License

The SDK is [MIT](LICENSE). The data it fetches is CC BY 4.0 (above).
