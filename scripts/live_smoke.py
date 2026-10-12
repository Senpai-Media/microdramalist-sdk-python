"""Calls the live API through the package: the free endpoints always, and
every data endpoint when MICRODRAMALIST_TOKEN is set. A quick "does the SDK
still match production" check before a release (task smoke:live). About 12
requests; well inside every limit."""

import os
import sys
from typing import Any, Callable

from microdramalist import MicroDramaList, MicroDramaListError

failed = False


def step(name: str, fn: Callable[[], Any]) -> Any:
    global failed
    try:
        out = fn()
        print(f"ok    {name}")
        return out
    except MicroDramaListError as err:
        print(f"FAIL  {name}: {type(err).__name__} {err.status} {err}")
        failed = True
        return None


with MicroDramaList(base_url=os.environ.get("MICRODRAMALIST_BASE_URL")) as mdl:
    hits = step("search_dramas", lambda: mdl.search_dramas("billionaire")) or []
    drama_id = hits[0]["id"] if hits else "mdid-r229ssxt"
    step("get_drama", lambda: mdl.get_drama(drama_id))
    step("new_dramas_feed", lambda: mdl.new_dramas_feed())
    if not mdl.has_token:
        print("skip  data endpoints: set MICRODRAMALIST_TOKEN to check them")
    else:
        stats = step("get_stats_platforms", mdl.get_stats_platforms)
        platform = stats["platforms"][0]["platform"] if stats else None
        step("get_stats_genres", lambda: mdl.get_stats_genres(platform=platform))
        step("get_stats_timeline", lambda: mdl.get_stats_timeline(platform=platform))
        step("list_dramas", lambda: mdl.list_dramas(platform=platform))
        step("list_new_dramas", mdl.list_new_dramas)
        step("list_changes", mdl.list_changes)
        step("get_drama_watch", lambda: mdl.get_drama_watch(drama_id))
        step("get_drama_matches", lambda: mdl.get_drama_matches(drama_id))
        step("get_drama_chart", lambda: mdl.get_drama_chart(drama_id))
        step("list_chart_weeks", mdl.list_chart_weeks)
        step("get_chart_week", mdl.get_chart_week)
        print("rate limit after:", mdl.last_rate_limit)

sys.exit(1 if failed else 0)
