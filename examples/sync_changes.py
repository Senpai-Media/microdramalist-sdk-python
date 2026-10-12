"""Keep a local copy in sync: every drama created, updated or pulled since a
time (default: 24 hours ago). Pair it with a data pack from
https://microdramalist.com/data for the starting point.

    MICRODRAMALIST_TOKEN=mdl_... python examples/sync_changes.py [since]
"""

import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

from microdramalist import MicroDramaList

since = sys.argv[1] if len(sys.argv) > 1 else (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

counts: Counter = Counter()
last = since
with MicroDramaList() as mdl:
    for event in mdl.iter_changes(since=since):
        counts[event["type"]] += 1
        last = event["at"]
        # Here: fetch the drama with mdl.get_drama(event["id"]) and upsert
        # it, or drop the listing on "pulled".

print(dict(counts))
print(f"Next run: python examples/sync_changes.py {last}")
