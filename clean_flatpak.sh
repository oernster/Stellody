#!/usr/bin/env bash
#
# Undo everything build_flatpak.sh did; nothing else.
#
# The three build paths are independent on purpose: this must never touch
# dist-installer/ or dist-pyinstaller/, which belong to the Windows build, nor
# dist/, which belongs to the macOS one. A cleaner that reaches into a sibling
# platform's output is a cleaner nobody dares run.

set -euo pipefail

# MUST match build_flatpak.sh. Stated again rather than shared, because a
# cleaner that sources the builder would fail on a machine where the builder
# cannot run at all.
APP_ID="uk.codecrafter.Stellody"
BUNDLE="stellody.flatpak"
MANIFEST="${APP_ID}.yml"

PURGE_DATA="no"
if [ "${1:-}" = "--purge-data" ]; then
    PURGE_DATA="yes"
fi

section() {
    if command -v tput >/dev/null 2>&1; then
        printf '\n%s%s%s\n' "$(tput bold)" "$1" "$(tput sgr0)"
    else
        printf '\n%s\n' "$1"
    fi
}

section "Uninstalling"
if command -v flatpak >/dev/null 2>&1 &&
    flatpak list --user 2>/dev/null | grep -q "${APP_ID}"; then
    flatpak uninstall --user -y "${APP_ID}"
else
    echo "  Not installed, skipping."
fi

section "Removing what the build wrote"
# Named one at a time rather than by pattern, so a directory this script has
# never heard of survives it.
rm -f "${BUNDLE}" "${MANIFEST}"
rm -rf .flatpak-build .flatpak-repo .flatpak-builder .flatpak-wheels \
    .flatpak-vendor packaging
echo "  Done."

if [ "${PURGE_DATA}" = "yes" ]; then
    section "Removing the library index and settings"
    # Asked for outright, never assumed. This is every rating, every play
    # count, every tag stated by hand and every correction accepted, which is
    # exactly what the uninstall screen on Windows names before it offers the
    # same thing.
    rm -rf "${HOME}/.var/app/${APP_ID}"
    echo "  Removed ${HOME}/.var/app/${APP_ID}"
else
    section "Kept"
    echo "  ${HOME}/.var/app/${APP_ID} holds your ratings, play counts, stated"
    echo "  tags and accepted corrections. Pass --purge-data to remove it too."
fi
