# microdramalist-sdk-python: the Python SDK for the MicroDramaList API

<!-- A map of the repository for contributors: what each folder is for,
     what a change depends on, and the rules every change keeps. Short on
     purpose; the long form is README.md and docs/getting-started.md. -->

## Goal

A sync and an async client for every endpoint of the
[MicroDramaList API](https://microdramalist.com/api-docs), for anyone who
wants micro drama data in Python 3.10+: plain dicts typed with
`TypedDict`s, so a response goes straight into pandas or `json.dump`. It
works when every operation in `spec/openapi.yaml` has a method on both
clients, every spec example comes back through them unchanged, and
`task check` passes on every supported Python.

## Inside

| Path                                   | What it is                                                                                                                                                                                                                                                                                                               |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/`                                 | the package `src/microdramalist/`: `_client.py` (`_Base`, then `MicroDramaList` and `AsyncMicroDramaList`, one method per operationId in snake_case, kept parallel by hand), `_errors.py` (the exceptions), `types.py` (the `TypedDict`s, by hand from the spec), `__init__.py` (the exports), `_version.py`, `py.typed` |
| `spec/`                                | `openapi.yaml`: a copy of the API's published spec, the source of truth; `task spec:sync` refreshes it                                                                                                                                                                                                                   |
| `tests/`                               | `test_spec.py` (both clients against the spec), `test_client.py` (token, requests, errors, rate limits, iterators), `conftest.py` (the fake transport)                                                                                                                                                                   |
| `examples/`                            | runnable scripts: a genre's share on each app, the latest chart, syncing changes, a genre's weekly trend in pandas                                                                                                                                                                                                       |
| `scripts/`                             | `check_package.py` (the sdist and wheel hold only the SDK and its docs, no credential-shaped string), `live_smoke.py` (the live API, `task smoke:live`)                                                                                                                                                                  |
| `docs/`                                | `getting-started.md`: creating a token, keeping it secret, first calls, limits, credit                                                                                                                                                                                                                                   |
| `.github/`                             | `workflows/test.yml`: ruff, mypy, pytest and a build on Python 3.10 to 3.14, every push and pull request                                                                                                                                                                                                                 |
| `pyproject.toml`                       | the package `microdramalist` (hatchling), its two dependencies, the sdist allowlist, ruff and mypy settings                                                                                                                                                                                                              |
| `uv.lock`                              | the locked development environment (`uv sync`)                                                                                                                                                                                                                                                                           |
| `Taskfile.yml`                         | `install`, `test`, `lint`, `format`, `check`, `package:check`, `smoke:live`, `spec:sync`                                                                                                                                                                                                                                 |
| `README.md`, `CHANGELOG.md`, `LICENSE` | the user guide (every method, errors, options, license), the release notes, MIT                                                                                                                                                                                                                                          |
| `CLAUDE.md`                            | the rules for an AI session (`AGENTS.md` is a symlink to it); `ROUTING.md`: what to load for each kind of change                                                                                                                                                                                                         |
| `mise.toml`, `.pre-commit-profiles`    | tool versions (`mise trust && mise install && uv sync`); a maintainers' hook profile                                                                                                                                                                                                                                     |

## Depends on / depended on by

- Reads: the MicroDramaList API at https://microdramalist.com and its
  spec; `httpx` and `typing-extensions`, nothing else at run time.
  Development only: pytest, pytest-asyncio, PyYAML, ruff, mypy.
- Used by: anyone installing from GitHub (PyPI later); the
  [TypeScript SDK](https://github.com/Senpai-Media/microdramalist-sdk-typescript)
  mirrors every change here, method for method.

## Load / skip

- Load: for a method, the operation in `spec/openapi.yaml`, both clients in `src/microdramalist/_client.py`, `src/microdramalist/types.py` and `tests/test_spec.py`; for a user-facing change, `README.md` and `docs/getting-started.md`.
- Skip: `.venv`, `dist` and the caches (gitignored); `uv.lock` unless a dependency changes; `spec/openapi.yaml` in full (read the one operation).

## Rules and traps

- This repository is public: nothing internal goes in it, comments included (`CLAUDE.md`).
- The spec is the source of truth: `types.py` and `_client.py` follow it by hand, and `tests/test_spec.py` fails on any operation, path or query parameter without a match on either client (`CLAUDE.md`).
- One method per operationId on both clients, kept parallel by hand; `requestPlatform` is deliberately absent (it needs the site's browser session, not a token).
- Responses stay the API's plain dicts; `types.py` only describes them. Dependencies: httpx and typing-extensions, nothing else; Python 3.10+ (`pyproject.toml`).
- The packages hold only the SDK and its docs: the sdist is an allowlist in `pyproject.toml` and `scripts/check_package.py` fails on anything else; it fails today on the `.gitignore` hatchling force-adds, to fix before the first PyPI upload (`pyproject.toml`).
- Every change: `task check` passes; README, docs and CHANGELOG describe it in the same commit; the TypeScript SDK gets the same change.
- Commit messages: `area: lowercase imperative description`, at most 80 characters, then a body for anything non-trivial (`CLAUDE.md`).
- Never commit a token: `.env*` is ignored and the tests run offline on a fake transport (`tests/conftest.py`).

## Read next

- `README.md` ("Development", "Every method"), then `docs/getting-started.md`.
- `CLAUDE.md`: the rules in full; `CHANGELOG.md`: what each release changed.
- The TypeScript SDK, for the same change on the other side.
