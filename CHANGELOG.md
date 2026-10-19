# Changelog

## 0.1.0 (unreleased)

- 2026-10-19: the API's limits changed. A token is 60 a minute and 300 an
  hour with no daily limit; the free endpoints 30 a minute, 150 an hour
  and 1,000 a day per address. `last_rate_limit` gains `hourlyLimit`,
  `hourlyRemaining` and `hourlyReset`; `dailyLimit` and `dailyRemaining`
  are set only on the free endpoints' daily refusal. The vendored spec
  carries the API's terms of use.

- First release: every MicroDramaList API v1 endpoint (free and data) on a
  sync and an async client, typed from the OpenAPI 3.1 spec; typed
  exceptions; rate-limit headers; automatic retry of per-minute 429s;
  `iter_dramas`, `iter_new_dramas` and `iter_changes`.
