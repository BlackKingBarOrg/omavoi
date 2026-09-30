import QtQuick
import QtQuick.Controls as Controls
import "UiLabels.js" as Labels
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
  property bool recordingBusy: false

  // Why the last command was refused, from the console. Without it a
  // refused `config set` moved nothing and said nothing.
  property string lastError: ""

  signal command(string cmd)
  // Asked of the console rather than run here: the answer is a dialog over
  // the whole card, and this view is a Flickable that would scroll it away.
  signal clearHistory()
  // Typed text goes as argv, never spliced into a shell string: a key name
  // is `[A-Z0-9_+]` once it has been checked, and what is typed here has
  // not been checked yet.
  signal commandArgs(var argv)

  property bool capturing: false
  property string captured: ""
  property bool capturedOk: false
  property int captureSeconds: 0
  onCapturingChanged: if (capturing) captureSeconds = 8
  Timer { interval: 1000; repeat: true; running: root.capturing; onTriggered: root.captureSeconds = Math.max(0, root.captureSeconds - 1) }

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
  // For the login that predates its own group membership. A plain restart
  // would not help: systemd --user has no more groups than the session it
  // belongs to. install.sh writes a runtime override that starts the daemon
  // through newgrp -- setuid root, re-reads /etc/group -- and restarts it,
  // so the key works now instead of after a logout nobody was told about
  // until they had finished setting up.
  Process {
    id: regrouper
    command: [Quickshell.env("HOME") + "/.config/omarchy/plugins/ai.bkblab.omavoi/install.sh"]
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
  // What the button next to the message does, or "" for the one thing no
  // button can do: pressing a key. Logging out used to be the other -- it is
  // not any more, because starting the daemon through newgrp does what the
  // logout was for.
  readonly property string remedy: {
    var h = root.health
    if (root.ill === "" || !h) return ""
    if (h.enabled === false || h.name_ok === false) return ""
    // A working daemon needs no remedy, and the one thing the user cannot
    // click — press a key — offers none.
    if (h.listener) return h.matches ? "" : "restart"
    if (!h.group_listed) return "group"
    if (!h.group_held) return "regroup"
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

  // What the page is laid out against: one label column, one measure for
  // prose, and a column that stops before it is a monitor wide.
  readonly property int labelWidth: Style.space(160)
  readonly property int noteWidth: Style.space(680)
  readonly property int columnWidth: Style.space(900)

  Tones { id: tones }

  // Advanced opens once and stays open while the console does.
  property bool advancedOpen: false
  // The four audio numbers and what they ship as, so the closed fold can
  // name the ones somebody moved. The same defaults config.DEFAULTS has.
  readonly property var audioRows: [
    { k: "audio.preroll_seconds", label: root.t("set.preroll"), unit: "ms",
      scale: 1000, from: 0, to: 5000, step: 100, dflt: 0.6, why: root.t("set.prerollwhy") },
    { k: "audio.tail_seconds", label: root.t("set.tail"), unit: "ms",
      scale: 1000, from: 0, to: 2000, step: 50, dflt: 0.25, why: root.t("set.tailwhy") },
    { k: "audio.warn_rms_dbfs", label: root.t("set.warnbelow"), unit: "dBFS",
      scale: 1, from: -90, to: 0, step: 1, dflt: -45, why: root.t("set.warnwhy") },
    { k: "audio.max_seconds", label: root.t("set.maxtake"), unit: "s",
      scale: 1, from: 5, to: 3600, step: 30, dflt: 300, why: root.t("set.maxwhy") }
  ]
  function advancedChanges() {
    var out = []
    for (var i = 0; i < root.audioRows.length; i++) {
      var row = root.audioRows[i]
      var now = Number(root.get(row.k, row.dflt))
      if (Math.abs(now - row.dflt) > 1e-9)
        out.push(root.t("modes.adv.kv").replace("%1", row.label)
                 .replace("%2", (row.k === "audio.max_seconds" ? Number((now / 60).toFixed(3)) + " " + root.t("unit.minutes")
                                  : row.unit === "ms" ? now + " " + root.t("unit.seconds")
                                  : now + " " + row.unit)))
    }
    return out
  }

  contentHeight: col.implicitHeight + pad * 2
  clip: true
  Controls.ScrollBar.vertical: Controls.ScrollBar {}

  // Common first, and the knobs nobody should need under Advanced at the
  // bottom: the audio timings were the second section on the page, above
  // the overlay and the history, and each came with a note about PipeWire.
  ColumnLayout {
    id: col
    x: root.pad
    y: root.pad
    width: Math.min(root.width - root.pad * 2, root.columnWidth)
    spacing: Style.space(22)

    // ---- hotkey ----------------------------------------------------
    ColumnLayout {
      Layout.fillWidth: true
      spacing: Style.space(10)
      SectionTitle { rule: false; title: root.t("set.hotkey"); note: root.t("set.hotkey.sub") }
      OmToggle {
        objectName: "hotkeyToggle"
        label: root.t("set.hotkey")
        on: root.get("hotkey.enabled", true)
        onClicked: root.commandArgs(["omavoi", "config", "set", "hotkey.enabled", on ? "false" : "true"])
      }
      RowLayout {
        Layout.fillWidth: true
        spacing: Style.space(10)
        OmText {
          Layout.preferredWidth: root.labelWidth
          text: root.t("set.key")
          size: "body"
          color: Color.muted
        }
        OmText {
          Layout.minimumWidth: Style.space(96)
          text: Labels.hotkey(root.get("hotkey.key", "?"), root.strings)
          size: "body"
          color: Color.foreground
        }
        // Pressed rather than picked from a list. Quickshell cannot read an
        // input device, but the daemon already can and already resolves key
        // names, so the capture happens there and the answer comes back here.
        //
        // The label stays short while it waits. It used to become the whole
        // sentence "waiting — press it now, or hold a combination", and the
        // three controls after it jumped along; the sentence is said in the
        // status line below, which is where this row says things.
        Button {
          objectName: "rebind"
          text: root.t("set.key.rebind")
          bordered: true
          fontSize: Style.font.caption
          enabled: !root.capturing
          onClicked: { root.captured = ""; grabber.running = true }
        }
        Button {
          text: root.t("set.key.check")
          bordered: true
          fontSize: Style.font.caption
          enabled: !root.checking
          onClicked: checker.running = true
        }
        // Typing it, as well as pressing it. Capture is the better way for
        // an ordinary key, and it is the only way the console had — which
        // leaves nowhere to put a combination you cannot comfortably hold,
        // or a key on a keyboard that is not plugged in yet. The name goes
        // through the same `config set`, so the check that refuses one no
        // keyboard emits applies here too.
        TextField {
          id: typedKey
          objectName: "typedHotkey"
          Layout.preferredWidth: Style.space(190)
          placeholderText: root.t("set.key.type")
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
          function apply() {
            var want = text.trim().toUpperCase()
            if (want === "") return
            root.commandArgs(["omavoi", "config", "set", "hotkey.key", want])
            text = ""
          }
          onAccepted: apply()
        }
        Button {
          visible: typedKey.text.trim() !== ""
          text: root.t("edit.save"); bordered: true; fontSize: Style.font.caption
          onClicked: typedKey.apply()
        }
        Button {
          visible: root.capturing
          text: root.t("word.cancel"); bordered: true; fontSize: Style.font.caption
          onClicked: { grabber.running = false; root.captured = "" }
        }
        Item { Layout.fillWidth: true }
      }

      // One line, and it is either the reason it does not work or the
      // devices it is working on. Never both, and never neither. The button
      // that fixes it sits on the same line as the reason.
      RowLayout {
        Layout.fillWidth: true
        Layout.leftMargin: root.labelWidth + Style.space(10)
        spacing: Style.space(10)
        // Its own length, not the column's: the fix button sits right after
        // the sentence rather than across the page from it.
        OmText {
          objectName: "keyStatus"
          Layout.maximumWidth: root.noteWidth
          wrapMode: Text.Wrap
          text: root.lastError !== "" ? root.lastError
                : root.capturing ? root.tf("set.key.press", root.captureSeconds)
                : root.captured !== "" ? root.captured
                : root.checking && root.ill === "" ? root.t("set.key.testing")
                : root.ill !== "" ? root.ill
                : root.health.configured !== undefined
                  ? root.tf("set.key.ok",
                            (root.health.bound_devices || []).length > 0
                            ? String(root.health.bound_devices.join(", "))
                                .replace(/\/dev\/input\/\S+ /g, "")
                            : "—")
                  : ""
          color: (root.lastError !== "" || root.captured !== "") ? Color.urgent
                 : root.capturing ? Color.accent
                 : root.ill !== "" ? Color.urgent : tones.good
        }
        Button {
          visible: root.remedy !== "" && !root.capturing
          text: root.remedy === "group" ? root.t("set.key.fix.group")
              : root.remedy === "regroup" ? root.t("set.key.fix.regroup")
              : root.t("set.key.fix.restart")
          bordered: true
          fontSize: Style.font.caption
          onClicked: {
            if (root.remedy === "group") grouper.running = true
            else if (root.remedy === "regroup") regrouper.running = true
            else restarter.running = true
          }
        }
        Item { Layout.fillWidth: true }
      }
      RowLayout {
        Layout.fillWidth: true
        spacing: Style.space(10)
        OmText {
          Layout.preferredWidth: root.labelWidth
          text: root.t("set.behaviour")
          size: "body"
          color: Color.muted
        }
        ButtonGroup {
          options: [{ value: "push_to_talk", label: root.t("set.ptt") },
                    { value: "toggle", label: root.t("set.toggle") }]
          value: root.get("hotkey.mode", "push_to_talk")
          fontSize: Style.font.caption
          onChanged: function (v) { root.command("omavoi config set hotkey.mode " + v) }
        }
      }
      OmText {
        Layout.leftMargin: root.labelWidth + Style.space(10)
        Layout.maximumWidth: root.noteWidth
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: root.t("set.hotkeynote")
        color: Color.muted
      }
    }

    MicrophoneSettings {
      Layout.fillWidth: true
      strings: root.strings
      target: String(root.get("audio.target", ""))
      recordingBusy: root.recordingBusy
      onCommandArgs: function(a) { root.commandArgs(a) }
    }

    // ---- on screen ---------------------------------------------------
    ColumnLayout {
      Layout.fillWidth: true
      spacing: Style.space(10)
      SectionTitle { title: root.t("set.hud"); note: root.t("set.hud.sub") }
      // Off, and the rest of the section goes with it: a size and a dwell for
      // an overlay that does not appear are two controls for nothing.
      RowLayout {
        Layout.fillWidth: true
        spacing: Style.space(10)
        OmText {
          Layout.preferredWidth: root.labelWidth
          text: root.t("set.hud.show")
          size: "body"
          color: Color.muted
        }
        OmToggle {
          objectName: "overlayToggle"
          label: root.get("ui.hud", true) === true ? root.t("set.on")
                                                   : root.t("set.off")
          on: root.get("ui.hud", true) === true
          onClicked: root.command(
            "omavoi config set ui.hud " + (on ? "false" : "true"))
        }
      }
      RowLayout {
        Layout.fillWidth: true
        visible: root.get("ui.hud", true) === true
        spacing: Style.space(10)
        OmText {
          Layout.preferredWidth: root.labelWidth
          text: root.t("set.keepup")
          size: "body"
          color: Color.muted
        }
        Dropdown {
          objectName: "resultPolicy"
          showLabel: false
          Layout.preferredWidth: Style.space(340)
          options: [{ value: "always", label: root.t("set.dwell.always") },
                    { value: "changed", label: root.t("set.dwell.changed") },
                    { value: "never", label: root.t("set.dwell.never") }]
          Binding on value { value: root.get("ui.hud_dwell", "changed") }
          onChanged: function (v) { root.command("omavoi config set ui.hud_dwell " + v) }
        }
      }
      OmText {
        Layout.leftMargin: root.labelWidth + Style.space(10)
        Layout.maximumWidth: root.noteWidth
        Layout.fillWidth: true
        visible: root.get("ui.hud", true) === true
        wrapMode: Text.Wrap
        text: root.t("set.hudnote")
        color: Color.muted
      }
      RowLayout {
        Layout.fillWidth: true
        visible: root.get("ui.hud", true) === true
        spacing: Style.space(10)
        OmText {
          Layout.preferredWidth: root.labelWidth
          text: root.t("set.hud.size")
          size: "body"
          color: Color.muted
        }
        ButtonGroup {
          options: [{ value: "xs", label: root.t("set.size.xs") },
                    { value: "s", label: root.t("set.size.s") },
                    { value: "m", label: root.t("set.size.m") }]
          value: root.get("ui.hud_size", "s")
          fontSize: Style.font.caption
          onChanged: function (v) { root.command("omavoi config set ui.hud_size " + v) }
        }
      }
      Rectangle {
        visible: root.get("ui.hud", true)
        Layout.leftMargin: root.labelWidth + Style.space(10)
        Layout.preferredWidth: Style.space(root.get("ui.hud_size", "s") === "xs" ? 160 : root.get("ui.hud_size", "s") === "m" ? 280 : 220)
        implicitHeight: Style.space(root.get("ui.hud_size", "s") === "m" ? 48 : root.get("ui.hud_size", "s") === "xs" ? 28 : 36)
        radius: Style.cornerRadius
        color: Color.popups.background
        border.color: Color.muted
        OmText { anchors.centerIn: parent; text: "▂ ▅ ▃ ▆ ▂   " + root.t("set.preview"); color: Color.foreground }
      }
      RowLayout {
        Layout.fillWidth: true
        spacing: Style.space(10)
        OmText {
          Layout.preferredWidth: root.labelWidth
          text: root.t("set.notifications")
          size: "body"
          color: Color.muted
        }
        OmToggle {
          objectName: "notificationToggle"
          label: root.get("ui.notify", true) === true ? root.t("set.on")
                                                       : root.t("set.off")
          on: root.get("ui.notify", true) === true
          onClicked: root.command(
            "omavoi config set ui.notify " + (on ? "false" : "true"))
        }
        OmText {
          Layout.fillWidth: true
          Layout.maximumWidth: root.noteWidth
          wrapMode: Text.Wrap
          text: root.t("set.notifynote")
          color: Color.muted
        }
      }
    }

    // ---- history and privacy ---------------------------------------
    ColumnLayout {
      Layout.fillWidth: true
      spacing: Style.space(10)
      SectionTitle { title: root.t("set.history"); note: root.t("set.history.sub") }
      RowLayout {
        Layout.fillWidth: true
        OmText { Layout.preferredWidth: root.labelWidth; text: root.t("history.save"); size: "body"; color: Color.muted }
        OmToggle {
          objectName: "historyToggle"
          label: root.get("history.enabled", true) ? root.t("set.on") : root.t("set.off")
          on: root.get("history.enabled", true)
          onClicked: root.commandArgs(["omavoi", "config", "set", "history.enabled", on ? "false" : "true"])
        }
      }
      OmText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.t("history.savenote"); color: Color.muted }
      RowLayout {
        visible: root.get("history.enabled", true)
        Layout.fillWidth: true
        OmText { Layout.preferredWidth: root.labelWidth; text: root.t("history.textcount"); size: "body"; color: Color.muted }
        NumberField {
          objectName: "historyTextCount"
          value: Number(root.get("history.keep", 500)); from: 1; to: 10000; stepSize: 50
          onModified: function(v) { root.commandArgs(["omavoi", "config", "set", "history.keep", String(v)]) }
        }
        OmText { text: root.t("set.takes"); color: Color.muted }
      }
      RowLayout {
        Layout.fillWidth: true
        spacing: Style.space(10)
        OmText {
          Layout.preferredWidth: root.labelWidth
          text: root.t("set.keepaudio")
          size: "body"
          color: Color.muted
        }
        NumberField {
          objectName: "historyAudioCount"
          enabled: root.get("history.enabled", true)
          value: Number(root.get("history.keep_audio", 0))
          from: 0
          to: 500
          stepSize: 5
          onModified: function (v) {
            root.command("omavoi config set history.keep_audio " + v)
          }
        }
        OmText { text: root.t("set.takes"); color: Color.muted }
        Button {
          text: root.t("history.noaudio"); bordered: true; fontSize: Style.font.caption
          enabled: root.get("history.enabled", true) && Number(root.get("history.keep_audio", 0)) > 0
          onClicked: root.commandArgs(["omavoi", "config", "set", "history.keep_audio", "0"])
        }
        Item { Layout.fillWidth: true }
      }
      OmText {
        Layout.leftMargin: root.labelWidth + Style.space(10)
        Layout.maximumWidth: root.noteWidth
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: root.t("set.historynote")
        color: Color.muted
      }

      // One take goes from the history tab, by right-clicking it. This is
      // the other end of that: everything, including the recordings that
      // `keep audio` has not swept yet.
      RowLayout {
        Layout.fillWidth: true
        Layout.leftMargin: root.labelWidth + Style.space(10)
        spacing: Style.space(12)
        Button {
          text: root.t("set.clearhistory")
          foreground: Color.urgent
          bordered: true
          fontSize: Style.font.caption
          onClicked: root.clearHistory()
        }
        OmText {
          Layout.maximumWidth: Style.space(520)
          Layout.fillWidth: true
          wrapMode: Text.Wrap
          text: root.t("set.clearnote")
          color: Color.muted
        }
      }

      Rectangle {
        Layout.fillWidth: true
        Layout.topMargin: Style.space(6)
        implicitHeight: privacy.implicitHeight + Style.space(20)
        color: "transparent"
        border.width: 1
        border.color: Qt.rgba(Color.muted.r, Color.muted.g, Color.muted.b, 0.6)
        radius: Style.cornerRadius

        ColumnLayout {
          id: privacy
          anchors.left: parent.left
          anchors.right: parent.right
          anchors.top: parent.top
          anchors.margins: Style.space(10)
          spacing: Style.space(4)
          // This banner was unconditional, and the console offers a remote
          // speech engine — so choosing it left a green "audio never leaves
          // this machine" standing over an engine that uploads every take.
          // A privacy claim is the worst thing here to be wrong about, and
          // the answer is one config key away.
          readonly property bool speechIsRemote:
            String(root.get("speech.backend", "")) === "api"
          // What it is uploaded to, as specifically as the config knows: the
          // explicit URL, else the provider name, else neither.
          readonly property string speechTarget: {
            var u = String(root.get("speech.api.base_url", "") || "")
            if (u !== "") return u
            var p = String(root.get("speech.api.provider", "") || "")
            // "api" only if both are empty, which ApiWhisperBackend refuses
            // to start on anyway — better than naming a field label.
            return p !== "" ? p : "api"
          }
          OmText {
            // `privacy.`, not `parent.`: inside a Layout the children's
            // parent is the layout, which happens to be the same object
            // here and would stop being it the moment anything is wrapped.
            text: privacy.speechIsRemote
                  ? root.tf("set.audioleaves", privacy.speechTarget)
                  : root.t("set.neverleaves")
            size: "body"
            color: privacy.speechIsRemote ? tones.warn : tones.good
          }
          OmText {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: privacy.speechIsRemote ? root.t("set.privacynote.api")
                                         : root.t("set.privacynote")
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
      spacing: Style.space(10)
      SectionTitle { title: root.t("up.title") }
      UpdateView {
        Layout.fillWidth: true
        strings: root.strings
        setupReport: root.setupReport
        onCommand: function (c) { root.command(c) }
      }
    }

    // ---- advanced ----------------------------------------------------
    ColumnLayout {
      Layout.fillWidth: true
      spacing: Style.space(12)
      FoldHeader {
        objectName: "settingsAdvanced"
        readonly property var changes: root.advancedChanges()
        title: root.t("modes.adv")
        open: root.advancedOpen
        summary: changes.length > 0
                 ? root.tf("modes.adv.changed", changes.join(root.t("modes.adv.sep"))) : ""
        onToggled: root.advancedOpen = !root.advancedOpen
      }

      ColumnLayout {
        objectName: "settingsAdvancedBody"
        visible: root.advancedOpen
        Layout.fillWidth: true
        spacing: Style.space(12)

        // Editable, at last. These four were plain text for as long as the
        // page existed — including audio.preroll_seconds, which is the knob
        // the clipped-onset warning tells you to reach for.
        //
        // Keep integer precision internally while displaying seconds or minutes.
        Repeater {
          model: root.audioRows
          ColumnLayout {
            readonly property var row: modelData
            Layout.fillWidth: true
            spacing: Style.space(3)
            RowLayout {
              Layout.fillWidth: true
              spacing: Style.space(10)
              OmText {
                Layout.preferredWidth: root.labelWidth
                wrapMode: Text.Wrap
                text: row.label
                size: "body"
                color: Color.muted
              }
              NumberField {
                objectName: "audioNumber:" + row.k
                id: audioNumber
                readonly property real divisor: row.unit === "ms" ? 1000 : row.k === "audio.max_seconds" ? 60 : 1
                DoubleValidator { id: audioValidator; bottom: row.from / audioNumber.divisor; top: row.to / audioNumber.divisor; decimals: 4 }
                Component.onCompleted: {
                  var divisor = this.divisor
                  field.validator = audioValidator
                  field.textFromValue = function(value, locale) { return Number(value / divisor).toLocaleString(locale, 'f', divisor === 1 ? 0 : 3).replace(/([.,]\d*?)0+$/, '$1').replace(/[.,]$/, '') }
                  field.valueFromText = function(text, locale) { return Math.round(Number.fromLocaleString(locale, text) * divisor) }
                  field.contentItem.text = Qt.binding(function() { return audioNumber.field.textFromValue(audioNumber.field.value, audioNumber.field.locale) })
                }
                value: Math.round(Number(root.get(row.k, row.dflt)) * row.scale)
                from: row.from
                to: row.to
                stepSize: row.step
                onModified: function (v) {
                  var out = row.scale === 1 ? String(v)
                                            : String(v / row.scale)
                  root.command("omavoi config set " + row.k + " " + out)
                }
              }
              OmText { text: row.unit === "ms" ? root.t("unit.seconds") : row.k === "audio.max_seconds" ? root.t("unit.minutes") : row.unit; color: Color.muted }
              Item { Layout.fillWidth: true }
            }
            OmText {
              visible: row.why !== ""
              Layout.leftMargin: root.labelWidth + Style.space(10)
              Layout.maximumWidth: root.noteWidth
              Layout.fillWidth: true
              wrapMode: Text.Wrap
              text: row.why
              color: Color.muted
            }
          }
        }

        RowLayout {
          Layout.fillWidth: true
          Layout.topMargin: Style.space(4)
          spacing: Style.space(10)
          OmText {
            Layout.preferredWidth: root.labelWidth
            wrapMode: Text.Wrap
            text: root.t("set.configfile")
            size: "body"
            color: Color.muted
          }
          // `config edit`, not `config path`. The latter prints the path to
          // stdout, which this console throws away -- so the button did
          // nothing at all.
          Button {
            text: root.t("set.editconfig")
            bordered: true
            fontSize: Style.font.caption
            onClicked: root.command("omavoi config edit")
          }
          Button {
            text: root.t("set.restart")
            bordered: true
            fontSize: Style.font.caption
            onClicked: root.command("systemctl --user restart omavoid")
          }
          Item { Layout.fillWidth: true }
        }
        OmText {
          Layout.leftMargin: root.labelWidth + Style.space(10)
          Layout.fillWidth: true
          Layout.maximumWidth: root.noteWidth
          wrapMode: Text.Wrap
          text: root.t("set.configpath")
          color: Color.muted
        }
      }
    }
  }
}
