"""Extract Table 3 of the MemoryAgentBench paper (arXiv 2507.05257v4) into results/paper_table3.csv.

The paper's numbers are parsed from arXiv's HTML rendering of the paper, so none is typed by hand.
They are reference values only: the paper's systems ran on GPT-4o-mini, ours on Claude Haiku 5.5.

    python -m data.paper_reference
"""

import csv
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

URL = "https://arxiv.org/html/2507.05257v4"
OUT = Path(__file__).resolve().parent.parent / "results" / "paper_table3.csv"
COLUMNS = ["SH-QA", "MH-QA", "LME(S*)", "EventQA", "AR Avg", "MCC", "Recom", "TTL Avg", "Summ", "DetQA",
           "LRU Avg", "FC-SH", "FC-MH", "SF Avg", "Overall"]


class TableRows(HTMLParser):
    """Collects the text of every table row on the page, cell by cell, per table."""

    def __init__(self):
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables.append([])
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.row is not None and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None and self.tables:
            self.tables[-1].append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def _numbers(cells: list[str]) -> list[str]:
    return [c for c in cells[1:] if re.fullmatch(r"\d+(\.\d+)?", c)]


def parse_table3(html: str) -> list[dict]:
    """Table 3 is the only table whose system rows carry all 15 score columns."""
    parser = TableRows()
    parser.feed(html)
    table = max(parser.tables, key=lambda t: sum(len(_numbers([c for c in r if c])) == len(COLUMNS) for r in t))
    rows, family = [], None
    for cells in table:
        cells = [c for c in cells if c]
        numbers = _numbers(cells)
        if len(cells) == 1 and cells[0].endswith("Agents"):
            family = cells[0]
        elif len(numbers) == len(COLUMNS):
            rows.append({"System": cells[0], "Family": family, **dict(zip(COLUMNS, map(float, numbers)))})
    return rows


def main() -> None:
    html = urllib.request.urlopen(URL, timeout=60).read().decode("utf-8")
    rows = parse_table3(html)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["System", "Family", *COLUMNS])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows from {URL} to {OUT}")


if __name__ == "__main__":
    main()
