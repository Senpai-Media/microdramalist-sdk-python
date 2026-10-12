"""Both clients against spec/openapi.yaml, the API's one definition (a copy
of https://microdramalist.com/openapi.yaml, refreshed by `task spec:sync`):

- every operation has a method on both clients, its operationId in
  snake_case (one deliberate exception, below);
- each method calls the spec's method and path and sends only query
  parameters the spec declares;
- each method returns the spec's own 200 example unchanged.

A spec change that adds an endpoint or a parameter fails here first.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import pytest
import yaml

from microdramalist import AsyncMicroDramaList, MicroDramaList

from .conftest import Answer, FakeAPI

SPEC = yaml.safe_load((Path(__file__).parent.parent / "spec" / "openapi.yaml").read_text())

# requestPlatform needs the site's browser sign-in cookie, not a token, so an
# SDK cannot call it on a user's behalf (src/microdramalist/_client.py).
NOT_IN_SDK = {"requestPlatform"}


def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


# How each operation is called in these tests, with the spec's example values.
CALLS: Dict[str, Tuple[tuple, dict]] = {
    "getDrama": (("mdid-r229ssxt",), {}),
    "searchDramas": (("billionaire",), {}),
    "requestShow": (("https://www.reelshort.com/movie/example-123",), {}),
    "newDramasFeed": ((), {"genre": "Revenge", "platform": "dramabox", "language": "eng"}),
    "getStatsPlatforms": ((), {}),
    "getStatsGenres": ((), {"platform": "dramabox", "language": "eng", "tags": "platform"}),
    "getStatsTimeline": (
        (),
        {"genre": "Revenge", "platform": "dramabox", "language": "eng", "tags": "all", "interval": "week"},
    ),
    "listDramas": ((), {"genre": "Revenge", "platform": "dramabox", "language": "eng", "sort": "popular", "page": 2}),
    "listNewDramas": ((), {"genre": "Revenge", "platform": "dramabox", "language": "eng", "days": 7, "page": 1}),
    "listChanges": ((), {"since": "2026-10-10T00:00:00Z"}),
    "getDramaWatch": (("mdid-r229ssxt",), {}),
    "getDramaMatches": (("mdid-r229ssxt",), {}),
    "getDramaChart": (("mdid-r229ssxt",), {}),
    "listChartWeeks": ((), {}),
    "getChartWeek": (("latest",), {}),
}

OPS: List[Tuple[str, str, Dict[str, Any]]] = [
    (method.upper(), path, op)
    for path, item in SPEC["paths"].items()
    for method, op in item.items()
    if op["operationId"] not in NOT_IN_SDK
]


def param(p: Dict[str, Any]) -> Dict[str, Any]:
    """A parameter, following a components $ref."""
    if "$ref" in p:
        return SPEC["components"]["parameters"][p["$ref"].rsplit("/", 1)[-1]]
    return p


def example_answer(op: Dict[str, Any]) -> Tuple[Answer, Any]:
    media_type, media = next(iter(op["responses"]["200"]["content"].items()))
    example = media["example"]
    if media_type == "application/json":
        return Answer(body=example), example
    return Answer(text=example), example


def test_every_operation_has_a_method() -> None:
    for _, _, op in OPS:
        name = snake(op["operationId"])
        assert callable(getattr(MicroDramaList, name, None)), name
        assert callable(getattr(AsyncMicroDramaList, name, None)), f"async {name}"
        assert op["operationId"] in CALLS, f"test call for {op['operationId']}"


def check_request(fake: FakeAPI, method: str, path: str, op: Dict[str, Any]) -> None:
    request = fake.calls[0]
    assert request.method == method
    assert re.fullmatch(re.sub(r"\{[^}]+\}", "[^/]+", path), request.url.path), request.url.path
    declared = {param(p)["name"] for p in op.get("parameters", []) if param(p)["in"] == "query"}
    for name in request.url.params:
        assert name in declared, f"query {name} is not in the spec"


@pytest.mark.parametrize(("method", "path", "op"), OPS, ids=[op["operationId"] for _, _, op in OPS])
def test_sync_method_matches_spec(method: str, path: str, op: Dict[str, Any]) -> None:
    answer, example = example_answer(op)
    fake = FakeAPI(answer)
    args, kwargs = CALLS[op["operationId"]]
    with MicroDramaList(token="mdl_test", http_client=fake.sync_client()) as mdl:
        fn: Callable[..., Any] = getattr(mdl, snake(op["operationId"]))
        assert fn(*args, **kwargs) == example
    check_request(fake, method, path, op)


@pytest.mark.parametrize(("method", "path", "op"), OPS, ids=[op["operationId"] for _, _, op in OPS])
async def test_async_method_matches_spec(method: str, path: str, op: Dict[str, Any]) -> None:
    answer, example = example_answer(op)
    fake = FakeAPI(answer)
    args, kwargs = CALLS[op["operationId"]]
    async with AsyncMicroDramaList(token="mdl_test", http_client=fake.async_client()) as mdl:
        fn: Callable[..., Any] = getattr(mdl, snake(op["operationId"]))
        assert await fn(*args, **kwargs) == example
    check_request(fake, method, path, op)
