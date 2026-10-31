import socket
from unittest.mock import patch
import pytest
import requests
from veritylens.collector import (
    CollectionError, validate_public_url, extract_html, manual_source, collect_url,
    search_wikipedia, _bounded_get, MAX_BYTES,
)


@pytest.mark.parametrize("url", [
    "file:///etc/passwd", "http://localhost/", "http://127.0.0.1/",
    "http://10.2.3.4/", "http://169.254.169.254/latest/meta-data/",
    "http://8.8.8.8:8888/", "http://user:password@example.com/",
    "garbage", "http://[::1]/",
])
def test_rejects_unsafe_urls(url):
    with pytest.raises(CollectionError):
        validate_public_url(url)


def test_dns_resolution_to_private_ip_is_rejected():
    with patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.11", 80))]):
        with pytest.raises(CollectionError, match="nonpublic"):
            validate_public_url("https://some-resolvable-domain.example/")


def test_reads_html_and_visible_metadata():
    page = (b'<html><head><title>Example Notice</title><meta property="article:published_time" '
            b'content="2026-09-01"/></head><body><main><p>Document eligibility is based '
            b'on verified academic programme enrollment and completion.</p></main></body></html>')
    title, text, published = extract_html(page, "https://example.com")
    assert title == "Example Notice"
    assert "eligibility" in text
    assert published == "2026-09-01"


def test_manual_text_does_not_claim_an_authenticated_source():
    source = manual_source("S1", "Pasted notice", "Here is some information.")
    assert source.url is None
    assert "not authenticated" in source.extraction_note
    assert source.collected_at and source.collected_at.endswith("Z")


def test_extracts_same_host_canonical_and_leaves_missing_date_unknown():
    page = (
        b'<html><head><title>Notice</title><link rel="canonical" '
        b'href="/official/notice"></head><body><main><p>Current guidance text '
        b'contains enough readable information for extraction.</p></main></body></html>'
    )
    from veritylens.collector import _extract_html_details

    title, text, published, modified, canonical, truncated = _extract_html_details(
        page, "https://example.org/page?ref=1"
    )
    assert title == "Notice"
    assert "Current guidance" in text
    assert published is None
    assert modified is None
    assert canonical == "https://example.org/official/notice"
    assert not truncated


def test_malformed_canonical_metadata_does_not_discard_readable_page():
    page = (
        b'<html><head><title>Notice</title><link rel="canonical" '
        b'href="https://[malformed"></head><body><main><p>'
        b'Current eligibility information and application instructions are provided here.'
        b'</p></main></body></html>'
    )
    from veritylens.collector import _extract_html_details

    title, text, published, modified, canonical, truncated = _extract_html_details(
        page, "https://example.org/page"
    )
    assert title == "Notice"
    assert "eligibility" in text
    assert published is None and modified is None
    assert canonical is None
    assert not truncated


def test_collect_url_records_retrieval_and_page_metadata(monkeypatch):
    page = (
        b'<html><head><title>Current Notice</title><meta name="date" content="2026-10-01">'
        b'<link rel="canonical" href="/current"></head><body><main><p>'
        b'Current eligibility information and application instructions are provided here.'
        b'</p></main></body></html>'
    )
    session = FakeSession([FakeResponse(200, {"Content-Type": "text/html"}, [page])])
    monkeypatch.setattr("veritylens.collector.requests.Session", lambda: session)
    monkeypatch.setattr("veritylens.collector.validate_public_url", lambda url: url)
    monkeypatch.setattr("veritylens.collector._robots_allowed", lambda *_: True)

    source = collect_url("https://example.org/notice", "S1")
    assert source.url == "https://example.org/notice"
    assert source.canonical_url == "https://example.org/current"
    assert source.published_at == "2026-10-01"
    assert source.collected_at and source.collected_at.endswith("Z")


def test_collect_url_keeps_publication_and_modification_dates_distinct(monkeypatch):
    page = (
        b'<html><head><title>Updated Notice</title>'
        b'<meta property="article:modified_time" content="2026-10-01T10:00:00Z">'
        b'</head><body><main><p>Current eligibility information and application '
        b'instructions are provided here.</p></main></body></html>'
    )
    session = FakeSession([FakeResponse(200, {"Content-Type": "text/html"}, [page])])
    monkeypatch.setattr("veritylens.collector.requests.Session", lambda: session)
    monkeypatch.setattr("veritylens.collector.validate_public_url", lambda url: url)
    monkeypatch.setattr("veritylens.collector._robots_allowed", lambda *_: True)

    source = collect_url("https://example.org/notice", "S1")
    assert source.published_at is None
    assert source.modified_at == "2026-10-01T10:00:00Z"


def test_http_timeout_is_reported_as_collection_error():
    class TimeoutSession:
        def get(self, *_args, **_kwargs):
            raise requests.Timeout()

    with pytest.raises(CollectionError, match="timed out"):
        _bounded_get(TimeoutSession(), "http://8.8.8.8/")


