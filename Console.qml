import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
import qs.Ui

// The console. Summoned, not kept loaded: it is five tabs of tables inside a
// process that also draws your bar, so it should only exist while it is open.
//
// Before the daemon is installed this is a setup checklist instead — a fresh
// install has no takes, no models and no daemon, so the normal view would be
// five empty panes.
Item {
  id: root

  property bool opened: false
  property string tab: "history"
  // Not ready until something says so. The optimistic default meant that on a
  // machine with no daemon the probe could not even start, onStreamFinished
  // never fired, and the console kept claiming everything was fine.
  property var setupReport: ({ ready: false, done: 0, total: 5, steps: [] })
  property var takes: []
  property int historyLimit: 40
  property bool historyHasMore: false
  property int selected: 0
  // Which row the next history load should land on. -1 means the newest,
  // which is right for every load except the one after a delete: there, the
  // row you were on is gone and what you want to be looking at is whatever
  // took its place.
  property int keepSelected: -1
  property var modesData: ({ modes: [], llm: [] })
  property var modelsData: ({ models: [] })
  property var dictData: ({ rules: [] })
  property var namesData: ({ names: [], seed: "" })
  property var configData: ({})
  // A 3 GB pull runs detached, so without this the button looks inert for
  // minutes. Cleared when a refresh reports the model as present.
  property var pulling: ({})

  // Gated on the binary existing as well as on the report, so a probe that
  // never ran cannot leave the tabs on screen with nothing behind them.
  readonly property bool ready: root.daemonPresent
                                && setupReport && setupReport.ready === true
  readonly property var take: (takes && takes.length > selected) ? takes[selected] : null

  // The checklist's root work, gathered so it can be done rather than copied.
  //
  // First-run and the update screen both install behind one button already;
  // the checklist was the one screen that handed you a command and made you
  // find a terminal. Everything it asks for is still printed before it runs.
  readonly property var rootPackages: {
    var out = []
    var steps = (root.setupReport && root.setupReport.steps) || []
    for (var i = 0; i < steps.length; i++) {
      var s = steps[i]
      if (s.done || !s.needs_root) continue
      if (String(s.command || "").indexOf("pacman") < 0) continue
      var parts = String(s.command).split(/\s+/)
      for (var j = 0; j < parts.length; j++)
        if (parts[j] !== "" && parts[j][0] !== "-"
            && parts[j] !== "sudo" && parts[j] !== "pacman")
          out.push(parts[j])
    }
    return out
  }
  readonly property bool rootGroupNeeded: {
    var steps = (root.setupReport && root.setupReport.steps) || []
    for (var i = 0; i < steps.length; i++) {
      var s = steps[i]
      if (!s.done && s.needs_root && String(s.command || "").indexOf("usermod") >= 0)
        return true
    }
    return false
  }
  readonly property var rootPlan: {
    var pkgs = root.rootPackages
    if (pkgs.length === 0 && !root.rootGroupNeeded) return []
    // One pkexec, because polkit prompts for every call: pacman is
    // auth_admin rather than auth_admin_keep. When the input group is also
    // needed it joins the same shell line rather than asking twice, exactly
    // as the first-run screen does it.
    var argv
    if (pkgs.length > 0 && root.rootGroupNeeded)
      argv = ["pkexec", "/bin/sh", "-c",
              "pacman -S --needed --noconfirm " + pkgs.join(" ")
              + " && usermod -aG input " + Quickshell.env("USER")]
    else if (pkgs.length > 0)
      argv = ["pkexec", "/usr/bin/pacman", "-S", "--needed", "--noconfirm"].concat(pkgs)
    else
      argv = ["pkexec", "/usr/bin/usermod", "-aG", "input", Quickshell.env("USER")]
    // Restarting is not tidiness. A backend remembers "llama-server is not
    // installed" for the life of the process, and reload deliberately carries
    // the registry over rather than drop resident weights -- so installing the
    // binary alone leaves the daemon still saying it is missing.
    return [
      { key: "packages", root: true, label: strings.t("first.step.packages"),
        argv: argv },
      { key: "restart", label: strings.t("up.step.restart"),
        argv: ["systemctl", "--user", "restart", "omavoid"] }
    ]
  }

  readonly property int pad: Style.space(22)
  readonly property var tabs: {
    var out = [
      { key: "history", label: strings.t("nav.history") },
      { key: "modes", label: strings.t("nav.modes") },
      { key: "models", label: strings.t("nav.models") },
      { key: "dictionary", label: strings.t("nav.dictionary") },
      { key: "settings", label: strings.t("nav.settings") }
    ]
    // Reachable while anything is still missing, which is not the same as
    // being blocked. `ready` means dictation works, and it stays true with
    // the LLM engine absent -- so the checklist, and the one button that
    // installs from it, used to be unreachable in exactly the state a person
    // needs it: everything fine except the engine a shipped mode calls for.
    if (root.setupReport && root.setupReport.done < root.setupReport.total)
      out.push({ key: "setup", label: strings.t("nav.setup") })
    return out
  }

  function open(payloadJson) {
    // A caller can land you on a specific tab: the bar module opens setup,
    // a keybinding can go straight to history.
    if (payloadJson) {
      try {
        var p = JSON.parse(payloadJson)
        if (p && p.tab) tab = String(p.tab)
      } catch (e) {}
    }
    opened = true
    refresh()
  }
  // The menu goes with it. Closing the console leaves the history tab
  // mounted, so a menu left open would still be open on the next opening,
  // over a list that has moved on since.
  function close() {
    historyView.dismissMenu()
    opened = false
  }
  function toggle() { opened ? close() : open("") }

  function refresh() {
    probeDaemon.running = true
    probeWeights.running = true
    // Everything below is an `omavoi` subprocess. On a machine that has not
    // installed it yet, asking anyway logs a failed spawn per probe, on every
    // refresh, forever — and the answer is already on screen.
    if (!root.daemonPresent) return
    probeSetup.running = true
    // The config carries the UI language, which every tab needs — not just
    // the one that displays the config.
    configProc.running = true
    if (ready) loadTab()
  }

  function loadTab() {
    if (tab === "history") { histProc.running = true; return }
    // The catalogue too: a mode names its own speech model and its own LLM
    // entries, so the pickers need to know what is on disk.
    if (tab === "modes") { modesProc.running = true; modelsProc.running = true; return }
    if (tab === "models") { modelsProc.running = true; modesProc.running = true; return }
    if (tab === "dictionary") { dictProc.running = true; namesProc.running = true; return }
    if (tab === "settings") { configProc.running = true; return }
  }

  // A command changes config on disk, so everything on screen is re-read
  // after it rather than guessed at.
  function applyArgs(argv) {
    applyBatch([argv])
  }

  function apply(cmd) {
    var pull = cmd.match(/^omavoi model pull (\S+)/)
    if (pull) {
      var next = ({})
      for (var k in pulling) next[k] = pulling[k]
      next[pull[1]] = true
      pulling = next
      slowPoll.restart()
    }
    applyArgs(["bash", "-lc", cmd])
  }

  onTabChanged: {
    historyView.dismissMenu()
    if (opened && ready) loadTab()
  }

  IpcLink { id: link }

  Tones { id: tones }

  Strings {
    id: strings
    // Before the daemon exists there is no config to read, so the first-run
    // screen's own picker is the only statement of intent there is. Without
    // this, choosing 简体中文 on that screen changed the command it would
    // run and not one word on it — the whole page stayed in English, which
    // reads as the picker being broken.
    lang: (!root.daemonPresent && firstRun.lang !== "")
          ? firstRun.lang
          : ((root.configData.ui && root.configData.ui.language) || "")
  }

  Connections {
    target: link
    // A finished take is the one thing that can invalidate the view while it
    // is open, so the list follows it rather than polling.
    function onTakeFinished(text, rejected, changes, warnings) {
      if (root.opened && root.tab === "history") histProc.running = true
    }
  }

  // Whether the daemon exists at all. Everything else on this screen assumes
  // it does; the first-run flow is what runs when it does not.
  property bool daemonPresent: true
  Process {
    id: probeDaemon
    // The exit code, not the output: a login shell can print a profile's
    // worth of noise around "yes" and the comparison then always fails.
    command: ["sh", "-c", "command -v omavoi"]
    onExited: function (code, status) { root.daemonPresent = code === 0 }
  }

  // ggml weights another tool already downloaded. Found rather than fetched:
  // three gigabytes is not worth having twice.
  //
  // Several candidates, not one. `head -1` returned whatever sorted first —
  // which the second glob makes any .bin in our own store, `ggml-base.bin`
  // included — and the first-run screen then offered "use what is here" and
  // selected large-v3-turbo regardless. The screen picks the first line it
  // recognises now, so what it offers is what it found.
  property string foundWeights: ""
  Process {
    id: probeWeights
    command: ["sh", "-lc",
              "ls -1 \"$HOME\"/.local/share/*/models/ggml-large-v3*.bin " +
              "\"$HOME\"/.local/share/omavoi/models/ggml/*.bin 2>/dev/null | head -8"]
    stdout: StdioCollector {
      onStreamFinished: root.foundWeights = text.trim()
    }
  }

  Process {
    id: probeSetup
    command: ["omavoi", "setup", "--json"]
    stdout: StdioCollector {
      onStreamFinished: {
        try { root.setupReport = JSON.parse(text) }
        catch (e) { root.setupReport = { ready: false, done: 0, total: 5, steps: [] } }
        if (root.opened && root.ready && root.takes.length === 0) root.loadTab()
        // The setup tab goes away when it has nothing left to list, and the
        // tab it was showing would otherwise stay selected with no way back
        // to it and nothing on screen.
        if (root.tab === "setup" && root.setupReport
            && root.setupReport.done >= root.setupReport.total)
          root.tab = "history"
      }
    }
  }

  Process {
    id: histProc
    command: ["omavoi", "history", "-n", String(root.historyLimit + 1), "--json"]
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          var list = JSON.parse(text)
          root.historyHasMore = list.length > root.historyLimit
          root.takes = list.reverse().slice(0, root.historyLimit)
          root.selected = root.keepSelected < 0 ? 0
                          : Math.max(0, Math.min(root.keepSelected,
                                                 root.takes.length - 1))
        } catch (e) { root.takes = [] }
        root.keepSelected = -1
      }
    }
  }

  // Serialize writes so rapid clicks and multi-field forms cannot lose a
  // command. Each action reports back to the tab that submitted it.
  property var jobs: []
  property var currentJob: null
  property int commandIndex: 0
  property bool reloading: false
  property bool restartRequired: false
  property var feedback: ({})
  property bool feedbackDetails: false
  readonly property var currentFeedback: feedback[tab] || ({})
  readonly property bool saving: currentJob !== null || jobs.length > 0
  property string lastError: ""

  function report(owner, state, detail) {
    var next = Object.assign({}, root.feedback)
    next[owner] = { state: state, detail: detail || "" }
    root.feedback = next
    root.feedbackDetails = false
  }
  function applyBatch(commands) {
    if (!commands || !commands.length) return
    var needsRestart = commands.some(function(a) {
      var line = a.join(" ")
      return /omavoi config set (audio\.|speech\.)/.test(line)
             || /omavoi model use /.test(line)
    })
    var restarts = commands.some(function(a) { return a.join(" ").indexOf("systemctl --user restart omavoid") >= 0 })
    root.jobs = root.jobs.concat([{ owner: root.tab, commands: commands,
                                  needsRestart: needsRestart, restarts: restarts }])
    root.report(root.tab, "saving", "")
    queueNext.restart()
  }
  function nextJob() {
    if (root.currentJob || !root.jobs.length) return
    root.currentJob = root.jobs[0]
    root.jobs = root.jobs.slice(1)
    root.report(root.currentJob.owner, "saving", "")
    root.commandIndex = 0
    root.reloading = false
    mutation.command = root.currentJob.commands[0]
    mutation.running = true
  }
  function finishJob(state, detail) {
    root.report(root.currentJob.owner, state, detail)
    root.currentJob = null
    root.pulling = ({})
    root.refresh()
    queueNext.restart()
  }
  Timer { id: queueNext; interval: 0; onTriggered: root.nextJob() }
  Timer { id: nextCommand; interval: root.reloading && root.currentJob && root.currentJob.restarts ? 1400 : 0; onTriggered: mutation.running = true }
  Process {
    id: mutation
    stderr: StdioCollector { id: mutationErr }
    onExited: function(code, status) {
      var why = String(mutationErr.text || "").replace(/\x1b\[[0-9;]*m/g, "").trim()
      if (root.reloading) {
        root.finishJob(code === 0 ? "saved" : "pending", why)
        return
      }
      if (code !== 0) {
        root.lastError = why
        root.finishJob("failed", why)
        return
      }
      root.lastError = ""
      if (root.currentJob.needsRestart) root.restartRequired = true
      if (root.currentJob.restarts) root.restartRequired = false
      root.commandIndex++
      if (root.commandIndex < root.currentJob.commands.length) {
        mutation.command = root.currentJob.commands[root.commandIndex]
      } else {
        root.reloading = true
        mutation.command = ["omavoi", "reload"]
      }
      nextCommand.restart()
    }
  }

  // A download says nothing until it finishes, so ask the catalogue what it
  // has while one is running.
  Timer {
    id: slowPoll
    interval: 4000
    repeat: true
    running: Object.keys(root.pulling).length > 0
    onTriggered: modelsProc.running = true
  }

  Process {
    id: modesProc
    command: ["omavoi", "mode", "list", "--json"]
    stdout: StdioCollector {
      onStreamFinished: { try { root.modesData = JSON.parse(text) } catch (e) {} }
    }
  }
  Process {
    id: modelsProc
    command: ["omavoi", "model", "list", "--json"]
    stdout: StdioCollector {
      onStreamFinished: { try { root.modelsData = JSON.parse(text) } catch (e) {} }
    }
  }
  Process {
    id: dictProc
    command: ["omavoi", "dict", "list", "--json"]
    stdout: StdioCollector {
      onStreamFinished: { try { root.dictData = JSON.parse(text) } catch (e) {} }
    }
  }
  Process {
    id: namesProc
    command: ["omavoi", "names", "list", "--json"]
    stdout: StdioCollector {
      onStreamFinished: { try { root.namesData = JSON.parse(text) } catch (e) {} }
    }
  }
  Process {
    id: configProc
    command: ["omavoi", "config", "show", "--json"]
    stdout: StdioCollector {
      onStreamFinished: { try { root.configData = JSON.parse(text) } catch (e) {} }
    }
  }

  Process { id: runner }
  function run(cmd) {
    runner.command = ["bash", "-lc", cmd]
    runner.running = true
  }

  // Same rule as argRunner above, for the commands that are not settings:
  // copying a take hands a whole dictated sentence to wl-copy.
  Process { id: argvRunner }
  function runArgv(argv) {
    argvRunner.command = argv
    argvRunner.running = true
  }

  // Why the last delete was refused. Its own property rather than
  // `lastError`, which the settings tab shows: a refused `config set` has
  // nothing to do with the history tab, and a refused delete has nothing to
  // do with settings.
  property string historyError: ""

  // The two commands that change the history. Deliberately not `applyArgs`:
  // that one reloads the daemon's config afterwards and re-reads every tab,
  // and the history is not config -- there is nothing for the daemon to pick
  // up, and nothing else on screen that a deleted take changes.
  Process {
    id: histEdit
    stderr: StdioCollector { id: histEditErr }
    onExited: function (code, status) {
      root.historyError = code === 0 ? "" : String(histEditErr.text || "").trim()
      histProc.running = true
    }
  }

  function removeTake(id) {
    if (!id) return
    root.keepSelected = root.selected
    histEdit.command = ["omavoi", "history", "rm", String(id)]
    histEdit.running = true
  }

  function clearHistory() {
    root.keepSelected = -1
    histEdit.command = ["omavoi", "history", "clear"]
    histEdit.running = true
  }

  PanelWindow {
    id: panel
    visible: root.opened
    anchors { top: true; bottom: true; left: true; right: true }
    color: Qt.rgba(0, 0, 0, 0.45)
    WlrLayershell.namespace: "omavoi-console"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive

    Item {
      anchors.fill: parent
      focus: true
      // Innermost first. The dialog takes Enter and the arrows as well as
      // Escape, and an Enter that reached the console behind it would be
      // answering a question nobody could see.
      Keys.onPressed: function (event) {
        if (root.tab === "modes" && modesView.handleKey(event)) { event.accepted = true; return }
        if (confirmClear.handleKey(event)) { event.accepted = true; return }
        if (event.key === Qt.Key_Escape) {
          if (!historyView.dismissMenu()) root.close()
          event.accepted = true
        }
      }

      MouseArea {
        anchors.fill: parent
        onClicked: root.close()
      }

      Rectangle {
        id: card
        width: Math.min(parent.width - Style.space(80), Style.space(1440))
        height: Math.min(parent.height - Style.space(80), Style.space(900))
        anchors.centerIn: parent
        color: Color.popups.background
        radius: Style.cornerRadius
        border.width: Math.max(1, Style.space(2))
        border.color: Color.accent

        // Swallow clicks so the backdrop dismissal does not fire through.
        MouseArea { anchors.fill: parent }

        // Inside the border, not over it. A Rectangle paints its border
        // beneath its children, and the header and the history list are
        // opaque, so the accent frame showed on the right and along the
        // bottom of the detail pane and nowhere else.
        ColumnLayout {
          anchors.fill: parent
          anchors.margins: card.border.width
          spacing: 0

          // ---- header -------------------------------------------------
          Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Style.space(44)
            // The card's own rounding, less the border, so a theme that
            // rounds its windows gets a header that follows the corner.
            topLeftRadius: Math.max(0, card.radius - card.border.width)
            topRightRadius: Math.max(0, card.radius - card.border.width)
            color: Qt.darker(Color.popups.background, 1.25)

            // Everything but the spacer at its own width, and the spacer the
            // only thing that grows. Where the row is short of room -- German,
            // French or Vietnamese on a 1366-pixel screen -- the tabs' padding
            // and the language picker give some up, and the state never does:
            // it is the one thing here that is news. Items a layout does not
            // fill are fixed at their preferred width, so before this the row
            // simply ran past the card and the state was cut off at the border.
            RowLayout {
              anchors.fill: parent
              anchors.leftMargin: Style.space(18)
              anchors.rightMargin: Style.space(18)
              spacing: Style.space(20)

              OmText {
                text: "OMAVOI"
                size: "subtitle"
                font.letterSpacing: 3
                color: Color.foreground
              }

              RowLayout {
                Layout.fillHeight: true
                Layout.fillWidth: true
                Layout.maximumWidth: implicitWidth
                spacing: 0
                visible: root.ready
                Repeater {
                  model: root.tabs
                  Item {
                    Layout.fillHeight: true
                    Layout.fillWidth: true
                    Layout.minimumWidth: tabLabel.implicitWidth + Style.space(12)
                    Layout.maximumWidth: implicitWidth
                    implicitWidth: tabLabel.implicitWidth + Style.space(30)
                    OmText {
                      id: tabLabel
                      anchors.centerIn: parent
                      text: modelData.label
                      size: "body"
                      color: root.tab === modelData.key ? Color.foreground : Color.muted
                    }
                    Rectangle {
                      anchors.bottom: parent.bottom
                      width: parent.width
                      height: 2
                      color: root.tab === modelData.key ? Color.accent : "transparent"
                    }
                    MouseArea {
                      anchors.fill: parent
                      cursorShape: Qt.PointingHandCursor
                      onClicked: root.tab = modelData.key
                    }
                  }
                }
              }

              Item { Layout.fillWidth: true }

              // Same row as the tabs, because it is the same kind of choice:
              // which view of the program you are looking at.
              Dropdown {
                id: languagePicker
                Layout.alignment: Qt.AlignVCenter
                Layout.fillWidth: true
                Layout.preferredWidth: Style.space(150)
                Layout.maximumWidth: Style.space(150)
                // "Tiếng Việt", the longest name on the list, still fits.
                Layout.minimumWidth: Style.space(110)
                visible: root.ready
                showLabel: false
                // The code is the value, so what comes back from `changed`
                // is what goes into the config unmapped.
                //
                // Through a Binding element rather than `value: strings.active`.
                // Omarchy's Dropdown assigns `root.value = v` when a row is
                // picked, and an assignment to a bound property removes the
                // binding -- so after one pick the label was frozen on that
                // pick for the life of the console, while everything else
                // followed the config: a screen in English under a picker that
                // said 简体中文. A Binding element re-asserts itself whenever
                // its source changes, imperative writes notwithstanding.
                Binding on value { value: strings.active }
                options: {
                  var out = []
                  for (var i = 0; i < strings.languages.length; i++)
                    out.push({ value: strings.languages[i].code,
                               label: strings.languages[i].name })
                  return out
                }
                onChanged: function (code) {
                  root.applyArgs(["omavoi", "config", "set", "ui.language", code])
                }
              }

              OmText {
                visible: root.daemonPresent
                text: root.ready
                      ? (link.state === "stopped" ? strings.t("state.stopped")
                                                  : strings.t("state." + link.state))
                      : (strings.t("setup.prefix") + root.setupReport.done
                         + "/" + root.setupReport.total)
                color: root.ready && link.state !== "stopped" ? tones.good : tones.warn
              }
            }
          }

          ColumnLayout {
            visible: root.ready && (root.currentFeedback.state !== undefined || root.restartRequired)
            Layout.fillWidth: true
            Layout.leftMargin: root.pad
            Layout.rightMargin: root.pad
            Layout.topMargin: Style.space(8)
            Layout.bottomMargin: Style.space(8)
            spacing: Style.space(5)
            RowLayout {
              Layout.fillWidth: true
              OmText {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: root.currentFeedback.state === "failed" ? strings.t("feedback.failed")
                    : root.currentFeedback.state === "saving" ? strings.t("feedback.saving")
                    : root.restartRequired ? strings.t("feedback.restart")
                    : root.currentFeedback.state === "pending" ? strings.t("feedback.pending")
                    : strings.t("feedback.saved")
                color: root.currentFeedback.state === "failed" ? Color.urgent
                     : root.restartRequired || root.currentFeedback.state === "pending" ? tones.warn : Color.foreground
              }
              Button {
                visible: root.restartRequired || root.currentFeedback.state === "pending"
                text: strings.t("set.restart")
                bordered: true; fontSize: Style.font.caption
                enabled: !root.saving && link.state !== "recording" && link.state !== "transcribing"
                onClicked: root.applyArgs(["systemctl", "--user", "restart", "omavoid"])
              }
              Button {
                visible: !!root.currentFeedback.detail
                text: strings.t("feedback.details")
                bordered: true; fontSize: Style.font.caption
                onClicked: root.feedbackDetails = !root.feedbackDetails
              }
            }
            OmText {
              visible: root.feedbackDetails && !!root.currentFeedback.detail
              Layout.fillWidth: true; wrapMode: Text.Wrap
              text: root.currentFeedback.detail || ""
              color: Color.muted
            }
          }

          // ---- first run ----------------------------------------------
          //
          // With no daemon there is nothing to interrogate, so the checklist
          // below has nothing to list. This asks the two questions instead and
          // then installs, which is the only screen a new user should meet.
          FirstRun {
            id: firstRun
            visible: !root.daemonPresent
            Layout.fillWidth: true
            Layout.fillHeight: true
            strings: strings
            daemonPresent: root.daemonPresent
            foundWeights: root.foundWeights
            onFinished: root.refresh()
          }

          // ---- setup --------------------------------------------------
          SetupView {
            visible: root.daemonPresent && (!root.ready || root.tab === "setup")
            Layout.fillWidth: true
            Layout.fillHeight: true
            strings: strings
            setupReport: root.setupReport
            rootPlan: root.rootPlan
            daemonPresent: root.daemonPresent
            pad: root.pad
            onRun: function (cmd) { root.run(cmd) }
            onRefresh: root.refresh()
          }


          // ---- history ------------------------------------------------
          HistoryView {
            id: historyView
            visible: root.ready && root.tab === "history"
            Layout.fillWidth: true
            Layout.fillHeight: true
            strings: strings
            takes: root.takes
            hasMore: root.historyHasMore
            loading: histProc.running
            onLoadMore: { root.keepSelected = root.selected; root.historyLimit += 40; histProc.running = true }
            selected: root.selected
            pad: root.pad
            hotkey: link.hotkey
            error: root.historyError
            onPick: function (i) { root.selected = i }
            onRunArgs: function (a) { root.runArgv(a) }
            onRemove: function (id) { root.removeTake(id) }
          }


          // ---- modes / models / dictionary / settings -----------------
          ModesView {
            id: modesView
            strings: strings
            visible: root.ready && root.tab === "modes"
            Layout.fillWidth: true
            Layout.fillHeight: true
            payload: root.modesData
            catalogue: root.modelsData
            onCommand: function (c) { root.apply(c) }
            onCommandArgs: function (a) { root.applyArgs(a) }
          }

          ModelsView {
            strings: strings
            visible: root.ready && root.tab === "models"
            Layout.fillWidth: true
            Layout.fillHeight: true
            payload: root.modelsData
            pulling: root.pulling
            saving: root.saving
            onCommandBatch: function(commands) { root.applyBatch(commands) }
            onCommand: function (c) { root.apply(c) }
            onCommandArgs: function (a) { root.applyArgs(a) }
          }

          DictionaryView {
            onChanged: root.refresh()
            strings: strings
            visible: root.ready && root.tab === "dictionary"
            Layout.fillWidth: true
            Layout.fillHeight: true
            rules: root.dictData.rules || []
            names: root.namesData.names || []
            onCommandArgs: function (a) { root.applyArgs(a) }
            seed: root.namesData.seed || ""
            budget: Number(root.namesData.budget || 224)
            seedChars: Number(root.namesData.seed_chars || 0)
            dropped: root.namesData.dropped || []
            onCommand: function (c) { root.apply(c) }
          }

          SettingsView {
            strings: strings
            visible: root.ready && root.tab === "settings"
            Layout.fillWidth: true
            Layout.fillHeight: true
            cfg: root.configData
            recordingBusy: link.state === "recording" || link.state === "transcribing"
            setupReport: root.setupReport
            onCommand: function (c) { root.apply(c) }
            onCommandArgs: function (a) { root.applyArgs(a) }
            onClearHistory: confirmClear.opened = true
          }
        }

        // The one destructive thing in this console that asks first.
        // Removing a mode, a model or a dictionary rule is one click here
        // and always has been -- each of those can be written again or
        // downloaded again. Every take you have ever dictated cannot.
        //
        // A child of the card rather than of the settings tab, because that
        // tab is a Flickable: inside it the dialog would scroll with the
        // page and be clipped by it.
        ConfirmDialog {
          id: confirmClear
          objectName: "clearHistoryDialog"
          anchors.fill: parent
          z: 100
          message: strings.t("set.clear.confirm")
          cancelText: strings.t("set.clear.cancel")
          confirmText: strings.t("set.clear.go")
          onCanceled: confirmClear.opened = false
          onConfirmed: {
            confirmClear.opened = false
            root.clearHistory()
          }
        }
      }
    }
  }
}
