#!/bin/bash
# Packages the macOS .app (produced by `pyinstaller tohtoe.spec --noconfirm`)
# into a drag-to-Applications installer .dmg. macOS only -- uses hdiutil,
# which ships with the OS, so no extra tools (e.g. create-dmg) are needed.
#
# Run from the project root, after the .app already exists in dist/:
#   ./build_dmg.sh
set -euo pipefail

APP_NAME="Tohtoe's Stock Predictions for Mac"
DIST_DIR="dist"
APP_PATH="$DIST_DIR/$APP_NAME.app"
DMG_PATH="$DIST_DIR/TohtoeStockPredictionsForMac.dmg"

if [ "$(uname)" != "Darwin" ]; then
    echo "build_dmg.sh only works on macOS (needs hdiutil)." >&2
    exit 1
fi

if [ ! -d "$APP_PATH" ]; then
    echo "Error: \"$APP_PATH\" not found." >&2
    echo "Build it first with: pyinstaller tohtoe.spec --noconfirm" >&2
    exit 1
fi

STAGING_DIR=$(mktemp -d)
trap 'rm -rf "$STAGING_DIR"' EXIT

cp -R "$APP_PATH" "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"

rm -f "$DMG_PATH"
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGING_DIR" -ov -format UDZO "$DMG_PATH"

echo "Created $DMG_PATH"
echo "Double-click it, then drag \"$APP_NAME.app\" onto the Applications shortcut to install."
