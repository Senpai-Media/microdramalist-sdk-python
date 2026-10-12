"""One genre's share of each app's catalogue: which apps lean into Revenge?

    MICRODRAMALIST_TOKEN=mdl_... python examples/genre_share.py [genre]

Uses 1 + (number of apps) requests: the platform list, then each app's genres.
"""

import sys

from microdramalist import MicroDramaList

genre = sys.argv[1] if len(sys.argv) > 1 else "Revenge"

with MicroDramaList() as mdl:
    stats = mdl.get_stats_platforms()
    rows = []
    for p in stats["platforms"]:
        if not p["enabled"] or p["stories"] < 100:
            continue
        genres = mdl.get_stats_genres(platform=p["platform"])["genres"]
        g = next((x for x in genres if x["genre"] == genre), None)
        rows.append((p["name"], p["stories"], g["stories"] if g else 0, g["share"] if g else 0.0))

rows.sort(key=lambda r: r[3], reverse=True)
print(f"{'app':<20}{'stories':>9}{genre:>12}{'share':>8}")
for name, stories, count, share in rows:
    print(f"{name:<20}{stories:>9}{count:>12}{share:>7.1f}%")
print(stats["attribution"])
