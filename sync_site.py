"""Mirror the published site into the repository that serves stellody.com.

`docs/` is the site GitHub Pages serves at stellody.co.uk, which is the
canonical host. The same pages are served at stellody.com out of a second
repository that has no way of noticing when this one changes, so a change made
here and not carried across leaves two live hosts telling different stories.

This script carries it across. `--check` reports drift without writing
anything, so a build or a workflow can refuse to pass while the two disagree.
"""

from __future__ import annotations

import argparse
import filecmp
import pathlib
import shutil
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent
SOURCE = REPO_ROOT / "docs"
DEFAULT_TARGET = REPO_ROOT.parent / "stellody-website" / "public"

# Belongs to GitHub Pages alone: it names the custom domain and means nothing
# to a host that is not Pages.
PAGES_ONLY = frozenset({"CNAME"})

# The canonical host owns the sitemap. A mirror offering a competing one is how
# two hosts start arguing over which of them owns the same pages.
CANONICAL_ONLY = frozenset({"sitemap.xml"})

# Written for the mirror and different there on purpose, so it is neither
# copied over nor deleted as an unknown extra.
MIRROR_OWNED = frozenset({"robots.txt"})

NOT_MIRRORED = PAGES_ONLY | CANONICAL_ONLY
EXIT_OK = 0
EXIT_DRIFTED = 1
EXIT_NO_TARGET = 2


def _relative_files(root: pathlib.Path, ignore: frozenset[str]) -> set[str]:
    """Every file under `root`, as posix paths relative to it.

    Names in `ignore` are dropped wherever they appear, which is at the top
    level in practice; matching on the name rather than the path keeps the
    rule readable at the cost of a nesting case that does not arise.
    """
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name not in ignore
    }


def _differs(source: pathlib.Path, target: pathlib.Path) -> bool:
    """True when the two files differ, comparing contents rather than stats."""
    if not target.exists():
        return True
    return not filecmp.cmp(source, target, shallow=False)


def _plan(source: pathlib.Path, target: pathlib.Path) -> tuple[list[str], list[str]]:
    """What to copy across and what to delete, to make target mirror source."""
    # Excluded on BOTH sides: a mirror-owned file is neither copied over from
    # here nor deleted there as an unrecognised extra.
    wanted = _relative_files(source, NOT_MIRRORED | MIRROR_OWNED)
    present = _relative_files(target, MIRROR_OWNED) if target.exists() else set()

    copy = sorted(name for name in wanted if _differs(source / name, target / name))
    remove = sorted(present - wanted)
    return copy, remove


def _apply(
    source: pathlib.Path, target: pathlib.Path, copy: list[str], remove: list[str]
) -> None:
    """Carry the plan out, creating directories the mirror does not yet have."""
    for name in copy:
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, destination)
    for name in remove:
        (target / name).unlink()


def _report(copy: list[str], remove: list[str], verb: str) -> None:
    """Say what moved, by name, so a surprise is visible rather than counted."""
    for name in copy:
        print(f"  {verb} {name}")
    for name in remove:
        print(f"  removed {name}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--target",
        type=pathlib.Path,
        default=DEFAULT_TARGET,
        help=f"the mirror's directory (default: {DEFAULT_TARGET})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift and exit non-zero, writing nothing",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    target: pathlib.Path = args.target

    if not target.parent.exists():
        print(
            f"No mirror at {target}. Clone stellody-website beside this repo, "
            "or name its public directory with --target.",
            file=sys.stderr,
        )
        return EXIT_NO_TARGET

    copy, remove = _plan(SOURCE, target)

    if not copy and not remove:
        print(f"In sync: {target} already matches {SOURCE}.")
        return EXIT_OK

    if args.check:
        print(f"Drifted from {SOURCE}:")
        _report(copy, remove, "differs")
        print("Run sync_site.py to carry the change across.")
        return EXIT_DRIFTED

    _apply(SOURCE, target, copy, remove)
    print(f"Mirrored {SOURCE} into {target}:")
    _report(copy, remove, "copied")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
