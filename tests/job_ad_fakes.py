"""Fixtures and fakes for the Job ad fetcher's tests: synthetic pages and anonymized Sample pages, no network."""

import io
import urllib.error
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "job_ads"
SAMPLES = FIXTURES / "samples"  # real Job ad pages, anonymized; their expected outputs are written by hand
URL = "https://careers.example/jobs/1"


def page(name: str) -> str:
    return (FIXTURES / f"{name}.html").read_text("utf-8")


def expected(name: str) -> str:
    return (FIXTURES / "expected" / f"{name}.md").read_text("utf-8")


def sample(name: str) -> str:
    return (SAMPLES / f"{name}.html").read_text("utf-8")


def sample_expected(name: str) -> str:
    return (SAMPLES / "expected" / f"{name}.md").read_text("utf-8")


def with_ld_json(data: str, body: str = "") -> str:
    return f'<html><head><script type="application/ld+json">{data}</script></head><body>{body}</body></html>'


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
