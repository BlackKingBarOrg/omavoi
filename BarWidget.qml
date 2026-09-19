import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

// The bar module, and — before anything else is installed — the only way in.
// So it appears on a bare plugin install rather than hiding, and it does so
// in the accent colour rather than red: there is something to do, nothing is
// broken.
BarWidget {
  id: root
  moduleName: "ai.bkblab.omavoi"

  // Not ready until something says so. The console carried the optimistic
  // default and its own comment records what that cost: on a machine with no
  // daemon the probe could not even start, so it kept claiming everything was
  // fine. `setupKnown` is what lets the default be correct without flashing a
  // badge on a working machine for the frame before the first answer.
  property bool setupKnown: false
  property bool setupReady: false
  property int setupDone: 0
  property int setupTotal: 5

  // Whether the command exists, asked once. `link.state === "stopped"` only
  // means nothing is answering the socket, which is equally true of a daemon
  // that is restarting -- and reading that as "not installed" put "Setup" on
  // the bar of a working machine every time the unit bounced.
  property bool installed: true
  property bool installedKnown: false
  Process {
    id: probeInstalled
    // The exit code, not the output: a login shell prints a profile's worth
    // of noise around the answer.
    command: ["sh", "-c", "command -v omavoi"]
    onExited: function (code, status) {
      root.installed = code === 0
      root.installedKnown = true
    }
  }

  readonly property bool recording: link.state === "recording"
  readonly property bool working: link.state === "transcribing"
  // Three states, not one. Order matters: with nothing installed the socket
  // is dead too, so that has to be answered first.
  readonly property bool missing: installedKnown && !installed
  readonly property bool serviceDown: installedKnown && installed
                                      && link.state === "stopped"
  readonly property bool needsSetup: installed && setupKnown && !setupReady
                                     && !recording && !working && !serviceDown

  // The bar's own table. It followed Qt.locale() by having no table at all:
  // seven English sentences compiled in, on the one surface that is on screen
  // whatever else is. `uiLang` is the configured answer rather than the
  // locale's guess, and it arrives in the daemon's status snapshot -- empty,
  // before the daemon is up, still means "follow the locale".
  Strings {
    id: strings
    lang: link.uiLang
  }
  function t(k) { return strings.t(k) }
  function tf(k, a) { return strings.tf(k, a) }

  implicitWidth: reading.visible ? reading.implicitWidth : button.implicitWidth
  implicitHeight: button.implicitHeight

  function _clock(s) {
    var t = Math.max(0, Math.floor(s))
    return Math.floor(t / 60) + ":" + (t % 60 < 10 ? "0" : "") + (t % 60)
  }

  IpcLink { id: link }

  Component.onCompleted: probeInstalled.running = true

  // Setup state is asked for, not pushed: it changes only when the user acts,
  // and a 15 s check costs nothing next to a subscription that would have to
  // stay meaningful for the whole session.
  Process {
    id: probe
    command: ["omavoi", "setup", "--json"]
    stdout: StdioCollector {
      onStreamFinished: {
        root.setupKnown = true
        try {
          var r = JSON.parse(text)
          root.setupReady = !!r.ready
          root.setupDone = r.done || 0
          root.setupTotal = r.total || 5
        } catch (e) {
          root.setupReady = false
        }
      }
    }
  }

  // Only while the daemon is up and something is still missing. This was the
  // one timer in the plugin with an unconditional `running: true` -- every
  // sibling is gated on a condition -- and a bar widget is instantiated once
  // per monitor, so on a two-monitor machine it spawned `omavoi setup --json`
  // twice every fifteen seconds for the life of the session: after setup was
  // finished, to re-ask a question whose answer had stopped changing, and
  // before the daemon existed at all, as a pair of processes that could not
  // start and two warnings in the journal.
  //
  // Both halves come from the same mistake, which is asking. With no daemon
  // there is nothing to ask and nothing to ask it with -- IpcLink already
  // knows, and `missing` puts "Setup" on the bar without a single process.
  // Once setup is complete there is nothing left to learn. So the window
  // where this question is worth asking is exactly: daemon up, setup
  // unfinished, which is the minutes of a first run.
  //
  // A setup that comes apart later -- a package removed by hand -- is caught
  // by the re-probe below on the next take, and by the console, which probes
  // on its own when it opens.
  Timer {
    interval: 15000
    repeat: true
    running: link.alive && !root.setupReady
    onTriggered: if (!root.recording && !root.working) probe.running = true
  }

  Connections {
    target: link
    // A daemon coming up is what makes the question answerable, so this is
    // the probe's way in as well as its refresh: the timer above cannot run
    // until something is alive to answer.
    function onStateChanged() { if (link.state === "idle") probe.running = true }
    function onAliveChanged() { if (link.alive) probe.running = true }
  }

  // Two buttons rather than one, because they measure differently.
  // BarIconButton reserves a fixed icon slot and centres a glyph optically in
  // it; anything wider than the glyph spills over its neighbour. So the states
  // that carry a reading use WidgetButton, which is sized by its text — the
  // same component the clock uses.
  WidgetButton {
    id: reading
    // The uninstalled state used to be excluded here and fell through to the
    // glyph-only button, which on a fresh bar is an unlabelled download arrow
    // among seven other icons — indistinguishable from a system downloads
    // indicator, at the one moment the module is the only way in. It is the
    // state that most needs a word next to it, so it gets one.
    visible: root.recording || root.missing || root.serviceDown
             || root.needsSetup
    anchors.fill: parent
    bar: root.bar
    fontSize: Style.font.bodySmall
    text: root.recording ? "󰑊  " + root._clock(link.seconds)
          : root.missing ? "󰍬  " + root.t("nav.setup")
          : root.serviceDown ? "󰍬  " + root.t("bar.stopped")
          : "󰍬  " + root.setupDone + "/" + root.setupTotal
    active: root.recording
    tooltipText: root.recording
                 ? root.t("bar.tip.recording")
                 : root.missing
                   ? root.t("bar.tip.notinstalled")
                   : root.serviceDown
                     ? root.t("bar.tip.stopped")
                     : root.tf("bar.tip.unfinished",
                               root.setupDone + "/" + root.setupTotal)
    onPressed: function (b) { root.handle(b) }
  }

  BarIconButton {
    id: button
    visible: !reading.visible
    anchors.fill: parent
    bar: root.bar
    // Every state that needs a word beside the glyph is handled by the
    // button above, so this one is the working machine: idle, or mid-take.
    text: root.working ? "󰑫" : "󰍬"
    // `active` is the bar's own attention colour, which this theme already
    // reserves for recording modules.
    active: root.recording
    tooltipText: {
      if (root.working) return root.t("bar.tip.transcribing")
      // Right-click starts and stops a take by hand. It is the way in when
      // the key is not working yet, and it was written down nowhere.
      return (link.backend || root.t("bar.tip.ready"))
             + (root.setupReady ? "\n" + root.t("bar.tip.rightclick") : "")
    }
    onPressed: function (b) { root.handle(b) }
  }

  function handle(b) {
    if (b === Qt.RightButton && root.setupReady) {
      // Start or stop a take by hand. The hotkey normally does this inside
      // the daemon; this is for when the key is not set up yet.
      link.send("record")
    } else {
      root.bar.run("omarchy-shell shell toggle ai.bkblab.omavoi")
    }
  }
}
