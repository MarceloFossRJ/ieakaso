"""The Job ad fetcher's extraction and HTTP call. Pages are synthetic fixtures; no test touches the network."""

import urllib.error

import pytest
from job_ad_fakes import URL, FakeResponse, Opener, expected, http_error, page, with_ld_json

from ieakaso.job_ad import FetchError, NoAdError, UnreadableError, extract, fetch_page

# Extraction paths: the expected Markdown is the spec.


@pytest.mark.parametrize("name", ["jsonld", "jsonld_extra", "graph", "page_text"])
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
    with pytest.raises(NoAdError, match="no Job ad"):
        extract(page("empty_shell"), URL)


def test_a_page_with_a_little_text_has_no_ad_content():
    with pytest.raises(NoAdError):
        extract("<body><main><p>Hello.</p></main></body>", URL)


def test_a_job_posting_without_a_title_or_description_has_no_ad_content():
    with pytest.raises(NoAdError):
        extract(with_ld_json('{"@type": "JobPosting", "hiringOrganization": {"name": "Acme"}}'), URL)


# The HTTP call: one GET, injectable opener.


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


def test_lines_already_in_the_ad_are_not_repeated_in_more_from_the_page():
    out = extract(page("jsonld_extra"), URL).split("\n# ", 1)[1]  # the ad, after the Source and Page title lines

    assert out.count("Lead a team of eight engineers") == 1
    assert out.count("Engineering Manager, Platform") == 1


def test_no_more_from_the_page_section_when_the_page_adds_nothing():
    out = extract(page("jsonld"), URL)

    assert out.startswith("Source: structured data\n")
    assert "More from the page" not in out


def test_the_comparison_ignores_case_and_spacing():
    html = with_ld_json(
        '{"@type": "JobPosting", "title": "Cook", "description": "<p>Cook   food.</p>"}',
        "<main><p>COOK food.</p></main>",
    )

    assert "More from the page" not in extract(html, URL)


LONG_AD = "<h1>Chef</h1><p>" + "Cook food for guests every day. " * 20 + "</p>"


# Cookie and consent banners are skipped, but never the page itself.


def test_a_cookie_class_on_the_body_does_not_hide_the_ad():
    html = f'<html class="cookie-consent-loaded"><body class="has-cookie-consent"><main>{LONG_AD}</main></body></html>'

    assert "# Chef" in extract(html, URL)


def test_a_cookie_banner_inside_the_page_is_still_skipped():
    html = f'<body><div id="cookie-consent"><p>We use cookies.</p></div><main>{LONG_AD}</main></body>'

    assert "We use cookies" not in extract(html, URL)


# Closed ads: the wording counts in a notice or at the top of the page, not anywhere.


def test_a_passing_mention_of_closed_applications_further_down_is_not_a_closed_ad():
    html = f"<main>{LONG_AD}<p>Applications are closed for our 2025 internship programme.</p></main>"

    assert extract(html, URL).startswith("Source: page text")


def test_a_closed_notice_far_down_the_page_is_a_closed_ad():
    html = f'<main>{LONG_AD}<div class="notice"><p>This job is no longer available.</p></div></main>'

    with pytest.raises(UnreadableError, match="closed"):
        extract(html, URL)


def test_a_notice_role_counts_as_a_notice():
    html = f'<main>{LONG_AD}<div role="alert">This position has been filled.</div></main>'

    with pytest.raises(UnreadableError, match="closed"):
        extract(html, URL)


def test_a_closed_notice_on_a_page_with_structured_data_is_a_closed_ad():
    html = with_ld_json(
        '{"@type": "JobPosting", "title": "Cook", "description": "Cook food."}',
        '<main><div class="notice">This job is no longer available.</div></main>',
    )

    with pytest.raises(UnreadableError, match="closed"):
        extract(html, URL)


# A JobPosting without a description keeps its details and takes the page text as the body.


def test_a_job_posting_without_a_description_uses_the_page_text_as_the_body():
    html = with_ld_json(
        '{"@type": "JobPosting", "title": "Chef", "hiringOrganization": {"name": "Acme"}}',
        f"<main>{LONG_AD}</main>",
    )

    out = extract(html, URL)

    assert out.startswith("Source: structured data + page text\n\n# Chef\n\n- **Company:** Acme\n")
    assert "Cook food for guests every day." in out


# What the page repeats from the structured data is left out, however its lines are wrapped.


def test_a_sentence_wrapped_differently_on_the_page_is_not_repeated():
    html = with_ld_json(
        '{"@type": "JobPosting", "title": "Cook", "description": "<p>Cook food.<br>Wash up.</p>"}',
        "<main><p>Cook food. Wash up.</p></main>",
    )

    assert "More from the page" not in extract(html, URL)


