"""The MicroDramaList API's response shapes, as TypedDicts.

Written by hand from spec/openapi.yaml (OpenAPI 3.1, the API's one
definition). Responses are returned as the plain dicts the API sends -- these
types only describe them for editors and type checkers, so a response loads
straight into pandas or json.dump. A nullable field in the spec
(``type: [T, "null"]``) is ``Optional[T]`` here. tests/test_spec.py checks
that every operation has a client method and that every spec example comes
back through it unchanged.
"""

from __future__ import annotations

from typing import List, Literal, Optional, TypedDict

from typing_extensions import NotRequired

TagSource = Literal["platform", "all"]
"""``platform``: the apps' own genre tags (default); ``all`` adds ours."""

Interval = Literal["day", "week", "month"]

ChartMove = Literal["up", "down", "same", "new", "reentry"]
"""A chart entry's movement against the week before."""


class License(TypedDict):
    """The CC BY 4.0 block every data (token) response ends with."""

    license: str
    licenseUrl: str
    attribution: str
    """The credit line to show beside anything made from the data."""


# ------------------------------------------------------------------ free


class DramaListing(TypedDict):
    platform: str
    """The app's display name."""
    url: str
    """The link a reader follows (the app's homepage for an unverified listing)."""
    unverified: bool
    language: Optional[str]
    dubbed: bool
    additionalAttributes: List[str]
    externalId: Optional[str]
    lastCheckedAt: str


class Drama(TypedDict):
    """GET /api/v1/dramas/{id} (free)."""

    id: str
    title: str
    alternativeTitles: List[str]
    genres: List[str]
    episodeCount: Optional[int]
    releaseYear: Optional[int]
    languages: List[str]
    upvotes: int
    downvotes: int
    description: Optional[str]
    """Our rewritten description; None until written."""
    posterUrl: Optional[str]
    availableOn: List[DramaListing]


class SearchResult(TypedDict):
    """One match of GET /api/v1/search (free)."""

    id: str
    title: str
    posterUrl: Optional[str]
    description: Optional[str]


class ShowRequestReply(TypedDict):
    """POST /api/v1/show-requests (free)."""

    matched: bool
    """The URL is on an app we cover."""
    alreadyAdded: NotRequired[bool]
    dramaSlug: NotRequired[str]


# ------------------------------------------------------- catalogue stats


class PlatformStat(TypedDict):
    platform: str
    """The slug the other endpoints take as ``platform``."""
    name: str
    enabled: bool
    """Still crawled."""
    titles: int
    stories: int
    englishShare: float
    """Percent of titles in English, one decimal."""
    episodeMedian: Optional[float]


class PlatformsResponse(License):
    """GET /api/v1/stats/platforms."""

    platforms: List[PlatformStat]


class GenreStat(TypedDict):
    genre: str
    stories: int
    titles: int
    share: float
    """Percent of the scope's stories, one decimal."""


class GenresScope(TypedDict):
    platform: Optional[str]
    language: Optional[str]
    tags: TagSource


class GenresResponse(License):
    """GET /api/v1/stats/genres."""

    scope: GenresScope
    totalStories: int
    """Stories in the scope (with a live listing), the shares' denominator."""
    genres: List[GenreStat]


class TimelineScope(TypedDict):
    genre: Optional[str]
    platform: Optional[str]
    language: Optional[str]
    tags: TagSource
    interval: Interval


class TimelineNotes(TypedDict):
    snapshots: str
    firstSeen: str


class SnapshotPoint(TypedDict):
    period: str
    """The period's first day (UTC; weeks start on Monday)."""
    titles: int
    stories: int


class FirstSeenPoint(TypedDict):
    period: str
    titles: int


class TimelineResponse(License):
    """GET /api/v1/stats/timeline."""

    scope: TimelineScope
    notes: TimelineNotes
    snapshots: List[SnapshotPoint]
    """Catalogue size at the end of each period, from nightly snapshots."""
    firstSeen: List[FirstSeenPoint]
    """Titles our crawler first saw in each period; not release dates."""


# ---------------------------------------------------------------- dramas


class ListedDrama(TypedDict):
    id: str
    slug: str
    url: str
    title: str
    language: Optional[str]
    genres: List[str]
    episodeCount: Optional[int]
    releaseYear: Optional[int]
    platforms: List[str]
    """Slugs of the apps with a live listing (that one only, when filtered by platform)."""
    firstSeen: str
    """When our crawler first saw the title; not a release date."""


class DramasResponse(License):
    """GET /api/v1/dramas: one page, 50 at most."""

    page: int
    perPage: int
    dramas: List[ListedDrama]
    nextPage: Optional[int]
    """None on a short (last) page."""


class NewDramasResponse(DramasResponse):
    """GET /api/v1/new."""

    since: str
    """now - days, the list's cut-off."""


class ChangeEvent(TypedDict):
    type: Literal["created", "updated", "pulled"]
    id: str
    url: str
    platform: Optional[str]
    """The app a listing was pulled from (``pulled`` only)."""
    at: str


class ChangesResponse(License):
    """GET /api/v1/changes."""

    since: str
    events: List[ChangeEvent]
    next: str
    """The last event's time (or ``since`` when none): the next call's ``since``."""
    complete: bool
    """False when the 1,000 limit cut the list short."""


class Version(TypedDict):
    id: str
    url: str
    title: str


class WatchListing(TypedDict):
    platform: str
    platformName: str
    link: str
    """Our affiliate link where we have one; the app's homepage for an unverified listing."""
    language: Optional[str]
    dubbed: bool
    episodeCount: Optional[int]
    version: Version
    lastChecked: str


class WatchResponse(License):
    """GET /api/v1/dramas/{id}/watch."""

    id: str
    title: str
    url: str
    watch: List[WatchListing]


class MatchListing(TypedDict):
    platform: str
    platformShowId: Optional[str]
    platformUrl: str
    unverified: bool


class MatchVersion(TypedDict):
    id: str
    url: str
    title: str
    language: Optional[str]
    kind: str
    """``original``, or the version's kind (dub, language, ...)."""
    label: Optional[str]
    listings: List[MatchListing]


class MatchesResponse(License):
    """GET /api/v1/dramas/{id}/matches."""

    story: str
    """The original version's public id."""
    versions: List[MatchVersion]


# ---------------------------------------------------------------- charts


class DramaChartWeek(TypedDict):
    week: str
    rank: int
    move: ChartMove
    lastWeek: Optional[int]


class DramaChartResponse(License):
    """GET /api/v1/dramas/{id}/chart."""

    id: str
    title: str
    weeksOnChart: int
    peak: Optional[int]
    """Best rank; None when never on the chart."""
    weeks: List[DramaChartWeek]


class ChartWeekRef(TypedDict):
    week: str
    startsOn: str
    url: str


class ChartWeeksResponse(License):
    """GET /api/v1/charts/weekly."""

    weeks: List[ChartWeekRef]


class ChartEntry(TypedDict):
    rank: int
    move: ChartMove
    lastWeek: Optional[int]
    peak: int
    weeksOnChart: int
    id: str
    title: str
    url: str


class ChartWeekResponse(License):
    """GET /api/v1/charts/weekly/{week}."""

    week: str
    startsOn: str
    entries: List[ChartEntry]


class RateLimit(TypedDict):
    """The rate-limit headers of the last response; a field is None when absent."""

    limit: Optional[int]
    remaining: Optional[int]
    reset: Optional[int]
    """When the minute window resets, in Unix seconds."""
    dailyLimit: Optional[int]
    dailyRemaining: Optional[int]
