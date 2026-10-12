"""Test helpers: a fake transport that records every request and answers
from a queue, so the tests run offline and never touch microdramalist.com."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
import pytest


@dataclass
class Answer:
    status: int = 200
    body: Any = None
    text: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)


class FakeAPI:
    """Answers each request with the next queued Answer (the last one repeats)."""

    def __init__(self, *answers: Answer) -> None:
        self.answers = list(answers) or [Answer(body={})]
        self.calls: List[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        a = self.answers[min(len(self.calls) - 1, len(self.answers) - 1)]
        content = a.text if a.text is not None else json.dumps(a.body if a.body is not None else {})
        return httpx.Response(a.status, content=content.encode(), headers=a.headers)

    def sync_client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler), follow_redirects=True)

    def async_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler), follow_redirects=True)


LICENSE = {
    "license": "CC BY 4.0",
    "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
    "attribution": "Data from MicroDramaList (https://microdramalist.com)",
}


@pytest.fixture(autouse=True)
def no_env_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests decide the token themselves; a developer's real one never leaks in."""
    monkeypatch.delenv("MICRODRAMALIST_TOKEN", raising=False)
