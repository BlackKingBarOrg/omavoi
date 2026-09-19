import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

// Upgrading, in the same shape as installing: the commands are printed, one
// button runs them, and nothing here needs a terminal.
//
// It exists because the honest command for the daemon is not the obvious one.
// `uv tool upgrade omavoi` reports "Nothing to upgrade" against a git source
// even when the branch has moved — measured, pinned to an old commit — so the
// route is a reinstall from the URL. Nobody should have to know that.
ColumnLayout {
  id: root

  property var strings: null
  // Steps the daemon says are still missing and need root — a package added
  // by a version you are upgrading *to* is invisible to the version you have.
  property var setupReport: ({ steps: [] })

  signal command(string cmd)
  signal finished()

  function t(k) { return root.strings ? root.strings.t(k) : k }
  function tf(k, a) { return root.strings ? root.strings.tf(k, a) : k }

  // Pinned to one commit, in one place. See DaemonSource.qml.
  DaemonSource { id: daemonSource }
  readonly property string repo: daemonSource.spec
  readonly property string pluginId: "ai.bkblab.omavoi"

  // -- is there anything to do? -------------------------------------------
  //
  // Asked of the clone rather than of a version file: the plugin is a git
  // checkout, so the question is whether origin has moved past it.
  property int behind: -1
  // Why the count is unknown, when it is. `pluginError` was declared here
  // from the start and nothing ever set it: the probe sent git's stderr to
  // /dev/null and printed -1, so a laptop with no network and a directory
  // that was hand-copied instead of cloned produced the same -1 and the same
  // sentence — "the plugin was not installed from git" — which sends the
  // first one to reinstall something that is perfectly fine.
  //
  // "" means the count is good. Anything else is the reason it is not.
  property string pluginError: ""
  Process {
    id: probeBehind
    command: ["sh", "-c",
              "d=\"$HOME/.config/omarchy/plugins/ai.bkblab.omavoi\"; " +
              "git -C \"$d\" rev-parse --git-dir >/dev/null 2>&1 || " +
              "{ echo nogit; exit 0; }; " +
              "e=$(git -C \"$d\" fetch --quiet origin 2>&1) || " +
              "{ echo \"nofetch $e\"; exit 0; }; " +
              "git -C \"$d\" rev-list --count HEAD..@{upstream} 2>/dev/null || " +
              "echo noupstream"]
    stdout: StdioCollector {
      onStreamFinished: {
        var out = String(text).trim()
        if (out.indexOf("nofetch") === 0) {
          // Still shows the count it can compute locally when there is one;
          // it is simply not known to be current.
          root.behind = -1
          // git says its piece over four or five lines, of which the first
          // is the one that identifies the cause — "'origin' does not
          // appear to be a git repository", "Could not resolve host" — and
          // the rest is advice about access rights that is wrong whenever
          // the real answer is that the laptop is on a train.
          var why = out.slice(7).split("\n")
                       .map(function (l) { return l.trim() })
                       .filter(function (l) { return l !== "" })[0] || ""
          why = why.replace(/^fatal:\s*/, "").slice(0, 120)
          root.pluginError = root.tf("up.nofetch", why || "git fetch failed")
        } else if (out === "noupstream") {
          root.behind = -1
          root.pluginError = root.t("up.noupstream")
        } else if (out === "nogit" || out === "") {
          root.behind = -1
          root.pluginError = ""          // up.unknown, which is now accurate
        } else {
          root.behind = parseInt(out, 10)
          root.pluginError = isNaN(root.behind) ? root.t("up.noupstream") : ""
          if (isNaN(root.behind)) root.behind = -1
        }
      }
    }
  }
  // Local edits stop a fast-forward, and hand-copied files are exactly how a
  // developer's machine ends up unable to update itself.
  property bool pluginDirty: false
  Process {
    id: probeDirty
    command: ["sh", "-c",
              "test -n \"$(git -C \"$HOME/.config/omarchy/plugins/ai.bkblab.omavoi\" " +
              "status --porcelain 2>/dev/null)\""]
    onExited: function (code, status) { root.pluginDirty = code === 0 }
  }

  function refresh() {
    probeBehind.running = true
    probeDirty.running = true
  }
  Component.onCompleted: refresh()

  readonly property var rootSteps: {
    var out = []
    var steps = (root.setupReport && root.setupReport.steps) || []
    for (var i = 0; i < steps.length; i++) {
      var s = steps[i]
      if (!s.done && s.needs_root && String(s.command || "").indexOf("pacman") >= 0)
        out.push(s)
    }
    return out
  }

  readonly property var steps: {
    var plan = [
      { key: "plugin", label: root.t("up.step.plugin"),
        argv: ["omarchy", "plugin", "update", root.pluginId, "--yes"] },
      { key: "daemon", label: root.t("up.step.daemon"),
        // Not `uv tool upgrade`: against a git source it does nothing and
        // says so in a way that reads like success.
        argv: ["uv", "tool", "install", "--reinstall", root.repo] }
    ]
    // Whatever the newer daemon then asks for, in one prompt.
    if (root.rootSteps.length > 0) {
      var pkgs = []
      for (var i = 0; i < root.rootSteps.length; i++) {
        var parts = String(root.rootSteps[i].command).split(/\s+/)
        for (var j = 0; j < parts.length; j++)
          if (parts[j] !== "" && parts[j][0] !== "-"
              && parts[j] !== "sudo" && parts[j] !== "pacman")
            pkgs.push(parts[j])
      }
      if (pkgs.length > 0)
        plan.push({ key: "packages", root: true, label: root.t("first.step.packages"),
                    argv: ["pkexec", "/usr/bin/pacman", "-S", "--needed",
                           "--noconfirm"].concat(pkgs) })
    }
    // The plugin's own installer, re-run. It is the only thing that puts the
    // unit, the Hyprland keybinding and the Omarchy menu entry in place, and
    // nothing else in this plan touches them -- so a user who installed six
    // versions ago kept whatever those files said then, and a change to any
    // of the three reached new installs only. It is idempotent to the byte,
    // so being already current costs a no-op.
    plan.push({ key: "shortcuts", label: root.t("up.step.shortcuts"),
                argv: [Quickshell.env("HOME") + "/.config/omarchy/plugins/"
                       + root.pluginId + "/install.sh"] })
    plan.push({ key: "restart", label: root.t("up.step.restart"),
                argv: ["systemctl", "--user", "restart", "omavoid"] })
    return plan
  }

  spacing: Style.space(8)

  OmText {
    text: root.t("up.title")
    font.letterSpacing: 1
    color: Color.muted
  }

  OmText {
    Layout.fillWidth: true
    wrapMode: Text.Wrap
    text: root.behind > 0 ? root.tf("up.behind", root.behind)
          : root.behind === 0 ? root.t("up.current")
          : root.pluginError !== "" ? root.pluginError
          : root.t("up.unknown")
    size: "body"
    color: root.behind > 0 || root.pluginError !== "" ? "#e0af68"
                                                      : Color.foreground
  }

  // The line above answers "is the plugin behind?", which is the only half
  // this screen can see. The daemon is a separate `uv tool install` whose
  // receipt records the URL and not the commit, and the package version is
  // static, so nothing here can compare them — and reporting "up to date"
  // for a question it never asked is the same fault as reporting the config
  // file instead of the running binding.
  OmText {
    Layout.fillWidth: true
    Layout.maximumWidth: Style.space(760)
    wrapMode: Text.Wrap
    text: root.t("up.daemon.blind")
    color: Qt.darker(Color.muted, 1.15)
  }

  // Said before the button, because the button cannot fix it and the message
  // pacman gives for it explains nothing.
  OmText {
    visible: root.pluginDirty
    Layout.fillWidth: true
    wrapMode: Text.Wrap
    // The advice has to name the repository, and "checkout -- ." was wrong
    // anyway: it restores modified files and leaves untracked ones behind,
    // which still blocks the fast-forward.
    text: root.tf("up.dirty",
                  "https://github.com/BlackKingBarOrg/omavoi")
    color: Color.urgent
  }

  StepRunner {
    id: plan
    Layout.fillWidth: true
    strings: root.strings
    steps: root.steps
    onFinished: {
      root.refresh()
      root.finished()
    }
  }

  RowLayout {
    Layout.fillWidth: true
    spacing: Style.space(10)
    Button {
      visible: !plan.running
      enabled: !root.pluginDirty
      text: plan.done ? root.t("up.again")
            : plan.failure !== "" ? root.t("first.retry")
            : root.t("up.run")
      // "Check again" used to re-run the whole plan -- reinstall the plugin,
      // reinstall the daemon, re-run install.sh, restart the unit -- behind a
      // label that promises a question. After a finished update the only
      // honest thing that button can do is ask the question again: reset the
      // runner back to its idle shape and re-probe. The Update button comes
      // back with it, so running it twice is still one click away.
      onClicked: {
        if (plan.done) { plan.reset(); root.refresh() }
        else { plan.reset(); plan.begin() }
      }
    }
    OmText {
      visible: plan.running
      // `at` is -1 while idle, and steps[-1] is undefined.
      text: plan.at >= 0 && plan.at < root.steps.length
            ? root.tf("first.working", root.steps[plan.at].label) : ""
      size: "body"
      color: Color.accent
    }
    OmText {
      visible: plan.done
      text: root.t("up.done")
      size: "body"
      color: "#9ece6a"
    }
    OmText {
      visible: plan.failure !== ""
      Layout.fillWidth: true
      wrapMode: Text.Wrap
      text: plan.failure
      color: Color.urgent
    }
    Item { Layout.fillWidth: true }
  }
}
