"""The Job ad fetcher's extraction and HTTP call. Pages are synthetic fixtures; no test touches the network."""

import io
import urllib.error
from pathlib import Path

import pytest

from ieakaso.job_ad import FetchError, NoAdError, UnreadableError, extract, fetch_page

FIXTURES = Path(__file__).parent / "fixtures" / "job_ads"
URL = "https://careers.example/jobs/1"


def page(name: str) -> str:
    return (FIXTURES / f"{name}.html").read_text("utf-8")


def expected(name: str) -> str:
    return (FIXTURES / "expected" / f"{name}.md").read_text("utf-8")


def with_ld_json(data: str, body: str = "") -> str:
    return f'<html><head><script type="application/ld+json">{data}</script></head><body>{body}</body></html>'


# Extraction paths: the expected Markdown is the spec.


@pytest.mark.parametrize("name", ["jsonld", "graph", "page_text"])
def test_extraction_matches_the_expected_markdown(name: str):
    assert extract(page(name), URL) == expected(name)


def test_the_same_page_gives_the_same_text():
    assert extract(page("jsonld"), URL) == extract(page("jsonld"), URL)


def test_structured_data_wins_over_the_page_body():
    assert "Loading the job details" not in extract(page("jsonld"), URL)


def test_a_json_ld_block_that_is_not_json_is_ignored():
    html = with_ld_json("{not json", "<main><h1>Plain ad</h1><p>" + "Words about the job. " * 20 + "</p></main>")

    assert extract(html, URL).startswith("Source: page text\n")


def test_a_json_ld_block_without_a_job_posting_falls_back_to_the_page_text():
    html = with_ld_json('{"@type": "Organization", "name": "Acme"}', "<p>" + "Words about the job. " * 20 + "</p>")

    assert extract(html, URL).startswith("Source: page text\n")


def test_a_job_posting_in_a_list_of_json_ld_objects_is_found():
    html = with_ld_json('[{"@type": "WebSite"}, {"@type": "JobPosting", "title": "Cook", "description": "Cook food."}]')

    out = extract(html, URL)

    assert out.startswith("Source: structured data\n")
    assert "# Cook" in out
    assert "Cook food." in out


def test_page_text_prefers_article_when_there_is_no_main():
    html = (
        "<body><p>Outside text.</p><article><h1>Chef</h1><p>" + "Cook food for guests. " * 20 + "</p></article></body>"
    )

    out = extract(html, URL)

    assert "# Chef" in out
    assert "Outside text." not in out


def test_page_text_uses_the_body_when_there_is_no_main_or_article():
    html = "<body><h1>Chef</h1><p>" + "Cook food for guests. " * 20 + "</p></body>"

    assert "# Chef" in extract(html, URL)


# Exit 2: not readable without the candidate.


def test_a_login_wall_is_unreadable():
    with pytest.raises(UnreadableError, match="login"):
        extract(page("login_wall"), URL)


def test_a_redirect_to_a_login_address_is_unreadable():
    html = "<body><p>Welcome back. Please continue.</p></body>"

    with pytest.raises(UnreadableError, match="login"):
        extract(html, "https://www.linkedin.example/authwall?trk=job")


def test_a_closed_ad_is_unreadable():
    with pytest.raises(UnreadableError, match="closed"):
        extract(page("closed"), URL)


@pytest.mark.parametrize(
    "sentence",
    [
        "This position has been filled.",
        "This job posting has expired.",
        "Applications are now closed.",
        "Diese Stelle ist leider nicht mehr verfügbar.",
        "Die Stelle wurde bereits besetzt.",
    ],
)
def test_closed_ad_wordings_are_recognised(sentence: str):
    with pytest.raises(UnreadableError, match="closed"):
        extract(f"<body><main><h1>Chef</h1><p>{sentence}</p></main></body>", URL)


# Exit 3: fetched, but no ad content.


def test_an_empty_shell_has_no_ad_content():
    with pytest.raises(NoAdError, match="no job ad"):
        extract(page("empty_shell"), URL)


def test_a_page_with_a_little_text_has_no_ad_content():
    with pytest.raises(NoAdError):
        extract("<body><main><p>Hello.</p></main></body>", URL)


def test_a_job_posting_without_a_title_or_description_has_no_ad_content():
    with pytest.raises(NoAdError):
        extract(with_ld_json('{"@type": "JobPosting", "hiringOrganization": {"name": "Acme"}}'), URL)


# The HTTP call: one GET, injectable opener.


class FakeResponse:
    def __init__(self, body: bytes, url: str = URL, charset: str | None = "utf-8"):
        self._body = body
        self._url = url
        self.headers = type("H", (), {"get_content_charset": lambda self_: charset})()

    def read(self, size: int = -1) -> bytes:
        return self._body

    def geturl(self) -> str:
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Opener:
    """Records requests and replays results (responses or exceptions) in order."""

    def __init__(self, *results):
        self.results = list(results)
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(URL, code, "status", {}, io.BytesIO(b""))  # type: ignore[arg-type]


def test_fetch_page_sends_one_get_with_a_browser_user_agent_and_a_timeout():
    opener = Opener(FakeResponse(b"<p>hi</p>"))

    result = fetch_page(URL, opener=opener)

    assert result.html == "<p>hi</p>"
    request, timeout = opener.requests[0]
    assert request.get_method() == "GET"
    assert request.full_url == URL
    assert "Mozilla" in request.get_header("User-agent")
    assert timeout
    assert request.get_header("Cookie") is None


def test_fetch_page_reports_the_final_address_after_redirects():
    opener = Opener(FakeResponse(b"<p>hi</p>", url="https://other.example/x"))

    assert fetch_page(URL, opener=opener).url == "https://other.example/x"


def test_fetch_page_decodes_with_the_declared_charset():
    opener = Opener(FakeResponse("<p>Größe</p>".encode("latin-1"), charset="latin-1"))

    assert fetch_page(URL, opener=opener).html == "<p>Größe</p>"


def test_a_client_error_fails_at_once_and_names_the_status():
    opener = Opener(http_error(404))

    with pytest.raises(FetchError, match="404"):
        fetch_page(URL, opener=opener)
    assert len(opener.requests) == 1


def test_a_server_error_is_retried_once():
    opener = Opener(http_error(503), FakeResponse(b"<p>ok</p>"))

    assert fetch_page(URL, opener=opener).html == "<p>ok</p>"
    assert len(opener.requests) == 2


def test_a_second_failure_is_reported():
    opener = Opener(http_error(503), http_error(503))

    with pytest.raises(FetchError, match="503"):
        fetch_page(URL, opener=opener)
    assert len(opener.requests) == 2


def test_a_network_error_is_retried_once_then_reported():
    opener = Opener(urllib.error.URLError("name not resolved"), urllib.error.URLError("name not resolved"))

    with pytest.raises(FetchError, match="[Nn]etwork"):
        fetch_page(URL, opener=opener)
    assert len(opener.requests) == 2


def test_a_timeout_is_reported():
    opener = Opener(TimeoutError("timed out"), TimeoutError("timed out"))

    with pytest.raises(FetchError, match="timed out"):
        fetch_page(URL, opener=opener)


def test_only_http_and_https_addresses_are_fetched():
    opener = Opener()

    with pytest.raises(FetchError, match="http"):
        fetch_page("file:///etc/passwd", opener=opener)
    assert opener.requests == []
