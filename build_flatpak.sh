#!/usr/bin/env bash
#
# Build Stellody as a Flatpak, then bundle it into one installable file.
#
# Run from the repository root on the Linux machine. It writes its packaging
# helpers into packaging/, builds through flatpak-builder and leaves
# stellody.flatpak beside this script. clean_flatpak.sh undoes all of it.
#
# Two things here are decided rather than copied; both are worth reading
# before changing them.
#
# PortAudio is built from source. Measured in the installed sounddevice: its
# bundled portaudio-binaries fallback is reached for Darwin and for Windows
# only; every other system re-raises "PortAudio library not found". So the
# wheel carries no library on Linux and the freedesktop runtime ships none,
# which means nothing would play at all without this module.
#
# The library is granted READ ONLY. Stellody never writes to a music file,
# which is the rule the whole application is built on and which a structural
# test already enforces. Granting the home directory read only puts the
# operating system behind that rule as well, so on this platform it is not
# merely true, it is unable to be otherwise.

set -euo pipefail

APP_ID="uk.codecrafter.Stellody"
APP_NAME="Stellody"
COMMAND="stellody"
RUNTIME="org.freedesktop.Platform"
SDK="org.freedesktop.Sdk"
RUNTIME_VERSION="25.08"
PYTHON_DIR="python3.13"

BUNDLE="stellody.flatpak"
BUILD_DIR=".flatpak-build"
REPO_DIR=".flatpak-repo"
WHEEL_DIR=".flatpak-wheels"
HELPER_DIR="packaging"
MANIFEST="${APP_ID}.yml"

# Matched to the runtime above. A wheel built for a newer glibc than the
# runtime holds installs cleanly then fails to load, which is a worse failure
# than refusing to download.
WHEEL_PLATFORM="manylinux_2_34_x86_64"
WHEEL_PYTHON="3.13"

PORTAUDIO_VERSION="19.7.0"
PORTAUDIO_URL="https://github.com/PortAudio/portaudio/archive/refs/tags/v${PORTAUDIO_VERSION}.tar.gz"
PORTAUDIO_ARCHIVE="portaudio-${PORTAUDIO_VERSION}.tar.gz"
VENDOR_DIR=".flatpak-vendor"

ICON_SIZES="16 24 32 48 64 96 128 256"

section() {
    if command -v tput >/dev/null 2>&1; then
        printf '\n%s%s%s\n' "$(tput bold)" "$1" "$(tput sgr0)"
    else
        printf '\n%s\n' "$1"
    fi
}

install_if_missing() {
    local tool="$1"
    command -v "${tool}" >/dev/null 2>&1 && return 0
    section "Installing ${tool}"
    if command -v apt >/dev/null 2>&1; then
        sudo apt update && sudo apt install -y "${tool}"
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y "${tool}"
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -S --noconfirm "${tool}"
    elif command -v zypper >/dev/null 2>&1; then
        sudo zypper install -y "${tool}"
    else
        echo "Install ${tool} by hand; no package manager here was recognised." >&2
        exit 1
    fi
}

section "Checking the tools"
install_if_missing flatpak
install_if_missing flatpak-builder
install_if_missing curl

section "Making sure the runtime is here"
flatpak remote-add --if-not-exists --user \
    flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user --noninteractive \
    flathub "${RUNTIME}//${RUNTIME_VERSION}" "${SDK}//${RUNTIME_VERSION}"

section "Fetching PortAudio"
# Fetched to a local file rather than named in the manifest with a checksum
# beside it. A checksum written from memory is a checksum that is wrong; it
# fails the build with an error about integrity rather than about the guess. A
# local archive needs none: the file that was downloaded is the file that is
# built.
mkdir -p "${VENDOR_DIR}"
if [ ! -f "${VENDOR_DIR}/${PORTAUDIO_ARCHIVE}" ]; then
    curl -fL -o "${VENDOR_DIR}/${PORTAUDIO_ARCHIVE}" "${PORTAUDIO_URL}"
fi

section "Fetching the wheels"
# Downloaded on the host so the build itself needs no network at all. What the
# application asks the network for at RUNTIME is one thing, the update check;
# what it asks for while being built should be nothing.
rm -rf "${WHEEL_DIR}"
pip download --only-binary :all: \
    --python-version "${WHEEL_PYTHON}" --implementation cp \
    --platform "${WHEEL_PLATFORM}" \
    -d "${WHEEL_DIR}" -r requirements.txt

section "Writing the packaging helpers"
rm -rf "${HELPER_DIR}"
mkdir -p "${HELPER_DIR}"

# The heredoc is UNQUOTED, so PYTHON_DIR and COMMAND are substituted once
# here. Everything the launcher must decide at RUN time is escaped, so it is
# written literally rather than resolved now against this machine. The python
# directory comes from the variable above rather than being typed again,
# because it has to match the runtime: bumping the runtime and leaving a
# stale python3.NN in the path is a launcher that finds no Qt and says
# nothing useful about why.
SITE="/app/lib/${PYTHON_DIR}/site-packages"
cat > "${HELPER_DIR}/${COMMAND}" <<LAUNCHER
#!/bin/sh
export PYTHONPATH="${SITE}:/app/share/${COMMAND}\${PYTHONPATH:+:\$PYTHONPATH}"
export QT_PLUGIN_PATH="${SITE}/PySide6/Qt/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="${SITE}/PySide6/Qt/plugins/platforms"
export QML2_IMPORT_PATH="${SITE}/PySide6/Qt/qml"
if [ -n "\$WAYLAND_DISPLAY" ] && [ -z "\$FORCE_X11" ]; then
    export QT_QPA_PLATFORM=wayland
