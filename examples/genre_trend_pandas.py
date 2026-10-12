"""A genre's weekly growth on one app, as a pandas DataFrame (and a chart if
matplotlib is installed). Needs pandas: pip install pandas matplotlib

    MICRODRAMALIST_TOKEN=mdl_... python examples/genre_trend_pandas.py [genre] [platform]

firstSeen counts titles our crawler first saw each week -- not release
dates -- and reaches back before the nightly snapshots began.
"""

import sys

import pandas as pd

from microdramalist import MicroDramaList

genre = sys.argv[1] if len(sys.argv) > 1 else "Revenge"
platform = sys.argv[2] if len(sys.argv) > 2 else "dramabox"

with MicroDramaList() as mdl:
    timeline = mdl.get_stats_timeline(genre=genre, platform=platform, interval="week")

df = pd.DataFrame(timeline["firstSeen"]).set_index("period")
print(df.tail(12))

try:
    import matplotlib.pyplot as plt

    ax = df["titles"].plot(kind="bar", title=f"{genre} titles first seen per week on {platform}")
    ax.figure.text(0.01, 0.01, timeline["attribution"], fontsize=7)
    plt.tight_layout()
    plt.show()
except ImportError:
    pass
