import re
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


class ContributionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.dates = {}
        self.counts = {}
        self.tooltip_for = None

    def handle_starttag(self, tag, attributes):
        values = dict(attributes)
        if tag == "td" and values.get("data-date") and values.get("id"):
            self.dates[values["id"]] = values["data-date"]
        if tag == "tool-tip":
            self.tooltip_for = values.get("for")

    def handle_data(self, text):
        if self.tooltip_for:
            match = re.search(r"\b(No|[\d,]+) contributions? on\b", text)
            if match:
                self.counts[self.tooltip_for] = (
                    0 if match[1] == "No" else int(match[1].replace(",", ""))
                )

    def handle_endtag(self, tag):
        if tag == "tool-tip":
            self.tooltip_for = None


def render_activity(days):
    total = sum(count for _, count in days)
    active = sum(count > 0 for _, count in days)
    first = date.fromisoformat(days[0][0])
    last = date.fromisoformat(days[-1][0])
    colors = ["#212830", "#0e4429", "#006d32", "#26a641", "#39d353"]
    peak = max(count for _, count in days)
    cells = []
    for day, count in days:
        current = date.fromisoformat(day)
        offset = (current - first).days + (first.weekday() + 1) % 7
        level = 0 if count == 0 else min(4, 1 + int((count / max(peak, 1)) * 3))
        cells.append(
            f'<rect x="{28 + offset // 7 * 13}" y="{142 + offset % 7 * 13}" '
            f'width="10" height="10" rx="2" fill="{colors[level]}">'
            f'<title>{day}: {count} contributions</title></rect>'
        )
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="282" '
        'viewBox="0 0 760 282" role="img" aria-labelledby="title description">'
        '<title id="title">Ankit Agrawal — GitHub activity</title>'
        f'<desc id="description">{total:,} publicly visible contributions across '
        f'{active} active days, {first} to {last}. Updated {updated} UTC.</desc>'
        '<rect x="1" y="1" width="758" height="280" rx="14" '
        'fill="#0d1117" stroke="#30363d"/>'
        '<g font-family="Arial, Helvetica, sans-serif">'
        '<text x="28" y="38" fill="#f0f6fc" font-size="22" '
        'font-weight="700">GitHub contribution activity</text>'
        f'<text x="28" y="84" fill="#39d353" font-size="30" '
        f'font-weight="700">{total:,}</text>'
        '<text x="28" y="110" fill="#c9d1d9" font-size="14">contributions</text>'
        f'<text x="300" y="84" fill="#f0f6fc" font-size="30" '
        f'font-weight="700">{active}</text>'
        '<text x="300" y="110" fill="#c9d1d9" font-size="14">active days</text>'
        f'<text x="28" y="132" fill="#9198a1" font-size="12">{first} — {last}</text>'
        + "".join(cells)
        + f'<text x="28" y="263" fill="#9198a1" font-size="12">'
        f'Public GitHub calendar · Updated {updated} UTC · Not a commit count</text>'
        '</g></svg>\n'
    )


def main():
    request = Request(
        "https://github.com/users/ankitagr01/contributions",
        headers={"User-Agent": "ankitagr01-profile", "Accept-Language": "en-US"},
    )
    with urlopen(request, timeout=30) as response:
        source = response.read().decode("utf-8")
    parser = ContributionParser()
    parser.feed(source)
    if not 350 <= len(parser.dates) <= 380:
        raise ValueError("Unexpected calendar size; keeping the previous graphic")
    if set(parser.dates) != set(parser.counts):
        raise ValueError("Incomplete contribution counts; keeping the previous graphic")
    days = sorted((day, parser.counts[key]) for key, day in parser.dates.items())
    if len({day for day, _ in days}) != len(days):
        raise ValueError("Duplicate calendar dates; keeping the previous graphic")
    output = Path(__file__).resolve().parents[1] / "assets" / "github-activity.svg"
    output.parent.mkdir(exist_ok=True)
    output.write_text(render_activity(days), encoding="utf-8")
    print(f"Rendered {sum(count for _, count in days):,} contributions over {len(days)} days")


if __name__ == "__main__":
    main()