def test_paywall_response_is_reported_without_reading_page():
    session = FakeSession([FakeResponse(403, {"Content-Type": "text/html"})])
    with pytest.raises(CollectionError, match="paywall"):
        _bounded_get(session, "http://8.8.8.8/")


def test_pasted_text_truncation_is_disclosed():
    source = manual_source("S1", "Long source", "x" * 100_001)
    assert len(source.text) == 100_000
    assert "truncated" in source.extraction_note.lower()


def test_wikipedia_search_returns_attributed_article_and_revision_metadata(monkeypatch):
    class JsonResponse:
        status_code = 200
        headers = {"Content-Type": "application/json"}

        def __init__(self, payload):
            import json

            self.body = json.dumps(payload).encode()
            self.closed = False

        def iter_content(self, chunk_size):
            yield self.body

        def close(self):
            self.closed = True

    responses = iter([
        JsonResponse({"query": {"search": [{
            "pageid": 123, "title": "Mars", "timestamp": "2026-10-25T10:00:00Z",
        }]}}),
        JsonResponse({
            "query": {
                "pages": [{
                    "pageid": 123,
                    "title": "Mars",
                    "fullurl": "https://en.wikipedia.org/wiki/Mars",
                    "canonicalurl": "https://en.wikipedia.org/wiki/Mars",
                    "extract": "Mars is the fourth planet from the Sun. " * 10,
                }],
            },
        }),
    ])
    request_data = []

    def fake_get(url, **kwargs):
        request_data.append({"url": url, **kwargs})
        return next(responses)

    monkeypatch.setattr("veritylens.collector.requests.get", fake_get)
    sources, failures = search_wikipedia("Mars", limit=3)

    assert not failures
    assert len(sources) == 1
    source = sources[0]
    assert source.collection_method == "wikipedia_search"
    assert source.url == source.canonical_url == "https://en.wikipedia.org/wiki/Mars"
    assert source.modified_at == "2026-10-25T10:00:00Z"
    assert source.published_at is None
    assert "not an authoritative source" in source.extraction_note
    assert len(request_data) == 2
    assert all(call["url"] == "https://en.wikipedia.org/w/api.php" for call in request_data)
    assert request_data[0]["params"]["srsearch"] == "Mars"
    assert request_data[1]["params"]["pageids"] == "123"
    assert request_data[1]["params"]["exchars"] <= 1200
    assert all(call["allow_redirects"] is False for call in request_data)


@pytest.mark.parametrize("query", ["", "x" * 301])
def test_wikipedia_search_rejects_empty_or_oversized_query(query):
    with pytest.raises(CollectionError):
        search_wikipedia(query)


def test_wikipedia_search_rejects_noncanonical_article_urls(monkeypatch):
    class JsonResponse:
        status_code = 200
        headers = {"Content-Type": "application/json"}

        def iter_content(self, chunk_size):
            import json

            payload = {
                "query": {
                    "pages": [{
                        "title": "Unsafe",
                        "fullurl": "https://attacker.example/redirect",
                        "extract": "A substantial article extract. " * 10,
                    }],
                },
            }
            yield json.dumps(payload).encode()

        def close(self):
            pass

    class SearchResponse(JsonResponse):
        def iter_content(self, chunk_size):
            import json

            yield json.dumps({"query": {"search": [{"pageid": 7, "title": "Unsafe"}]}}).encode()

    responses = iter([SearchResponse(), JsonResponse()])
    monkeypatch.setattr("veritylens.collector.requests.get", lambda *_args, **_kwargs: next(responses))
    sources, failures = search_wikipedia("example")
    assert not sources
    assert failures and "noncanonical" in failures[0]


class FakeResponse:
    def __init__(self, status, headers=None, chunks=None):
        self.status_code = status
        self.headers = headers or {}
        self.chunks = chunks or [b"short test text"]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("Not used in successful fixtures")

    def iter_content(self, chunk_size):
        yield from self.chunks


class FakeSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []
        self.headers = {}
        self.trust_env = True

    def get(self, url, **kwargs):
        self.requests.append(url)
        return next(self.responses)

    def close(self):
        pass


def test_redirect_to_private_host_is_blocked_before_request():
    session = FakeSession([FakeResponse(302, {"Location": "http://127.0.0.1/private"})])
    with pytest.raises(CollectionError, match="nonpublic"):
        _bounded_get(session, "http://8.8.8.8/")
    assert session.requests == ["http://8.8.8.8/"]


def test_huge_public_page_is_rejected_without_consuming_more():
    session = FakeSession([FakeResponse(200, {"Content-Type": "text/html"}, [b"x" * (MAX_BYTES + 1)])])
    with pytest.raises(CollectionError, match="too large"):
        _bounded_get(session, "http://8.8.8.8/")