def test_only_the_new_sentences_of_a_partly_repeated_paragraph_are_kept():
    html = with_ld_json(
        '{"@type": "JobPosting", "title": "Cook", "description": "<p>Cook food.</p>"}',
        "<main><p>Cook food. Contact person is Alex.</p></main>",
    )

    out = extract(html, URL)

    assert out.endswith("## More from the page\n\nContact person is Alex.\n")


# Heading levels: the description sits at ### or deeper, below the extra section's ##.


def test_description_headings_never_reach_the_level_of_the_extra_section():
    html = with_ld_json(
        '{"@type": "JobPosting", "title": "Cook", "description": "<h1>Big</h1><h2>Role</h2><p>Cook food.</p>"}'
    )

    out = extract(html, URL)

    assert "\n### Big\n" in out
    assert "\n### Role\n" in out


def test_a_heading_with_only_a_deeper_heading_under_it_is_kept():
    html = with_ld_json(
        '{"@type": "JobPosting", "title": "Cook", "description": "<p>Cook food.</p>"}',
        "<main><h3>Benefits</h3><h4>Time off</h4><p>Thirty days.</p></main>",
    )

    out = extract(html, URL)

    assert "### Benefits\n\n#### Time off\n\nThirty days." in out


def test_a_page_over_the_size_cap_is_cut_and_marked(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("ieakaso.job_ad.fetch.MAX_BYTES", 10)
    opener = Opener(FakeResponse(b"<p>" + b"x" * 50))

    result = fetch_page(URL, opener=opener)

    assert result.truncated
    assert len(result.html) == 10


def test_a_page_under_the_size_cap_is_not_marked():
    assert not fetch_page(URL, opener=Opener(FakeResponse(b"<p>hi</p>"))).truncated


# The page's <title> follows the Source line: it often names the company when the ad doesn't.


def test_the_page_title_is_the_second_line():
    html = f"<html><head><title>Chef @ Example Bistro</title></head><body><main>{LONG_AD}</main></body></html>"

    assert extract(html, URL).split("\n")[:3] == ["Source: page text", "", "Page title: Chef @ Example Bistro"]


def test_the_page_title_is_written_with_structured_data_too():
    data = '{"@type": "JobPosting", "title": "Chef", "description": "<p>Cook food for guests every day.</p>"}'
    html = with_ld_json(data).replace("<head>", "<head><title>Chef | Example Bistro Careers</title>")

    assert extract(html, URL).split("\n")[2] == "Page title: Chef | Example Bistro Careers"


def test_the_page_title_is_whitespace_normalized():
    html = f"<html><head><title>\n  Chef\n  - Example   Bistro </title></head><body>{LONG_AD}</body></html>"

    assert "Page title: Chef - Example Bistro\n" in extract(html, URL)


def test_no_page_title_line_without_a_title():
    html = f"<html><head><title>  </title></head><body>{LONG_AD}</body></html>"

    assert "Page title:" not in extract(html, URL)


# A page header can hold the ad's title and details; its navigation is still skipped.


def test_a_page_header_is_read():
    html = (
        f"<body><header><h1>Chef</h1><p>Full time</p></header><p>{'Cook food for guests every day. ' * 20}</p></body>"
    )

    out = extract(html, URL)

    assert "# Chef" in out
    assert "Full time" in out


def test_navigation_inside_a_header_is_still_skipped():
    html = f'<body><header><nav><a href="/">Home</a></nav></header>{LONG_AD}</body>'

    assert "Home" not in extract(html, URL)


# Inline elements that touch keep their words apart, as a browser shows them laid out.


def test_touching_inline_elements_get_a_space_between_their_words():
    html = f"<body>{LONG_AD}<p><span>Cost Centers</span><span>Technology</span><span>T4B</span></p></body>"

    assert "Cost Centers Technology T4B" in extract(html, URL)


def test_text_glued_to_a_tag_stays_glued():
    html = f'<body>{LONG_AD}<p>See <a href="#">our values</a>. Join <b>us</b>!</p></body>'

    assert "See our values. Join us!" in extract(html, URL)


def test_an_element_glued_to_punctuation_stays_glued():
    html = f"<body>{LONG_AD}<p><b>Salary:</b><span>(EUR)</span></p></body>"

    assert "Salary:(EUR)" in extract(html, URL)


def test_only_the_first_title_element_is_the_page_title():
    html = f"<html><head><title>Chef @ Example Bistro</title></head><body>{LONG_AD}<svg><title>Icon</title></svg></body></html>"

    assert "Page title: Chef @ Example Bistro\n" in extract(html, URL)
