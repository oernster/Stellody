"""Write each page's last change into the sitemap, read from the history.

A `lastmod` is the only signal a sitemap carries beyond its list of URLs; a
wrong one is worse than none, since a crawler that finds the date disagreeing
with the page stops believing the file. So it is derived rather than typed, from
the last commit that touched each page, then stamped by the build exactly as the
version is. Nobody has to remember it and nobody can get it wrong by hand.

It is machine metadata, which is the one thing the no-visible-dates rule for
these sites exempts: nothing here reaches a reader.

Run it directly to refresh the file; the build scripts call `main` themselves.
Where git cannot be asked, every date is left exactly as it stands, since a
guess would be the thing this exists to prevent.
"""

from __future__ import annotations

import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
SITE_DIR = ROOT / "docs"
SITEMAP = SITE_DIR / "sitemap.xml"
SITE_URL = "https://stellody.co.uk/"
HOME_PAGE = "index.html"
URL_PATTERN = re.compile(
    r"<url>\s*<loc>([^<]+)</loc>(?:\s*<lastmod>[^<]*</lastmod>)?\s*</url>"
)


def page_for(url: str) -> str:
    """The file a listed URL is served from; the home page for the bare host."""
    tail = url.removeprefix(SITE_URL)
    return tail or HOME_PAGE


def last_changed(page: str) -> str:
    """The date of the last commit touching that page, empty when unknown."""
    try:
        answer = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", f"docs/{page}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    return answer.stdout.strip() if answer.returncode == 0 else ""


def stamped(text: str) -> tuple[str, list[str]]:
    """The sitemap with every date refreshed, plus what was refreshed."""
    touched: list[str] = []

    def one(found: re.Match) -> str:
        url = found.group(1)
        page = page_for(url)
        when = last_changed(page)
        if not when:
            return found.group(0)
        touched.append(f"{page} {when}")
        return f"<url><loc>{url}</loc><lastmod>{when}</lastmod></url>"

    return URL_PATTERN.sub(one, text), touched


def main() -> None:
    """Refresh the sitemap in place, saying what it wrote."""
    if not SITEMAP.exists():
        print("no sitemap to stamp")
        return
    before = SITEMAP.read_text(encoding="utf-8")
    after, touched = stamped(before)
    if after == before:
        print("sitemap already current")
        return
    SITEMAP.write_text(after, encoding="utf-8")
    print("stamped into the sitemap:")
    for line in touched:
        print(f"  {line}")


if __name__ == "__main__":
    main()
