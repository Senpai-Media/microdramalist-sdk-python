"""This week's MicroDramaList Top 20, with movement and where to watch #1.

MICRODRAMALIST_TOKEN=mdl_... python examples/latest_chart.py
"""

from microdramalist import MicroDramaList

ARROW = {"up": "▲", "down": "▼", "same": "=", "new": "NEW", "reentry": "RE"}

with MicroDramaList() as mdl:
    chart = mdl.get_chart_week("latest")
    print(f"MicroDramaList Top 20, week {chart['week']} (from {chart['startsOn']})\n")
    for e in chart["entries"]:
        last = "  " if e["lastWeek"] is None else f"{e['lastWeek']:>2}"
        print(f"{e['rank']:>2}  {ARROW[e['move']]:<3} last {last}  {e['title']}")

    if chart["entries"]:
        watch = mdl.get_drama_watch(chart["entries"][0]["id"])["watch"]
        apps = sorted({w["platformName"] for w in watch})
        print(f"\nWatch #1 on: {', '.join(apps)}")
    print(f"\n{chart['attribution']}")
