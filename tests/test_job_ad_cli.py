"""The job_ad command: the Job ad as Markdown on stdout, exit codes 0-3. The page fetch is injected."""

import pytest
from job_ad_fakes import URL, expected, page

from ieakaso.job_ad import FetchError, Page, cli


def fetcher(html: str, url: str = URL):
    return lambda requested: Page(url=url, html=html)


def failing(error: Exception):
    def fetch(requested):
        raise error

    return fetch


def test_exit_0_writes_the_ad_to_stdout(capsys: pytest.CaptureFixture[str]):
    assert cli.main(["fetch", URL], fetch=fetcher(page("jsonld"))) == 0

    captured = capsys.readouterr()
    assert captured.out == expected("jsonld")
    assert captured.err == ""


def test_the_first_line_names_the_source(capsys: pytest.CaptureFixture[str]):
    cli.main(["fetch", URL], fetch=fetcher(page("page_text")))

    assert capsys.readouterr().out.splitlines()[0] == "Source: page text"


def test_the_address_is_passed_to_the_fetch():
    seen = []

    def fetch(requested):
        seen.append(requested)
        return Page(url=requested, html=page("jsonld"))

    cli.main(["fetch", URL], fetch=fetch)

    assert seen == [URL]


def test_exit_1_when_the_fetch_fails(capsys: pytest.CaptureFixture[str]):
    code = cli.main(["fetch", URL], fetch=failing(FetchError("the server answered HTTP 404")))

    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert "HTTP 404" in captured.err


@pytest.mark.parametrize("name", ["login_wall", "closed"])
def test_exit_2_when_the_ad_needs_the_candidate(name: str, capsys: pytest.CaptureFixture[str]):
    code = cli.main(["fetch", URL], fetch=fetcher(page(name)))

    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    assert "paste" in captured.err


def test_exit_3_when_the_page_has_no_ad(capsys: pytest.CaptureFixture[str]):
    code = cli.main(["fetch", URL], fetch=fetcher(page("empty_shell")))

    captured = capsys.readouterr()
    assert code == 3
    assert captured.out == ""
    assert "paste" in captured.err


def test_a_page_cut_at_the_size_cap_is_reported_on_stderr(capsys: pytest.CaptureFixture[str]):
    code = cli.main(["fetch", URL], fetch=lambda requested: Page(url=URL, html=page("jsonld"), truncated=True))

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == expected("jsonld")
    assert "cut off" in captured.err
