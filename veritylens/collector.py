"""Public HTML collection with URL validation, redirect checks and safe limits.

Do not rely on this as a hardened internet crawler: DNS rebinding between validation
and HTTP connection is an acknowledged limitation (documented in README).
"""
from __future__ import annotations
import ipaddress
import json
import re
import socket
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from .models import Source

MAX_BYTES = 1_500_000
USER_AGENT = "VerityLensResearchDemo/0.1 (public-document analysis)"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"


class CollectionError(ValueError):
    """A source cannot safely or successfully be collected."""


def validate_public_url(url: str) -> str:
    """Reject loopback/private/special addresses and non-HTTP(S) URLs."""
    candidate = url.strip()
    try:
        parts = urlsplit(candidate)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            raise CollectionError("Only absolute HTTP/HTTPS links are supported.")
        if parts.username or parts.password:
            raise CollectionError("URLs with embedded credentials are not accepted.")
        if parts.port not in {None, 80, 443}:
            raise CollectionError("Nonstandard network ports are not accepted.")
        hostname = parts.hostname.rstrip(".")
        if hostname.lower() in {"localhost", "localhost.localdomain"}:
            raise CollectionError("Localhost is not allowed.")
        try:
            addresses = [ipaddress.ip_address(hostname)]
        except ValueError:
            addresses = [ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)]
        if not addresses or any(not address.is_global for address in addresses):
            raise CollectionError("Private, local, or otherwise nonpublic host blocked.")
    except (socket.gaierror, UnicodeError) as exc:
        raise CollectionError(f"Could not resolve a public destination: {exc}") from exc
    except ValueError as exc:
        if isinstance(exc, CollectionError):
            raise
        raise CollectionError(f"Malformed or disallowed URL: {exc}") from exc
    return candidate


def _bounded_get(session: requests.Session, url: str, *, check_html: bool = True) -> tuple[bytes, str, str]:
    current = url
    for _ in range(5):
        validate_public_url(current)
        try:
            with session.get(current, allow_redirects=False, stream=True, timeout=(4, 10)) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    destination = response.headers.get("Location")
                    if not destination:
                        raise CollectionError("Redirect did not contain a destination.")
                    current = urljoin(current, destination)
                    continue
                if response.status_code in {401, 402, 403}:
                    raise CollectionError("Access denied or paywall; this page cannot be retrieved.")
                if response.status_code >= 400:
                    raise CollectionError(f"Source returned HTTP {response.status_code}.")
                content_type = response.headers.get("Content-Type", "").lower()
                if check_html and not ("html" in content_type or "text/plain" in content_type):
                    raise CollectionError("Only public HTML and text pages are supported in this version.")
                data = bytearray()
                for chunk in response.iter_content(chunk_size=32768):
                    data.extend(chunk)
                    if len(data) > MAX_BYTES:
                        raise CollectionError("Page too large; maximum 1.5 MB.")
                return bytes(data), current, content_type
        except requests.Timeout as exc:
            raise CollectionError("Source request timed out.") from exc
        except requests.RequestException as exc:
            raise CollectionError("Source could not be fetched because of a network error.") from exc
    raise CollectionError("Too many redirects (limit: 5).")


def _robots_allowed(session: requests.Session, url: str) -> bool | None:
    parts = urlsplit(url)
    robot_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        raw, actual, _ = _bounded_get(session, robot_url, check_html=False)
        if urlsplit(actual).netloc != parts.netloc:
            return None
        parser = RobotFileParser()
        parser.parse(raw.decode("utf-8", "replace").splitlines())
        return parser.can_fetch(USER_AGENT, url)
    except CollectionError:
        return None  # Unknown policy, shown as a warning instead of invented approval.