elif [ -n "\$DISPLAY" ]; then
    export QT_QPA_PLATFORM=xcb
else
    export QT_QPA_PLATFORM=xcb
fi
exec python3 /app/share/${COMMAND}/main.py "\$@"
LAUNCHER
chmod 755 "${HELPER_DIR}/${COMMAND}"

cat > "${HELPER_DIR}/${APP_ID}.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=A music player for the collection already on your computer
Exec=${COMMAND}
Icon=${APP_ID}
Categories=AudioVideo;Audio;Player;
Terminal=false
DESKTOP

cat > "${HELPER_DIR}/${APP_ID}.metainfo.xml" <<METAINFO
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>${APP_ID}</id>
  <name>${APP_NAME}</name>
  <summary>A music player for the collection already on your computer</summary>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0-or-later</project_license>
  <developer id="uk.codecrafter">
    <name>Oliver Ernster</name>
  </developer>
  <description>
    <p>
      ${APP_NAME} plays the music you already have. It reads your files and
      never writes to them: where an album is labelled badly it says so and
      leaves the file exactly as it found it.
    </p>
  </description>
  <launchable type="desktop-id">${APP_ID}.desktop</launchable>
  <content_rating type="oars-1.1"/>
</component>
METAINFO

section "Writing the manifest"
cat > "${MANIFEST}" <<MANIFEST_YML
app-id: ${APP_ID}
runtime: ${RUNTIME}
runtime-version: "${RUNTIME_VERSION}"
sdk: ${SDK}
command: ${COMMAND}

build-options:
  strip: true
  no-debuginfo: true

finish-args:
  - --share=ipc
  - --socket=fallback-x11
  - --socket=wayland
  - --device=dri
  # The sound, which is the whole point of the application.
  - --socket=pulseaudio
  # The update check asks GitHub whether a newer Stellody exists. Without this
  # it fails quietly, so it would be found by a listener rather than a build.
  - --share=network
  # The library, READ ONLY. Stellody never writes to a music file; granting it
  # no way to do so puts the sandbox behind the rule the application is built
  # on. Its own database lives under the sandbox's data directory, which needs
  # no permission at all.
  - --filesystem=home:ro
  - --filesystem=/media:ro
  - --filesystem=/run/media:ro

modules:
  # Measured in the installed sounddevice: the bundled binaries are for Darwin
  # and Windows only, so on Linux the library has to come from somewhere.
  - name: portaudio
    buildsystem: autotools
    config-opts:
      - --prefix=/app
      - --disable-static
      - --with-alsa
    sources:
      - type: archive
        path: ${VENDOR_DIR}/${PORTAUDIO_ARCHIVE}

  - name: python-deps
    buildsystem: simple
    build-commands:
      - python3 -m ensurepip --upgrade
      - pip3 install --no-cache-dir --no-index --find-links wheels
        --prefix=/app -r requirements.txt
    sources:
      - type: dir
        path: ${WHEEL_DIR}
        dest: wheels
      - type: file
        path: requirements.txt

  - name: ${COMMAND}
    buildsystem: simple
    build-commands:
      - install -d /app/share/${COMMAND}
      - cp -r main.py stellody assets VERSION LICENSE /app/share/${COMMAND}/
      - install -Dm755 ${HELPER_DIR}/${COMMAND} /app/bin/${COMMAND}
      - install -Dm644 ${HELPER_DIR}/${APP_ID}.desktop
        /app/share/applications/${APP_ID}.desktop
      - install -Dm644 ${HELPER_DIR}/${APP_ID}.metainfo.xml
        /app/share/metainfo/${APP_ID}.metainfo.xml
MANIFEST_YML

# One install line per icon size, appended rather than written inline, so the
# sizes stay a list here instead of being repeated in the manifest by hand.
for size in ${ICON_SIZES}; do
    cat >> "${MANIFEST}" <<ICON_LINE
      - install -Dm644 assets/stellody_icon_${size}.png
        /app/share/icons/hicolor/${size}x${size}/apps/${APP_ID}.png
ICON_LINE
done

cat >> "${MANIFEST}" <<MANIFEST_TAIL
    sources:
      - type: dir
        path: .
MANIFEST_TAIL

section "Building"
rm -rf "${BUILD_DIR}" "${REPO_DIR}"
flatpak-builder --user --install-deps-from=flathub --force-clean \
    --repo="${REPO_DIR}" "${BUILD_DIR}" "${MANIFEST}"

section "Bundling"
rm -f "${BUNDLE}"
flatpak build-bundle \
    --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo \
    "${REPO_DIR}" "${BUNDLE}" "${APP_ID}"

section "Done"
echo "Wrote ${BUNDLE}"
echo "Install it with: flatpak install --user ${BUNDLE}"
echo "Run it with:     flatpak run ${APP_ID}"
