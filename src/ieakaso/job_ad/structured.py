"""The schema.org JobPosting in a page's <script type="application/ld+json">, as Markdown."""

import html
import json
from dataclasses import dataclass
from html.parser import HTMLParser

from ieakaso.job_ad.markdown import to_markdown

UNITS = {"HOUR": "hour", "DAY": "day", "WEEK": "week", "MONTH": "month", "YEAR": "year"}


@dataclass(frozen=True)
class AdData:
    markdown: str  # the ad's details and text, as Markdown
    has_description: bool  # the JobPosting held a description; if not, the page text has to supply the body


class _LdJson(HTMLParser):
    """Collects the text of every <script type="application/ld+json"> in a page."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.blocks: list[str] = []
        self._open = False

    def handle_starttag(self, tag, attrs):
        if tag == "script" and (dict(attrs).get("type") or "").lower().split(";")[0].strip() == "application/ld+json":
            self._open = True
            self.blocks.append("")

    def handle_endtag(self, tag):
        if tag == "script":
            self._open = False

    def handle_data(self, data):
        if self._open:
            self.blocks[-1] += data


def job_posting(page_html: str) -> dict | None:
    """The first schema.org JobPosting in the page's ld+json blocks (alone, in a list or in a @graph), or None."""
    scanner = _LdJson()
    scanner.feed(page_html)
    scanner.close()
    for block in scanner.blocks:
        try:
            data = json.loads(block, strict=False)
        except ValueError:
            continue
        found = _find(data)
        if found is not None:
            return found
    return None


def _find(node) -> dict | None:
    """The JobPosting object in parsed ld+json: the node itself, or one inside a list or a @graph."""
    if isinstance(node, list):
        for item in node:
            found = _find(item)
            if found is not None:
                return found
    elif isinstance(node, dict):
        kinds = node.get("@type")
        if "JobPosting" in (kinds if isinstance(kinds, list) else [kinds]):
            return node
        return _find(node.get("@graph"))
    return None


def ad_data(job: dict) -> AdData | None:
    """The ad in a JobPosting as Markdown, or None when it holds nothing to show."""
    description = _description(job.get("description"))
    parts = []
    title = _text(job.get("title"))
    if title:
        parts.append(f"# {title}")
    details = [
        ("Company", _field(job.get("hiringOrganization"), "name")),
        ("Location", _locations(job)),
        ("Employment type", _employment_types(job.get("employmentType"))),
        ("Posted", _text(job.get("datePosted"))),
        ("Valid through", _text(job.get("validThrough"))),
        ("Salary", _salary(job.get("baseSalary"))),
        ("Reference", _field(job.get("identifier"), "value")),
    ]
    lines = [f"- **{label}:** {value}" for label, value in details if value]
    if lines:
        parts.append("\n".join(lines))
    organization = job.get("hiringOrganization")
    about = _description(organization.get("description")) if isinstance(organization, dict) else ""
    if about:
        parts.append(about)
    if description:
        parts.append(description)
    if not parts:
        return None
    return AdData("\n\n".join(parts), has_description=bool(description))


def _description(value) -> str:
    """A description (HTML, escaped HTML or plain text) as Markdown, headings from ### down."""
    text = _text(value)
    if "<" not in text and "&lt;" in text:
        text = html.unescape(text)
    if "<" not in text:
        text = "".join(f"<p>{html.escape(chunk.strip())}</p>" for chunk in text.split("\n\n"))
    return to_markdown(text, min_level=3)


def _text(value) -> str:
    """A string, number as text, stripped; anything else (None, objects, booleans) as an empty string."""
    if isinstance(value, bool) or value is None:
        return ""
    if isinstance(value, (str, int, float)):
        return str(value).strip()
    return ""


def _field(value, key: str) -> str:
    """value[key] as text when value is an object, else value itself as text (a name or an id may be either)."""
    return _text(value.get(key)) if isinstance(value, dict) else _text(value)


def _locations(job: dict) -> str:
    """The places of the job, with Remote when the ad says so, separated by semicolons."""
    places = job.get("jobLocation")
    places = places if isinstance(places, list) else [places]
    found = []
    for place in places:
        name = _place(place)
        if name and name not in found:
            found.append(name)
    if _text(job.get("jobLocationType")).upper() == "TELECOMMUTE":
        found.append("Remote")
    return "; ".join(found)


def _place(place) -> str:
    """One place as `locality, region, country`."""
    if not isinstance(place, dict):
        return _text(place)
    address = place.get("address")
    if isinstance(address, dict):
        country = address.get("addressCountry")
        country = country.get("name") if isinstance(country, dict) else country
        parts = [_text(address.get("addressLocality")), _text(address.get("addressRegion")), _text(country)]
        return ", ".join(part for part in parts if part)
    return _text(address) or _text(place.get("name"))


def _employment_types(value) -> str:
    """FULL_TIME or a list of them as `Full time, Contractor`."""
    values = value if isinstance(value, list) else [value]
    names = [_text(item).replace("_", " ").lower().capitalize() for item in values if _text(item)]
    return ", ".join(names)


def _salary(value) -> str:
    """A MonetaryAmount as `90000-110000 EUR per year`; empty when there is no figure."""
    if not isinstance(value, dict):
        return ""
    amount = value.get("value")
    if isinstance(amount, dict):
        unit = amount.get("unitText")
        low, high = _number(amount.get("minValue")), _number(amount.get("maxValue"))
        single = _number(amount.get("value"))
        figure = f"{low}-{high}" if low and high else low or high or single
    else:
        unit = value.get("unitText")
        figure = _number(amount)
    if not figure:
        return ""
    text = figure
    currency = _text(value.get("currency"))
    if currency:
        text += f" {currency}"
    unit = _text(unit).upper()
    if unit:
        text += f" per {UNITS.get(unit, unit.lower())}"
    return text


def _number(value) -> str:
    """A number as text without a trailing .0; empty when it is not a number."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()
