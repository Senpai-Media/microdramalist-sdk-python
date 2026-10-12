# microdramalist-sdk-python

The public Python SDK for the MicroDramaList API
(https://microdramalist.com/api-docs). **This repository is public**
(github.com/Senpai-Media/microdramalist-sdk-python): everything committed
here, comments included, is read by strangers. Nothing internal goes in it
-- no infrastructure, hostnames other than microdramalist.com, other
repositories' paths, credentials, or notes about how the site is run.

- `spec/openapi.yaml` is a copy of the API's published spec
  (https://microdramalist.com/openapi.yaml); `task spec:sync` refreshes
  it. It is the source of truth: `src/microdramalist/types.py` and
  `_client.py` follow it by hand, and `tests/test_spec.py` fails when an
  operation, path or query parameter has no match on either client, or a
  spec example does not come back unchanged.
- One method per operationId, in snake_case, on both `MicroDramaList` and
  `AsyncMicroDramaList` (kept parallel by hand). `requestPlatform` is
  deliberately absent (it needs the site's browser session cookie, not a
  token).
- Responses stay the API's plain dicts; `types.py` only describes them.
  Dependencies: httpx and typing-extensions, nothing else. Python 3.10+.
- Every change: `task check` passes, README / docs / CHANGELOG describe it
  in the same commit, and the TypeScript SDK
  (github.com/Senpai-Media/microdramalist-sdk-typescript) gets the same
  change.
- Commit messages: `area: lowercase imperative description` (at most 80
  characters), a blank line, then a body for anything non-trivial. No AI
  attribution.
