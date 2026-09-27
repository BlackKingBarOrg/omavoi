import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons

// The theme's own green and yellow, for "this works" and "look at this".
//
// The shell's palette is foreground, background, accent, urgent and muted —
// nothing for success or caution — so this plugin wrote Tokyo Night's
// #9ece6a and #e0af68 into a dozen places, and on every other theme a green
// from a different palette sat next to that theme's accent. The theme's
// colors.toml has both: by name (`green`, `yellow`) or as the terminal's
// color2 and color3. The two old constants stay for a theme that has
// neither.
//
// One per view, like Strings, because a plugin folder has nowhere to hang a
// singleton. Reading a small file each is nothing.
QtObject {
  id: tones

  property color good: "#9ece6a"
  property color warn: "#e0af68"

  function parse(raw) {
    var found = ({})
    var lines = String(raw || "").split("\n")
    for (var i = 0; i < lines.length; i++) {
      var m = lines[i].match(/^\s*([A-Za-z0-9_-]+)\s*=\s*["']?(#[0-9A-Fa-f]{6})/)
      if (m) found[m[1]] = m[2]
    }
    tones.good = found.green || found.color2 || "#9ece6a"
    tones.warn = found.yellow || found.color3 || "#e0af68"
  }

  property FileView file: FileView {
    path: Quickshell.env("HOME") + "/.local/state/omarchy/current/theme/colors.toml"
    watchChanges: true
    printErrors: false
    onLoaded: tones.parse(text())
    onFileChanged: reload()
  }

  // A theme switch reaches the shell as a pushed payload, not as a change to
  // a file anyone is watching, so follow the palette that did change.
  property Connections themeSwitch: Connections {
    target: Color
    function onAccentChanged() { tones.file.reload() }
  }
}
