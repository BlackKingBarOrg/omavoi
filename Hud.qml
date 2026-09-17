import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
import qs.Ui

// The recording HUD: a 28px strip, one notch off the bar's height, so it
// reads as system chrome rather than a dialog. It is kept loaded because it
// has to be on screen the instant the key goes down — mounting it on demand
// would show up as a stutter at the start of every take.
Item {
  id: root

  // ui.hud_size, which was declared with three values and implemented as the
  // constant 28. It scales the geometry and not the type: the font comes from
  // the theme through OmText, and overriding pixelSize here would take the
  // strip out of step with every other surface in the shell. xs is a strip
  // that reads as a status light, m one you can see from across the desk.
  readonly property real sizeScale: link.hudSize === "xs" ? 0.78
                                  : link.hudSize === "m" ? 1.25
                                  : 1.0
  readonly property int barH: Style.space(Math.round(28 * sizeScale))
  // The meter is 24 bars; these are what make it wider or taller, and they are
  // read where the bars are built.
  readonly property int meterBar: Math.max(1, Math.round(2 * sizeScale))
  readonly property int meterPeak: Math.round(10 * sizeScale)

  // idle | recording | transcribing | done | rejected
  property string phase: "idle"
  property string doneText: ""
  property bool doneFlagged: false
  property int doneChanges: 0
  property string rejectedWhy: ""

  // `ui.hud = false` means no overlay at all — the setting existed and
  // nothing read it, so the only way to turn the HUD off was not to run the
  // shell. Recording and transcribing are suppressed with everything else:
  // a HUD that is off but still flashes on every take is not off.
  readonly property bool open: phase !== "idle" && link.hudEnabled
  readonly property bool quiet: link.level > 0 && link.level < 0.02

  readonly property color edge: {
    if (phase === "done") return quiet ? Color.foreground : "#9ece6a"
    if (phase === "rejected") return Color.muted
    if (quiet && phase === "recording") return "#e0af68"
    return Color.accent
  }

  IpcLink { id: link }

  // The overlay's own table. Strings.qml is documented as one instance per
  // root component and had exactly one, in the console — so the surface you
  // see on every take was the only one never translated, and said "no
  // speech" in English whatever language the rest of the shell was in.
  //
  // The language comes from the daemon rather than from Qt.locale(), which
  // is the same reason the console reads it from the config: a locale is a
  // guess and ui.language is an answer. It arrives in the status snapshot
  // and again on every reload, so switching language in the console moves
  // this without a shell restart.
  Strings {
    id: strings
    lang: link.uiLang
  }

  Connections {
    target: link
    function onStateChanged() {
      if (link.state === "recording") { root.phase = "recording"; dwell.stop() }
      else if (link.state === "transcribing") root.phase = "transcribing"
      else if (link.state === "idle" || link.state === "stopped") {
        // A finished take sends its result just before going idle, and that
        // result owns the screen until the dwell timer says otherwise. Only
        // clear a take that never produced one — a cancel, or a daemon that
        // went away mid-recording.
        if (root.phase === "recording" || root.phase === "transcribing") {
          root.phase = "idle"
          dwell.stop()
        }
      }
    }
    function onTakeFinished(text, rejected, changes, warnings) {
      root.doneChanges = changes
      root.doneFlagged = (warnings && warnings.length > 0)
      if (rejected) {
        root.phase = "rejected"
        root.rejectedWhy = rejected
      } else if (link.hudDwell === "never") {
        // Straight to idle, not a 1 ms dwell: a short timer still puts the
        // result on screen for a frame, and one frame of text you asked not
        // to be shown is the thing "never" is for.
        root.phase = "idle"
        dwell.stop()
        return
      } else {
        root.phase = "done"
        root.doneText = text
      }
      dwell.interval = root._dwellFor()
      dwell.restart()
    }
  }

  // ui.hud_dwell, which until now was a control in the settings page that
  // wrote a config key nothing read: this function hardcoded "changed" and
  // the other two choices did nothing at all.
  //
  //   changed  lingers only when there was something to see (the default: a
  //            dwell you always pay for becomes noise the moment you dictate
  //            two sentences in a row, but a silent correction you never saw
  //            is worse)
  //   always   lingers on every take, for reading back what was typed
  //   never    no result frame — the strip goes when the take does
  //
  // A rejection always lingers, under every policy. It is the one frame that
  // says why nothing was typed, and "never" means "do not show me my own
  // text", not "do not tell me it failed".
  function _dwellFor() {
    if (phase === "rejected") return 1600
    if (link.hudDwell === "always") return 1400
    if (doneFlagged || doneChanges > 0) return 1400
    return 350
  }

  Timer { id: dwell; onTriggered: root.phase = "idle" }

  // Something to animate against while a take is being processed. During
  // recording the meter moves because link.level moves; during processing
  // there is nothing coming in, so the bars sat at their minimum height and
  // the strip looked frozen — for a quarter of a second with whisper alone,
  // and for as long as an LLM step takes with one configured.
  //
  // A timer rather than a NumberAnimation on a property: it runs only while
  // the phase needs it, so nothing ticks between takes.
  property real pulse: 0
  Timer {
    interval: 60
    repeat: true
    running: root.open && root.phase === "transcribing"
    onTriggered: root.pulse += 0.06
  }

  IpcHandler {
    target: "omavoi-hud"
    function state(): string { return root.phase }
    function ping(): string { return "ok" }
  }

  PanelWindow {
    id: panel
    visible: root.open
    anchors { top: true; bottom: true; left: true; right: true }
    color: "transparent"
    WlrLayershell.namespace: "omavoi-hud"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    exclusionMode: ExclusionMode.Ignore
    // Visual only: never take a click away from the window being dictated into.
    mask: Region {}

    Rectangle {
      id: strip
      height: root.barH
      width: content.implicitWidth + Style.space(16)
      anchors.horizontalCenter: parent.horizontalCenter
      anchors.bottom: parent.bottom
      anchors.bottomMargin: Style.gapsOut
      color: Color.popups.background
      radius: Style.cornerRadius
      border.width: 1
      border.color: root.edge
      opacity: root.open ? 1 : 0
      Behavior on opacity { NumberAnimation { duration: 110 } }
      Behavior on width { NumberAnimation { duration: 90 } }

      Row {
        id: content
        anchors.centerIn: parent
        spacing: Style.space(8)

        // Status dot, or a tick / cross once the take is over.
        OmText {
          anchors.verticalCenter: parent.verticalCenter
          size: "bodySmall"
          color: root.edge
          text: {
            if (root.phase === "recording") return "󰑊"
            if (root.phase === "transcribing") return "󰑫"
            if (root.phase === "done") return "󰄬"
            return "󰅖"
          }
        }

        // Live meter. The three dim bars on the left stand for the pre-roll —
        // audio captured before the key went down. No label: you learn what
        // they are by watching, and the explanation lives in the console.
        Row {
          visible: root.phase === "recording" || root.phase === "transcribing"
          anchors.verticalCenter: parent.verticalCenter
          spacing: root.meterBar
          Repeater {
            model: 24
            Rectangle {
              width: root.meterBar
              height: {
                if (index < 3) return root.meterBar * (1.5 + (index % 2) * 1.5)
                if (root.phase === "transcribing") {
                  // A travelling bump, not a level: nothing is coming in to
                  // measure, and pretending otherwise would be a meter that
                  // reads as input when there is none. One narrow peak
                  // moving left to right says "working" and says nothing
                  // about how far along it is, which is the truth — no
                  // stage here knows its own duration.
                  var at = (index - 3) / 20
                  var head = (root.pulse % 1.4) / 1.4
                  var near = Math.abs(at - head)
                  if (near > 0.18) return root.meterBar
                  var lift = Math.cos(near / 0.18 * Math.PI / 2)
                  return Math.round(root.meterBar + lift * root.meterPeak * 0.7)
                }
                var reach = Math.max(0, Math.min(1, link.level * 6))
                var pos = (index - 3) / 20
                var env = Math.sin(pos * Math.PI * 3.1 + link.seconds * 5) * 0.5 + 0.5
                return Math.max(root.meterBar,
                                Math.round(root.meterBar + reach * env * root.meterPeak))
              }
              radius: 0
              color: index < 3 ? Color.muted
                   : (root.phase === "transcribing" ? Qt.darker(Color.muted, 1.4) : root.edge)
              anchors.verticalCenter: parent.verticalCenter
              Behavior on height { NumberAnimation { duration: 60 } }
            }
          }
        }

        // Which phase, when a take is in one. "transcribing" covers the
        // speech pass, the rules, every LLM step and the injection, and a
        // ten-second wait with no word about which of those it is reads as
        // a program that has stopped.
        OmText {
          visible: root.phase === "transcribing" && link.stage !== ""
          anchors.verticalCenter: parent.verticalCenter
          text: {
            var label = strings.t("hud.stage." + link.stage)
            return link.stageDetail !== "" ? label + " " + link.stageDetail
                                           : label
          }
          color: Color.muted
        }

        // The text that was actually typed, so you get to see it before it goes.
        OmText {
          visible: root.phase === "done" || root.phase === "rejected"
          anchors.verticalCenter: parent.verticalCenter
          size: "body"
          color: root.phase === "done" ? Color.foreground : Color.muted
          elide: Text.ElideRight
          width: Math.min(implicitWidth, Style.space(Math.round(420 * root.sizeScale)))
          text: root.phase === "done" ? root.doneText
                                      : strings.t("hud.nospeech")
        }

        // How many rules touched the text. Which ones is a console question;
        // here it only has to register that something changed.
        OmText {
          visible: root.phase === "done" && root.doneChanges > 0
          anchors.verticalCenter: parent.verticalCenter
          color: Color.accent
          text: "·" + root.doneChanges
        }

        OmText {
          visible: root.phase === "rejected"
          anchors.verticalCenter: parent.verticalCenter
          color: Color.muted
          elide: Text.ElideRight
          width: Math.min(implicitWidth, Style.space(260))
          text: root.rejectedWhy
        }

        OmText {
          visible: root.phase === "recording"
          anchors.verticalCenter: parent.verticalCenter
          size: "body"
          color: Color.foreground
          text: {
            var t = Math.floor(link.seconds)
            return Math.floor(t / 60) + ":" + (t % 60 < 10 ? "0" : "") + (t % 60)
          }
        }
      }
    }
  }
}
