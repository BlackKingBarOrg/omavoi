import QtQuick

// Where the daemon comes from, pinned to one commit.
//
// The first-run screen and the update screen both install it with
// `uv tool install <spec>`, and each carried its own copy of the spec — the
// bare repository URL, which is "whatever master is today". Two problems
// with that, one of them disqualifying: the two copies can drift, and the
// Omarchy plugin marketplace's Automated Security Baseline classes an
// unpinned remote Git source that gets built and executed as a blocking
// finding (remote-git-execution-unpinned). Pinning is also simply what a
// listing is: the marketplace itself records the exact plugin commit it
// reviewed, so the daemon that commit installs should be exact too.
//
// One file, instantiated by both views the way Strings.qml is, because a
// plugin folder has no import path to hang a singleton on. Bump `sha` with
// `python3 tools/check_pin.py --sync`, which reads the sibling daemon
// checkout's HEAD; `tools/check_pin.py` alone refuses anything that is not a
// full 40-hex commit.
QtObject {
  readonly property string repo: "https://github.com/BlackKingBarOrg/omavoi-daemon"
  readonly property string sha: "c7a19415293b4a9a2ea7c04e35f98a52c699c09a"
  readonly property string spec: "git+" + repo + "@" + sha
}
