#!/usr/bin/env bash
#
# The three things a plugin cannot add for itself: the systemd user unit, a
# Hyprland keybinding, and a row in the Omarchy menu.
#
# Omarchy's manifest has no field for any of them, and `omarchy plugin add`
# deliberately runs nothing from inside a plugin -- a plugin lands in a
# trusted directory and is not itself trusted. So this is a command you run
# once, by hand, and it tells you exactly what it changed.
#
#   ~/.config/omarchy/plugins/ai.bkblab.omavoi/install.sh
#   ~/.config/omarchy/plugins/ai.bkblab.omavoi/install.sh --remove
#
# Both files are edited between markers, so running it twice changes nothing
# and --remove takes out exactly what was added.

set -euo pipefail

PLUGIN_ID="ai.bkblab.omavoi"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
BINDINGS="${XDG_CONFIG_HOME:-$HOME/.config}/hypr/bindings.lua"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
# The menu indexes */apps/*.svg and */apps/*.png under $HOME/.icons and
# $HOME/.local/share/icons by basename, at any depth, preferring SVG -- so
# `Icon=ai.bkblab.omavoi` resolves to exactly this file and nothing else.
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
BEGIN="-- >>> omavoi"
END="-- <<< omavoi"
REMOVE=0
[[ "${1:-}" == "--remove" ]] && REMOVE=1

say() { printf '  %s\n' "$*"; }

# Write over a file in place rather than moving a temp file onto it. `mv`
# carries the temp file's own mode across, and mktemp makes 0600 -- so this
# script's own strip_block had been quietly turning the user's bindings.lua
# from 0644 into 0600 on every run since it was written.
replace_file() {
  local file="$1" tmp="$2"
  cat "$tmp" > "$file"
  rm -f "$tmp"
}

# Trailing blank lines, because the block is always appended at the end and
# the heredoc opens with one to separate itself from whatever came before.
# strip_block took the block out and left that blank line behind, so every
# run added one more -- four runs, four blank lines. The header says running
# this twice changes nothing; this is what makes that true.
trim_trailing_blanks() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  local tmp; tmp="$(mktemp)"
  awk '{ line[NR] = $0 }
    END {
      last = 0
      for (i = 1; i <= NR; i++) if (line[i] ~ /[^[:space:]]/) last = i
      for (i = 1; i <= last; i++) print line[i]
    }' "$file" > "$tmp"
  replace_file "$file" "$tmp"
}

strip_block() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  # `--` before the pattern: BEGIN starts with "--", which grep otherwise
  # reads as an option, so this test silently never matched. The block was
  # never stripped, which made the script append a duplicate every run and
  # left --remove with nothing to remove.
  if grep -qF -- "$BEGIN" "$file"; then
    local tmp; tmp="$(mktemp)"
    awk -v b="$BEGIN" -v e="$END" '
      index($0, b) { skip = 1 } !skip { print } index($0, e) { skip = 0 }
    ' "$file" > "$tmp"
    replace_file "$file" "$tmp"
    trim_trailing_blanks "$file"
    say "removed the omavoi block from $file"
  fi
}

if (( REMOVE )); then
  echo "Removing Omavoi shortcuts"
  strip_block "$BINDINGS"
  if systemctl --user list-unit-files omavoid.service &>/dev/null; then
    systemctl --user disable --now omavoid.service 2>/dev/null || true
    say "disabled omavoid.service"
  fi
  # `rm -f` succeeds on a path that was never there, so the message has to
  # test for the file rather than the command.
  if [[ -e "$UNIT_DIR/omavoid.service" ]]; then
    rm -f "$UNIT_DIR/omavoid.service"
    say "removed the unit file"
  fi
  for f in "$APPS_DIR/$PLUGIN_ID.desktop" "$ICON_DIR/$PLUGIN_ID.svg"; do
    if [[ -e "$f" ]]; then
      rm -f "$f"
      say "removed $f"
    fi
  done
  systemctl --user daemon-reload
  echo "Done. The plugin itself is still installed; remove it with:"
  echo "  omarchy plugin remove $PLUGIN_ID"
  exit 0
fi

echo "Installing Omavoi shortcuts"

# 1. The daemon, as a user service.
mkdir -p "$UNIT_DIR"
install -m 0644 "$HERE/omavoid.service" "$UNIT_DIR/omavoid.service"
say "installed $UNIT_DIR/omavoid.service"
systemctl --user daemon-reload

if command -v omavoi >/dev/null; then
  systemctl --user enable --now omavoid.service && say "started omavoid.service"
else
  say "omavoi is not on PATH yet -- install it, then: systemctl --user enable --now omavoid"
fi

# 2. Keybindings. The console gets SUPER+ALT+V.
#
# The dictation key itself is NOT bound here. It is read from evdev inside the
# daemon, because binding a modifier in Hyprland fights itself: pressing one
# changes the modmask, which fires the release binding immediately and records
# a 0.0s take. If you are not in the `input` group yet, uncomment the F9 lines
# below -- a non-modifier key does work through Hyprland.
if [[ -f "$BINDINGS" ]]; then
  strip_block "$BINDINGS"
  trim_trailing_blanks "$BINDINGS"
  cat >> "$BINDINGS" <<'LUA'

-- >>> omavoi
o.bind("SUPER + ALT + V", "Omavoi console", "omarchy-shell shell toggle ai.bkblab.omavoi")
-- Not in the `input` group yet? Uncomment these two for a working key today.
-- Modifier keys cannot be used this way; a plain key like F9 can.
-- o.bind("F9", "Dictate", "omavoi record start")
-- o.bindr("F9", "Dictate (release)", "omavoi record stop")
-- <<< omavoi
LUA
  say "added the omavoi block to $BINDINGS"
else
  say "no $BINDINGS -- skipped the keybinding"
fi

# 3. A row in the Omarchy menu -- SUPER+SPACE, and SUPER+ALT+SPACE for the
# apps list directly. Both come from what Quickshell's DesktopEntries finds in
# the XDG data dirs, so joining them is a plain .desktop file: the plugin
# manifest has no field for a menu entry, and the one plugin-facing app API is
# for reading the app list rather than joining it.
mkdir -p "$APPS_DIR" "$ICON_DIR"
install -m 0644 "$HERE/$PLUGIN_ID.desktop" "$APPS_DIR/$PLUGIN_ID.desktop"
install -m 0644 "$HERE/$PLUGIN_ID.svg" "$ICON_DIR/$PLUGIN_ID.svg"
say "added the Omarchy menu entry and its icon"
# The shell watches the directory and picks the entry up on its own. This is
# for every other launcher on the machine, which reads a cache instead.
if command -v update-desktop-database >/dev/null; then
  update-desktop-database "$APPS_DIR" 2>/dev/null || true
fi

echo
echo "Next:"
echo "  omavoi setup      # shows what is still missing, with the command for each"
echo "  SUPER + SPACE     # Omavoi is in the menu now, or SUPER + ALT + V for the console"
