# Routing: what to load for each kind of change

Find the row for the change, open what it names, skip what it says to
skip. The spec is the source of truth and the tests enforce it, so most
rows start there; every method exists twice, sync and async.

| Task                                    | Go to                            | Load                                                                                                                                                                     | Skip                                                      |
| --------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------- |
| Add or change an API method             | `src/microdramalist/_client.py`  | the operation in `spec/openapi.yaml`, both clients, `src/microdramalist/types.py`, `tests/test_spec.py`, `README.md` ("Every method")                                    | `examples/` unless the method is shown there              |
| The spec changed upstream               | `spec/openapi.yaml`              | `task spec:sync`, then what `tests/test_spec.py` reports; `src/microdramalist/types.py` for a changed shape                                                              | `src/microdramalist/_errors.py`                           |
| Errors, retries, rate limits            | `src/microdramalist/_errors.py`  | `_Base` and both `_request` methods in `src/microdramalist/_client.py`, `tests/test_client.py`, `README.md` ("Errors and rate limits")                                   | the method list                                           |
| Iterators and paging                    | `src/microdramalist/_client.py`  | `iter_dramas`, `iter_new_dramas`, `iter_changes` on both clients; `tests/test_client.py`                                                                                 | `src/microdramalist/types.py` unless a page shape changed |
| Client options, the token, the base URL | `src/microdramalist/_client.py`  | `_Base.__init__` and both constructors, `tests/test_client.py` (the token tests), `README.md` ("Options"), `docs/getting-started.md` ("Keep your token secret")          | `spec/openapi.yaml`                                       |
| User documentation                      | `README.md`                      | `docs/getting-started.md`, `CHANGELOG.md`; the TypeScript SDK's README for the same wording                                                                              | the source unless a claim needs checking                  |
| An example                              | `examples/`                      | the sibling example, `README.md` ("Examples"); `py_compile` it (`task check` does)                                                                                       | the tests                                                 |
| A release                               | `src/microdramalist/_version.py` | `CHANGELOG.md`, `pyproject.toml` (the sdist allowlist and its known gap), `scripts/check_package.py` (`task package:check`), `scripts/live_smoke.py` (`task smoke:live`) | the tests' internals                                      |
| Supported Python versions, CI           | `.github/workflows/test.yml`     | `pyproject.toml` ("requires-python", classifiers), `mise.toml`                                                                                                           | the source                                                |
| Lint, format and type settings          | `pyproject.toml`                 | the `[tool.ruff]` and `[tool.mypy]` tables and their comments; `task lint`                                                                                               | the tests                                                 |

## Always

- `CONTEXT.md` (the map), then the file the row names.
- `CLAUDE.md`: a public repository, the spec rule, the two parallel clients, the package allowlist, the commit style, and the TypeScript SDK gets the same change.
- `task check` before a commit; `task package:check` before a publish.

## Never by default

- `.venv`, `dist` and the caches (gitignored); `uv.lock` unless a dependency changes.
- `spec/openapi.yaml` in full: read the one operation.
