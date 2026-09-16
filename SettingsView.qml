import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

// What is left once Modes took the contextual choices and Models took the
// weights: the physical and the global. A key, a microphone, an overlay, and
// what stays on disk.
Flickable {
  id: root
  property var cfg: ({})
  property var setupReport: ({ steps: [] })
  property int pad: Style.space(22)
  property var strings: null

  signal command(string cmd)

  property bool capturing: false
  property string captured: ""
  property bool capturedOk: false

  Process {
    id: grabber
    command: ["omavoi", "hotkey", "capture", "--timeout", "8", "--json"]
    onRunningChanged: root.capturing = grabber.running
    stdout: StdioCollector {
      onStreamFinished: {
        var r = ({})
        try { r = JSON.parse(text) } catch (e) { r = ({ ok: false, error: text }) }
        root.capturedOk = r.ok === true
        if (r.ok === true) {
          root.captured = ""
          // Written through the same command a terminal would use, so the
          // check that refuses an unresolvable name applies here too.
          root.command("omavoi config set hotkey.key " + r.key)
        } else {
          root.captured = String(r.error || "")
        }
      }
    }
  }

  // -- is the key actually working? ---------------------------------------
  //
  // Asked of the machine rather than of the config, because the config was
  // never the thing that broke: a key can be spelled right, owned by no
  // readable device, or held by a listener that is still on the old one. The
  // daemon answers all of that in one call; each answer here has the button
  // that fixes it next to it, so nobody has to open a terminal to find out
  // which of the four it was.
  property var health: ({})
  property bool checking: false
  Process {
    id: checker
    command: ["omavoi", "hotkey", "check", "--json"]
    onRunningChanged: root.checking = checker.running
    stdout: StdioCollector {
      onStreamFinished: {
        try { root.health = JSON.parse(text) } catch (e) { root.health = ({}) }
      }
    }
  }
  // Covers three of the causes at once — stopped, listening on nothing, and
  // listening on the previous key — and needs no password.
  Process {
    id: restarter
    command: ["systemctl", "--user", "restart", "omavoid"]
    onExited: function (code, status) { checkAgain.restart() }
  }
  // The one fix that needs root. Same command the first-run wizard folds in,
  // and it leaves the relogin message behind on purpose: being added to a
  // group does not add you to a session that already started.
  Process {
    id: grouper
    command: ["pkexec", "/usr/bin/usermod", "-aG", "input",
              Quickshell.env("USER") || ""]
    onExited: function (code, status) { checkAgain.restart() }
  }
  // A restarted daemon needs a moment before it can answer.
  Timer {
    id: checkAgain
    interval: 1400
    onTriggered: checker.running = true
  }

  readonly property string ill: {
    var h = root.health
    if (!h || h.configured === undefined) return ""
    if (h.enabled === false) return root.t("set.key.off")
    if (h.name_ok === false) return root.tf("set.key.badname", h.configured)
    // The daemon first. It is the process that reads the key, and this
    // session's own device access says nothing about it — they differ
    // whenever the daemon was started after the `input` group was granted,
    // or through newgrp. Asking the group first put a red "log out and back
    // in" over a hotkey that was working, which is the fifth place in this
    // program to have made that mistake.
    if (h.listener) return h.matches ? "" : root.tf("set.key.stale", h.bound)
    // Not in the group at all comes before "the daemon is not running":
    // starting it would not help, and a message about the daemon over a
    // button that adds you to a group does not read as one thought.
    if (!h.group_listed) return root.t("set.key.nogroup")
    if (h.daemon !== "running") return root.t("set.key.stopped")
    if (!h.group_held) return root.t("set.key.relogin")
    if (h.devices_problem) return root.tf("set.key.nodevice", h.configured)
    return root.t("set.key.stopped")
  }
  // What the button next to the message does, or "" for the two that no
  // button can do: pressing a key, and logging out.
  readonly property string remedy: {
    var h = root.health
    if (root.ill === "" || !h) return ""
    if (h.enabled === false || h.name_ok === false) return ""
    // A working daemon needs no remedy, and the two the user cannot click —
    // press a key, log out — offer none.
    if (h.listener) return h.matches ? "" : "restart"
    if (!h.group_listed) return "group"
    if (!h.group_held) return ""
    if (h.devices_problem) return ""
    return "restart"
  }

  Component.onCompleted: checker.running = true
  // The config changing is the moment a stale binding becomes possible.
  onCfgChanged: checkAgain.restart()

  // `strings` is null for the instant between creation and the Loader setting
  // it, so the key stands in until then rather than a blank.
  function t(k) { return root.strings ? root.strings.t(k) : k }
  function tf(k, a) { return root.strings ? root.strings.tf(k, a) : k }

  function get(path, fallback) {
    var node = root.cfg
    var parts = path.split(".")
    for (var i = 0; i < parts.length; i++) {
      if (!node || node[parts[i]] === undefined) return fallback
      node = node[parts[i]]
    }
    return node
  }

  contentHeight: col.implicitHeight + pad * 2
  clip: true

  ColumnLayout {
    id: col
    x: root.pad
    y: root.pad
    width: root.width - root.pad * 2
    spacing: Style.space(18)

    // ---- hotkey ----------------------------------------------------
    ColumnLayout {
      Layout.fillWidth: true
      spacing: Style.space(8)
      OmText {
        text: root.t("set.hotkey")
        font.letterSpacing: 1
        color: Color.muted
      }
      RowLayout {
        Layout.fillWidth: true
        OmText {
          Layout.preferredWidth: Style.space(160)
          text: root.t("set.key")
          size: "body"
          color: Color.muted
        }
        OmText {
          Layout.preferredWidth: Style.space(96)
          text: root.get("hotkey.key", "?")
          size: "body"
          color: Color.foreground
        }
        // Pressed rather than picked from a list. Quickshell cannot read an
        // input device, but the daemon already can and already resolves key
        // names, so the capture happens there and the answer comes back here.
        Button {
          text: root.capturing ? root.t("set.key.press") : root.t("set.key.rebind")
          enabled: !root.capturing
          onClicked: { root.captured = ""; grabber.running = true }
        }
        Button {
          visible: root.remedy !== ""
          text: root.remedy === "group" ? root.t("set.key.fix.group")
                                        : root.t("set.key.fix.restart")
          onClicked: {
            if (root.remedy === "group") grouper.running = true
            else restarter.running = true
          }
        }
        Button {
          text: root.t("set.key.check")
          enabled: !root.checking
          onClicked: checker.running = true
        }
        Item { Layout.fillWidth: true }
      }

      // One line, and it is either the reason it does not work or the
      // devices it is working on. Never both, and never neither.
      OmText {
        Layout.fillWidth: true
        Layout.maximumWidth: Style.space(760)
        wrapMode: Text.Wrap
        text: root.captured !== "" ? root.captured
              : root.checking && root.ill === "" ? root.t("set.key.testing")
              : root.ill !== "" ? root.ill
              : root.health.configured !== undefined
                ? root.tf("set.key.ok",
                          (root.health.bound_devices || []).length > 0
                          ? String(root.health.bound_devices.join(", "))
                              .replace(/\/dev\/input\/\S+ /g, "")
                          : "—")
                : ""
        color: root.captured !== "" ? Color.urgent
               : root.ill !== "" ? Color.urgent : "#9ece6a"
      }
      RowLayout {
        Layout.fillWidth: true
        OmText {
          Layout.preferredWidth: Style.space(160)
          text: root.t("set.behaviour")
          size: "body"
          color: Color.muted
        }
        ButtonGroup {
          options: [{ value: "push_to_talk", label: root.t("set.ptt") },
                    { value: "toggle", label: root.t("set.toggle") }]
          value: root.get("hotkey.mode", "push_to_talk")
          onChanged: function (v) { root.command("omavoi config set hotkey.mode " + v) }
        }
      }
      OmText {
        Layout.maximumWidth: Style.space(760)
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: root.t("set.hotkeynote")
        color: Qt.darker(Color.muted, 1.15)
      }
    }

    // ---- audio -----------------------------------------------------
    ColumnLayout {
      Layout.fillWidth: true
      spacing: Style.space(8)
      OmText {
        text: root.t("set.audio")
        font.letterSpacing: 1
        color: Color.muted
      }
      // Editable, at last. These four were plain text for as long as the page
      // existed — including audio.preroll_seconds, which is the knob the
      // clipped-onset warning tells you to reach for.
      //
      // NumberField is integer-only, so the two fractional ones are shown in
      // milliseconds and divided on the way out. 600 ms is also a plainer thing
      // to read than 0.6 s.
      Repeater {
        model: [
          { k: "audio.preroll_seconds", label: root.t("set.preroll"), unit: "ms",
            scale: 1000, from: 0, to: 5000, step: 100,
            why: root.t("set.prerollwhy") },
          { k: "audio.tail_seconds", label: root.t("set.tail"), unit: "ms",
            scale: 1000, from: 0, to: 2000, step: 50, why: "" },
          { k: "audio.warn_rms_dbfs", label: root.t("set.warnbelow"), unit: "dBFS",
            scale: 1, from: -90, to: 0, step: 1, why: "" },
          { k: "audio.max_seconds", label: root.t("set.maxtake"), unit: "s",
            scale: 1, from: 5, to: 3600, step: 30, why: "" }
        ]
        ColumnLayout {
          readonly property var row: modelData
          Layout.fillWidth: true
          spacing: Style.space(2)
          RowLayout {
            Layout.fillWidth: true
            spacing: Style.space(8)
            OmText {
              Layout.preferredWidth: Style.space(160)
              text: row.label
              size: "body"
              color: Color.muted
            }
            NumberField {
              value: Math.round(Number(root.get(row.k, 0)) * row.scale)
              from: row.from
              to: row.to
              stepSize: row.step
              onModified: function (v) {
                var out = row.scale === 1 ? String(v)
                                          : String(v / row.scale)
                root.command("omavoi config set " + row.k + " " + out)
              }
            }
            OmText { text: row.unit; color: Color.muted }
            Item { Layout.fillWidth: true }
          }
          OmText {
            visible: row.why !== ""
            Layout.maximumWidth: Style.space(760)
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: row.why
            color: Qt.darker(Color.muted, 1.15)
          }
        }
      }
    }

    // ---- hud -------------------------------------------------------
    ColumnLayout {
      Layout.fillWidth: true
      spacing: Style.space(8)
      OmText {
        text: root.t("set.hud")
        font.letterSpacing: 1
        color: Color.muted
      }
      RowLayout {
        Layout.fillWidth: true
        OmText {
          Layout.preferredWidth: Style.space(160)
          text: root.t("set.keepup")
          size: "body"
          color: Color.muted
        }
        ButtonGroup {
          options: [{ value: "always", label: root.t("set.dwell.always") },
                    { value: "changed", label: root.t("set.dwell.changed") },
                    { value: "never", label: root.t("set.dwell.never") }]
          value: root.get("ui.hud_dwell", "changed")
          onChanged: function (v) { root.command("omavoi config set ui.hud_dwell " + v) }
        }
      }
      OmText {
        Layout.maximumWidth: Style.space(760)
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: root.t("set.hudnote")
        color: Qt.darker(Color.muted, 1.15)
      }
      RowLayout {
        Layout.fillWidth: true
        OmText {
          Layout.preferredWidth: Style.space(160)
          text: root.t("set.notifications")
          size: "body"
          color: Color.muted
        }
        OmChip {
          label: root.get("ui.notify", true) === true ? root.t("set.on")
                                                       : root.t("set.off")
          on: root.get("ui.notify", true) === true
          onClicked: root.command(
            "omavoi config set ui.notify " + (on ? "false" : "true"))
        }
      }
    }

    // ---- history and privacy ---------------------------------------
    ColumnLayout {
      Layout.fillWidth: true
      spacing: Style.space(8)
      OmText {
        text: root.t("set.history")
        font.letterSpacing: 1
        color: Color.muted
      }
      RowLayout {
        Layout.fillWidth: true
        OmText {
          Layout.preferredWidth: Style.space(160)
          text: root.t("set.keepaudio")
          size: "body"
          color: Color.muted
        }
        NumberField {
          value: Number(root.get("history.keep_audio", 0))
          from: 0
          to: 500
          stepSize: 5
          onModified: function (v) {
            root.command("omavoi config set history.keep_audio " + v)
          }
        }
        OmText { text: root.t("set.takes"); color: Color.muted }
        Item { Layout.fillWidth: true }
      }
      OmText {
        Layout.maximumWidth: Style.space(760)
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: root.t("set.historynote")
        color: Qt.darker(Color.muted, 1.15)
      }

      Rectangle {
        Layout.fillWidth: true
        Layout.topMargin: Style.space(6)
        implicitHeight: privacy.implicitHeight + Style.space(20)
        color: "transparent"
        border.width: 1
        border.color: Qt.rgba(Color.muted.r, Color.muted.g, Color.muted.b, 0.6)

        ColumnLayout {
          id: privacy
          anchors.left: parent.left
          anchors.right: parent.right
          anchors.top: parent.top
          anchors.margins: Style.space(10)
          spacing: Style.space(4)
          OmText {
            text: root.t("set.neverleaves")
            size: "body"
            color: "#9ece6a"
          }
          OmText {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: root.t("set.privacynote")
            color: Color.muted
          }
        }
      }
    }

    // ---- upgrading ----
    //
    // Here rather than behind a command, because the command for the daemon
    // is not the one anybody would guess.
    ColumnLayout {
      Layout.fillWidth: true
      Layout.topMargin: Style.space(10)
      spacing: Style.space(8)
      UpdateView {
        Layout.fillWidth: true
        strings: root.strings
        setupReport: root.setupReport
        onCommand: function (c) { root.command(c) }
      }
    }

    RowLayout {
      Layout.topMargin: Style.space(6)
      spacing: Style.space(8)
      Button { text: root.t("set.editconfig"); onClicked: root.command("omavoi config path") }
      Button {
        text: root.t("set.restart")
        onClicked: root.command("systemctl --user restart omavoid")
      }
      OmText {
        Layout.fillWidth: true
        text: root.t("set.configpath")
        color: Color.muted
      }
    }
  }
}
