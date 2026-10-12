"""One plain GET: a browser-like User-Agent, a timeout, no cookies kept, one retry. Sends nothing else."""

import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from ieakaso.job_ad.errors import FetchError

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
TIMEOUT_SECONDS = 20
MAX_BYTES = 5_000_000


@dataclass(frozen=True)
class Page:
    url: str  # the address the page came from, after any redirects
    html: str


def fetch_page(url: str, opener: Callable | None = None) -> Page:
    """GET url and return the page. Retries once on a network error, a timeout or an HTTP 5xx."""
    if not url.lower().startswith(("http://", "https://")):
        raise FetchError(f"Only http and https addresses can be fetched, not {url!r}.")
    open_url = opener or urllib.request.urlopen
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}, method="GET"
    )
    error = FetchError("The fetch did not run.")
    for _attempt in range(2):
        try:
            with open_url(request, timeout=TIMEOUT_SECONDS) as response:
                body = response.read(MAX_BYTES)
                return Page(url=response.geturl(), html=_decode(body, response.headers.get_content_charset()))
        except urllib.error.HTTPError as http_error:
            error = FetchError(f"The server answered HTTP {http_error.code} for {url}.")
            if http_error.code < 500:
                break
        except urllib.error.URLError as url_error:
            if isinstance(url_error.reason, TimeoutError):
                error = FetchError(f"The request to {url} timed out after {TIMEOUT_SECONDS} seconds.")
            else:
                error = FetchError(f"Network error fetching {url}: {url_error.reason}.")
        except TimeoutError:
            error = FetchError(f"The request to {url} timed out after {TIMEOUT_SECONDS} seconds.")
        except OSError as os_error:
            error = FetchError(f"Network error fetching {url}: {os_error}.")
    raise error


def _decode(body: bytes, charset: str | None) -> str:
    try:
        return body.decode(charset or "utf-8", errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")
