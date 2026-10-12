"""The schema.org JobPosting in a page's <script type="application/ld+json">, as Markdown."""

import html
import json
from html.parser import HTMLParser

from ieakaso.job_ad.markdown import to_markdown

UNITS = {"HOUR": "hour", "DAY": "day", "WEEK": "week", "MONTH": "month", "YEAR": "year"}


class _LdJson(HTMLParser):
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
    """The first JobPosting in the page's ld+json blocks (alone, in a list or in a @graph), or None."""
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


def posting_markdown(posting: dict) -> str | None:
    """The ad as Markdown, or None when the posting has no description to read."""
    body = _description(posting.get("description"))
    if not body:
        return None
    parts = []
    title = _text(posting.get("title"))
    if title:
        parts.append(f"# {title}")
    details = [
        ("Company", _organization(posting.get("hiringOrganization"))),
        ("Location", _locations(posting)),
        ("Employment type", _employment_types(posting.get("employmentType"))),
        ("Posted", _text(posting.get("datePosted"))),
        ("Valid through", _text(posting.get("validThrough"))),
        ("Salary", _salary(posting.get("baseSalary"))),
        ("Reference", _identifier(posting.get("identifier"))),
    ]
    lines = [f"- **{label}:** {value}" for label, value in details if value]
    if lines:
        parts.append("\n".join(lines))
    organization = posting.get("hiringOrganization")
    about = _description(organization.get("description")) if isinstance(organization, dict) else ""
    if about:
        parts.append(about)
    parts.append(body)
    return "\n\n".join(parts)


def _description(value) -> str:
    text = _text(value)
    if "<" not in text and "&lt;" in text:
        text = html.unescape(text)
    if "<" not in text:
        text = "".join(f"<p>{html.escape(chunk.strip())}</p>" for chunk in text.split("\n\n"))
    return to_markdown(text, min_level=2)


def _text(value) -> str:
    if isinstance(value, bool) or value is None:
        return ""
    if isinstance(value, (str, int, float)):
        return str(value).strip()
    return ""


def _organization(value) -> str:
    return _text(value.get("name")) if isinstance(value, dict) else _text(value)


def _locations(posting: dict) -> str:
    places = posting.get("jobLocation")
    places = places if isinstance(places, list) else [places]
    found = []
    for place in places:
        name = _place(place)
        if name and name not in found:
            found.append(name)
    if _text(posting.get("jobLocationType")).upper() == "TELECOMMUTE":
        found.append("Remote")
    return "; ".join(found)


def _place(place) -> str:
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
    values = value if isinstance(value, list) else [value]
    names = [_text(item).replace("_", " ").lower().capitalize() for item in values if _text(item)]
    return ", ".join(names)


def _salary(value) -> str:
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
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _identifier(value) -> str:
    return _text(value.get("value")) if isinstance(value, dict) else _text(value)
