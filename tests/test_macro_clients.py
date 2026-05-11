"""
Tests for the GDELT and GDACS HTTP clients.

These never hit the live network — we inject ``httpx.MockTransport`` so the
tests are deterministic and CI-safe.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import httpx

from app.macro import (
    DEFAULT_PACKS,
    GdacsClient,
    GdacsRecord,
    GdeltArticle,
    GdeltClient,
    KeywordPack,
    confirm_articles,
)
from app.macro.event_fetcher import EventCategory, EventDirection

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _transport_returning(status: int, body: dict | str) -> httpx.MockTransport:
    payload = body if isinstance(body, str) else json.dumps(body)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text=payload)

    return httpx.MockTransport(handler)


def _transport_sequence(*responses: httpx.Response) -> httpx.MockTransport:
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        if not queue:
            return httpx.Response(500, text="exhausted")
        return queue.pop(0)

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# keyword packs
# ---------------------------------------------------------------------------


def test_default_packs_have_required_fields():
    assert len(DEFAULT_PACKS) >= 3
    for p in DEFAULT_PACKS:
        assert isinstance(p, KeywordPack)
        assert p.name
        assert p.gdelt_query.startswith("(")
        assert p.category == EventCategory.GEOPOLITICAL
        assert p.default_direction in (EventDirection.BEARISH, EventDirection.BULLISH)


# ---------------------------------------------------------------------------
# GDELT
# ---------------------------------------------------------------------------


async def test_gdelt_parses_articles():
    body = {
        "articles": [
            {
                "title": "Sanctions hit X",
                "url": "https://example.com/a",
                "domain": "example.com",
                "seendate": "20260511T120000Z",
                "sourcecountry": "US",
                "language": "English",
            },
            {
                "title": "Port closure in Y",
                "url": "https://other.org/b",
                "domain": "other.org",
                "seendate": "20260511T121500Z",
                "sourcecountry": "DE",
            },
        ]
    }
    client = GdeltClient(transport=_transport_returning(200, body), max_retries=1)
    articles = await client.fetch_pack(DEFAULT_PACKS[0])
    assert len(articles) == 2
    assert articles[0].domain == "example.com"
    assert articles[0].seendate.tzinfo == UTC


async def test_gdelt_empty_body_returns_empty_list():
    client = GdeltClient(transport=_transport_returning(200, ""), max_retries=1)
    articles = await client.fetch_pack(DEFAULT_PACKS[0])
    assert articles == []


async def test_gdelt_retries_on_429_then_succeeds():
    good_body = json.dumps({"articles": []})
    transport = _transport_sequence(
        httpx.Response(429, text="rate-limited"),
        httpx.Response(200, text=good_body),
    )
    client = GdeltClient(transport=transport, max_retries=3)
    articles = await client.fetch_pack(DEFAULT_PACKS[0])
    assert articles == []  # success, but no records


async def test_gdelt_gives_up_after_exhausted_retries():
    transport = _transport_sequence(
        httpx.Response(429),
        httpx.Response(429),
        httpx.Response(429),
    )
    client = GdeltClient(transport=transport, max_retries=3)
    articles = await client.fetch_pack(DEFAULT_PACKS[0])
    assert articles == []


async def test_gdelt_does_not_retry_on_404():
    transport = _transport_returning(404, "")
    client = GdeltClient(transport=transport, max_retries=5)
    articles = await client.fetch_pack(DEFAULT_PACKS[0])
    assert articles == []  # one-shot, did not loop


# ---------------------------------------------------------------------------
# confirmation gate
# ---------------------------------------------------------------------------


def _art(domain: str, when: datetime) -> GdeltArticle:
    return GdeltArticle(
        title="t",
        url=f"https://{domain}/x",
        domain=domain,
        seendate=when,
    )


def test_confirm_single_domain_returns_empty():
    now = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)
    arts = [_art("a.com", now), _art("a.com", now)]
    assert confirm_articles(arts, min_unique_domains=2, now=now) == []


def test_confirm_two_domains_passes():
    now = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)
    arts = [_art("a.com", now), _art("b.com", now - timedelta(minutes=10))]
    out = confirm_articles(arts, min_unique_domains=2, now=now)
    assert len(out) == 2


def test_confirm_drops_stale_articles_outside_window():
    now = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)
    arts = [
        _art("a.com", now - timedelta(hours=3)),
        _art("b.com", now - timedelta(hours=3)),
    ]
    assert confirm_articles(arts, min_unique_domains=2, window_minutes=60, now=now) == []


# ---------------------------------------------------------------------------
# GDACS
# ---------------------------------------------------------------------------


def _feature(eventid=1, eventtype="EQ", alertlevel="Orange", country="Japan"):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [143.0, 39.9]},
        "properties": {
            "eventid": eventid,
            "episodeid": 1,
            "eventtype": eventtype,
            "eventname": "test",
            "description": "Earthquake test",
            "alertlevel": alertlevel,
            "alertscore": 2.0,
            "fromdate": "2026-04-20T07:53:00",
            "todate": "2026-04-20T07:53:00",
            "datemodified": "2026-04-20T08:00:00",
            "country": country,
            "iso3": "JPN",
            "severitydata": {"severity": 7.4, "severitytext": "M 7.4", "severityunit": "M"},
        },
    }


async def test_gdacs_parses_feature_collection():
    body = {"type": "FeatureCollection", "features": [_feature(), _feature(eventid=2)]}
    client = GdacsClient(transport=_transport_returning(200, body), max_retries=1, days_back=30)
    records = await client.fetch_recent()
    assert len(records) == 2
    r = records[0]
    assert isinstance(r, GdacsRecord)
    assert r.alertlevel == "Orange"
    assert r.coordinates == (143.0, 39.9)
    assert r.severity == 7.4
    assert r.country == "Japan"


async def test_gdacs_retries_on_503():
    body = json.dumps({"features": []})
    transport = _transport_sequence(
        httpx.Response(503),
        httpx.Response(200, text=body),
    )
    client = GdacsClient(transport=transport, max_retries=3)
    records = await client.fetch_recent()
    assert records == []


async def test_gdacs_handles_malformed_feature():
    body = {"features": [{"properties": {}}]}  # missing eventid
    client = GdacsClient(transport=_transport_returning(200, body), max_retries=1)
    records = await client.fetch_recent()
    assert records == []
