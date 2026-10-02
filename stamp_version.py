"""Write the version from VERSION into the site, wherever it is shown.

The site cannot read `VERSION` when a browser renders it, so each place that
shows a version carries a delimited token and this rewrites whatever sits
between the delimiters. That keeps VERSION the single place a real version
string lives: everything else either reads it or is stamped from it.

**The site only, deliberately.** No markdown document in this repository carries
a version at all, so nothing outside `docs/` is a target here. A stamper that
also wrote into README.md would be putting version data somewhere that has a
rule against holding any.

**Asset links too.** GitHub Pages lets a browser keep a stylesheet for ten
minutes, so a fresh page can arrive beside its stale CSS and render broken.
Every local `href="x.css"` or `src="x.js"` in a page therefore carries
`?v=<hash>` of the file's content: a changed file is a new address. The hash is
taken over the bytes with CRLF folded to LF, so a Windows checkout and the LF
blob GitHub serves agree and a rerun elsewhere does not churn every page.

Idempotent: stamping a file already at the current version changes nothing and
the file is left alone rather than rewritten, so a build does not churn the
tree. Run it from the repository root, else let a build script call `main()`.
"""

from __future__ import annotations

import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
VERSION_FILE = ROOT / "VERSION"
SITE_DIR = ROOT / "docs"
SITE_PATTERNS = ("**/*.html", "**/*.md")
OPEN_TOKEN = "<!--VERSION-->"
CLOSE_TOKEN = "<!--/VERSION-->"
TOKEN = re.compile(re.escape(OPEN_TOKEN) + r".*?" + re.escape(CLOSE_TOKEN), re.DOTALL)
DEV_VERSION = "0.0.0-dev"

ASSET_HASH_LENGTH = 10
# A stylesheet or script reference; any query it already has is replaced.
ASSET_LINK = re.compile(
    r"""(?<![\w-])((?:href|src)=)(["'])"""
    r"""([^"'?#]+\.(?:css|js))(?:\?[^"'#]*)?(#[^"']*)?\2"""
)
# Only relative paths are local files: a scheme, `//` or a leading `/` is not.
NOT_RELATIVE = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.-]*:|/)")


def read_version() -> str:
    """The version this repository is at; a sentinel when VERSION is absent."""
    try:
        text = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return DEV_VERSION
    return text or DEV_VERSION


def site_files() -> tuple[pathlib.Path, ...]:
    """Every page that could carry a token, in a stable order."""
    found: list[pathlib.Path] = []
    for pattern in SITE_PATTERNS:
        found.extend(SITE_DIR.glob(pattern))
    return tuple(sorted(set(found)))


def stamp(path: pathlib.Path, version: str) -> bool:
    """Put this version in every token in one file; True when it changed."""
    text = path.read_text(encoding="utf-8")
    stamped = TOKEN.sub(f"{OPEN_TOKEN}{version}{CLOSE_TOKEN}", text)
    if stamped == text:
        return False
    path.write_text(stamped, encoding="utf-8")
    return True


def asset_hash(path: pathlib.Path) -> str:
    """The content hash of one asset, with CRLF folded to LF first."""
    if not path.is_file():
        raise FileNotFoundError(f"a page links to a missing asset: {path}")
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()[:ASSET_HASH_LENGTH]


def version_assets(path: pathlib.Path) -> bool:
    """Put a content hash on every local asset link in one page; True if changed."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        text = handle.read()

    def _link(match: re.Match[str]) -> str:
        attribute, quote, target, fragment = match.groups()
        if NOT_RELATIVE.match(target):
            return match.group(0)
        digest = asset_hash(path.parent / target)
        return f"{attribute}{quote}{target}?v={digest}{fragment or ''}{quote}"

    linked = ASSET_LINK.sub(_link, text)
    if linked == text:
        return False
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(linked)
    return True


def main() -> int:
    """Stamp the whole site, saying which files were actually touched."""
    version = read_version()
    if not SITE_DIR.is_dir():
        print(f"no site at {SITE_DIR}, nothing to stamp")
        return 0
    touched = [path for path in site_files() if stamp(path, version)]
    if not touched:
        print(f"site already at {version}")
    else:
        print(f"stamped {version} into:")
        for path in touched:
            print(f"  {path.relative_to(ROOT)}")
    pages = [path for path in site_files() if path.suffix == ".html"]
    linked = [path for path in pages if version_assets(path)]
    if not linked:
        print("asset links already current")
        return 0
    print("versioned asset links in:")
    for path in linked:
        print(f"  {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
