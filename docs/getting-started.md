# Getting started: your API token and first calls

This guide takes you from nothing to a working script in about five
minutes. The free endpoints (drama lookup, search, show requests and the
RSS feed) need none of it; everything else needs a personal API token.

## 1. Create an account and verify your email

1. Go to [microdramalist.com/signup](https://microdramalist.com/signup) and
   create an account (or [log in](https://microdramalist.com/login)).
2. Open the verification email we send and click its link. Tokens can only
   be created by a verified account; until then Settings says *"Verify your
   email address to create a token."* Lost the email?
   [Send it again](https://microdramalist.com/resend-verification).

## 2. Create a token

1. Open [Settings > API tokens](https://microdramalist.com/settings#api-tokens).
2. Type a name that says what the token is for, e.g. `my-genre-tracker`,
   and click **Create token**.
3. **Copy the token now.** It starts with `mdl_` and is shown once: we keep
   only a hash of it, so nobody (us included) can show it to you again. If
   you lose it, regenerate it (below).

An account can have up to five live tokens. Use one per app or script, so
you can turn one off without breaking the others.

## 3. Keep your token secret

A token is a password for your account's API quota. Treat it like one:

- **Keep it out of your code.** Put it in an environment variable; the SDK
  reads `MICRODRAMALIST_TOKEN` by itself:

  ```sh
  export MICRODRAMALIST_TOKEN=mdl_...      # macOS / Linux
  setx MICRODRAMALIST_TOKEN mdl_...        # Windows (new terminals)
  ```

  or a `.env` file that your `.gitignore` lists, loaded with python-dotenv
  or your framework.
- **Never ship it to a browser or a shared notebook.** Anything in
  front-end code, or saved in a notebook you share, can be read by whoever
  opens it. Call the data endpoints from your server or script and share
  only the results.
- **Leaked one?** In Settings > API tokens, **Regenerate** gives the token
  a new secret and the old one stops working at once; **Disable** pauses it
  (enable it again later); **Revoke** deletes it for good.

## 4. Install the SDK

```sh
pip install git+https://github.com/Senpai-Media/microdramalist-sdk-python
```

Python 3.10 or newer.

## 5. Your first calls

Save this as `first.py`:

```python
from microdramalist import MicroDramaList

with MicroDramaList() as mdl:  # reads MICRODRAMALIST_TOKEN
    # Free: no token used.
    hit = mdl.search_dramas("billionaire")[0]
    print("Found:", hit["title"], hit["id"])

    # Token: the apps we track, largest first.
    stats = mdl.get_stats_platforms()
    for p in stats["platforms"][:5]:
        print(f"{p['name']}: {p['titles']} titles, {p['englishShare']}% in English")

    # The top genres on one app.
    genres = mdl.get_stats_genres(platform=stats["platforms"][0]["platform"])["genres"]
    print(", ".join(f"{g['genre']} {g['share']}%" for g in genres[:5]))

    print(stats["attribution"])  # credit this wherever you show the data
    print("Requests left today:", mdl.last_rate_limit and mdl.last_rate_limit["dailyRemaining"])
```

Run it:

```sh
python first.py
```

If you see `AuthenticationError: this endpoint needs an API token`, the
environment variable is not set in that terminal; if you see `unknown or
revoked API token`, the value is wrong or the token was revoked.

## 6. Limits

| | Free endpoints | Data endpoints (token) |
| --- | --- | --- |
| Per minute | 30 per IP address | 60 per token |
| Per day | none | 10,000 per token (UTC day) |
| Show requests | 20 an hour per address | |

Over a limit the API answers `429` with `Retry-After`. The SDK waits and
retries per-minute limits for you, and raises `RateLimitError` for the
daily one. Need the whole catalogue? Download the free monthly data packs
from [microdramalist.com/data](https://microdramalist.com/data) instead of
paging through `list_dramas`, then keep them current with `iter_changes`.

## 7. Credit

The data is CC BY 4.0. Show the credit line (every data response has it as
`attribution`) with a link to https://microdramalist.com next to your
chart, table or article.

## Next

- [README](../README.md#every-method): every method.
- [examples/](../examples): runnable scripts.
- [API reference](https://microdramalist.com/api-docs): every endpoint,
  parameter and field.