def _extract_html_details(page: bytes, url: str) -> tuple[str, str, str | None, str | None, bool]:
    soup = BeautifulSoup(page, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else url
    canonical_url = None
    canonical = soup.select_one('link[rel~="canonical"][href]')
    if canonical:
        try:
            candidate = urljoin(url, canonical.get("href", "").strip())
            parts = urlsplit(candidate)
            original = urlsplit(url)
            same_host = (parts.hostname or "").casefold() == (original.hostname or "").casefold()
            safe_port = parts.port in {None, 80, 443}
            if (parts.scheme.lower() in {"http", "https"} and same_host and safe_port
                    and not parts.username and not parts.password):
                canonical_url = parts._replace(fragment="").geturl()
        except ValueError:
            pass
    published_at = None
    for selector in (
        'meta[property="article:published_time"]',
        'meta[name="date"]',
        'meta[name="pubdate"]',
    ):
        element = soup.select_one(selector)
        if element and element.get("content"):
            published_at = element["content"].strip()[:40]
            break
    modified_at = None
    for selector in (
        'meta[property="article:modified_time"]',
        'meta[name="last-modified"]',
    ):
        element = soup.select_one(selector)
        if element and element.get("content"):
            modified_at = element["content"].strip()[:40]
            break
    if not published_at:
        time_element = soup.select_one("time[datetime]")
        if time_element:
            published_at = time_element.get("datetime", "").strip()[:40] or None
    for elem in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
        elem.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    parts = [element.get_text(" ", strip=True) for element in main.find_all(["h1", "h2", "h3", "p", "li", "tr"])]
    content = "\n".join(x for x in parts if x and len(x) >= 5)
    if not content:
        content = main.get_text(" ", strip=True)
    content = re.sub(r"[ \t]+", " ", content)
    truncated = len(content) > 100_000
    content = content[:100_000]
    if len(content) < 60:
        raise CollectionError("No substantial readable text found in page.")
    return title[:180], content, published_at, modified_at, canonical_url, truncated


def extract_html(page: bytes, url: str) -> tuple[str, str, str | None]:
    title, content, published_at, _, _, _ = _extract_html_details(page, url)
    return title, content, published_at


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def collect_url(url: str, source_id: str) -> Source:
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": USER_AGENT})
    try:
        safe_url = validate_public_url(url)
        robots = _robots_allowed(session, safe_url)
        if robots is False:
            raise CollectionError("The site's robots.txt does not allow this crawler path.")
        raw, resolved, _ = _bounded_get(session, safe_url)
        title, text, published_at, modified_at, canonical, truncated = _extract_html_details(raw, resolved)
        notes = []
        if robots is None:
            notes.append("Robots policy could not be confirmed; check site terms before relying on this source.")
        if truncated:
            notes.append("Readable page text was truncated at the 100,000-character limit.")
        return Source(
            id=source_id, title=title, text=text, url=resolved, published_at=published_at,
            canonical_url=canonical, collected_at=_utc_timestamp(), modified_at=modified_at,
            collection_method="url",
            extraction_note=" ".join(notes),
        )
    finally:
        session.close()


def manual_source(source_id: str, title: str, text: str, published_at: str | None = None) -> Source:
    if not text.strip():
        raise CollectionError("Pasted source contains no text.")
    content = text.strip()
    note = "User-provided text; original publication not authenticated."
    if len(content) > 100_000:
        content = content[:100_000]
        note += " Text was truncated at the 100,000-character limit."
    return Source(
        id=source_id, title=title.strip()[:180] or f"Pasted source {source_id}",
        text=content, published_at=(published_at or "").strip() or None,
        collected_at=_utc_timestamp(), collection_method="manual",
        extraction_note=note,
    )


def _wikipedia_api_json(params: dict[str, str | int]) -> dict:
    try:
        response = requests.get(
            WIKIPEDIA_API,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=(4, 12),
            allow_redirects=False,
            stream=True,
        )
    except requests.Timeout as exc:
        raise CollectionError("Wikipedia search timed out.") from exc
    except requests.RequestException as exc:
        raise CollectionError("Wikipedia search could not be reached because of a network error.") from exc

    try:
        if response.status_code >= 300:
            raise CollectionError(f"Wikipedia search returned HTTP {response.status_code}.")
        content_type = response.headers.get("Content-Type", "").lower()
        if "json" not in content_type:
            raise CollectionError("Wikipedia search returned an unsupported content type.")
        data = bytearray()
        try:
            for chunk in response.iter_content(chunk_size=32768):
                data.extend(chunk)
                if len(data) > MAX_BYTES:
                    raise CollectionError("Wikipedia search response exceeded the size limit.")
        except requests.Timeout as exc:
            raise CollectionError("Wikipedia search timed out while reading results.") from exc
        except requests.RequestException as exc:
            raise CollectionError("Wikipedia search results could not be read.") from exc
        try:
            payload = json.loads(data)
        except (ValueError, UnicodeDecodeError) as exc:
            raise CollectionError("Wikipedia search returned invalid JSON.") from exc
    finally:
        response.close()

    if not isinstance(payload, dict):
        raise CollectionError("Wikipedia search returned an unsupported response.")
    if "error" in payload:
        raise CollectionError("Wikipedia API rejected the search request.")
    return payload


def search_wikipedia(query: str, *, limit: int = 3) -> tuple[list[Source], list[str]]:
    """Search English Wikipedia and retrieve short, attributed extracts for a research question."""
    normalized_query = query.strip()
    if not normalized_query:
        raise CollectionError("Enter a research question before searching Wikipedia.")
    if len(normalized_query) > 300:
        raise CollectionError("Wikipedia search queries must be 300 characters or fewer.")
    limit = max(1, min(int(limit), 3))
    search_payload = _wikipedia_api_json({
        "action": "query",
        "list": "search",
        "srsearch": normalized_query,
        "srlimit": limit,
        "srnamespace": 0,
        "format": "json",
        "formatversion": 2,
    })
    search_query = search_payload.get("query")
    if not isinstance(search_query, dict):
        raise CollectionError("Wikipedia search returned an unsupported response.")
    search_rows = search_query.get("search", [])
    if not isinstance(search_rows, list):
        raise CollectionError("Wikipedia search returned an unsupported response.")
    selected_rows = [
        row for row in search_rows[:limit]
        if isinstance(row, dict) and isinstance(row.get("pageid"), int)
    ]
    if not selected_rows:
        return [], ["Wikipedia search returned no matching articles."]
    sources: list[Source] = []
    failures: list[str] = []
    for search_row in selected_rows:
        page_id = search_row["pageid"]
        search_title = search_row.get("title", "Untitled article")
        try:
            details_payload = _wikipedia_api_json({
                "action": "query",
                "pageids": str(page_id),
                "prop": "extracts|info",
                "explaintext": 1,
                "exchars": 1200,
                "inprop": "url",
                "format": "json",
                "formatversion": 2,
            })
        except CollectionError as exc:
            failures.append(f"Could not retrieve Wikipedia article {str(search_title)[:120]}: {exc}")
            continue
        details_query = details_payload.get("query")
        if not isinstance(details_query, dict):
            failures.append(f"Wikipedia returned no article details for {str(search_title)[:120]}.")
            continue
        pages = details_query.get("pages", [])
        if not isinstance(pages, list) or not pages or not isinstance(pages[0], dict):
            failures.append(f"Wikipedia returned no article details for {str(search_title)[:120]}.")
            continue
        page = pages[0]
        title = page.get("title")
        text = page.get("extract")
        url = page.get("fullurl")
        if not isinstance(title, str) or not isinstance(text, str) or len(text.strip()) < 60:
            failures.append("A matching Wikipedia page had no substantial readable extract.")
            continue
        if not isinstance(url, str):
            failures.append(f"Wikipedia did not provide an article URL for {title[:120]}.")
            continue
        try:
            url_parts = urlsplit(url)
            url_port = url_parts.port
        except ValueError:
            failures.append(f"Wikipedia returned a malformed article URL for {title[:120]}; it was not used.")
            continue
        if (url_parts.scheme != "https" or url_parts.hostname != "en.wikipedia.org"
                or url_parts.username or url_parts.password or url_port not in {None, 443}):
            failures.append(f"Wikipedia returned a noncanonical article URL for {title[:120]}; it was not used.")
            continue
        modified_at = search_row.get("timestamp")
        if not isinstance(modified_at, str):
            modified_at = None
        canonical_url = page.get("canonicalurl")
        try:
            canonical_parts = urlsplit(canonical_url) if isinstance(canonical_url, str) else None
            canonical_host = canonical_parts.hostname if canonical_parts else None
            canonical_port = canonical_parts.port if canonical_parts else None
        except ValueError:
            canonical_host = None
            canonical_port = None
        if (canonical_host != "en.wikipedia.org" or canonical_port not in {None, 443}
                or not canonical_parts or canonical_parts.scheme != "https"
                or canonical_parts.username or canonical_parts.password):
            canonical_url = url
        sources.append(Source(
            id=f"W{len(sources) + 1}",
            title=title[:180],
            text=text[:100_000],
            url=url,
            canonical_url=canonical_url,
            collected_at=_utc_timestamp(),
            modified_at=modified_at,
            collection_method="wikipedia_search",
            extraction_note=(
                "Retrieved through English Wikipedia's public API for the submitted query. "
                "Wikipedia is collaboratively edited, not an authoritative source; verify important claims "
                "against the cited primary references. Page revision time is not a publication date."
            ),
        ))
    if not sources and not failures:
        failures.append("Wikipedia search returned no matching readable pages.")
    return sources, failures
