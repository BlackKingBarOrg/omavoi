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
  property var setupReport: ({ ready: true, done: 0, total: 5, steps: [] })
  property var takes: []
  property int selected: 0
  property bool busy: false
  property var modesData: ({ modes: [], llm: [] })
  property var modelsData: ({ models: [] })
  property var dictData: ({ rules: [] })
  property var namesData: ({ names: [], seed: "" })
  property var configData: ({})
  // A 3 GB pull runs detached, so without this the button looks inert for
  // minutes. Cleared when a refresh reports the model as present.
  property var pulling: ({})

  readonly property bool ready: setupReport && setupReport.ready
  readonly property var take: (takes && takes.length > selected) ? takes[selected] : null

  readonly property int pad: Style.space(22)
  readonly property var tabs: [
    { key: "history", label: "History" },
    { key: "modes", label: "Modes" },
    { key: "models", label: "Models" },
    { key: "dictionary", label: "Dictionary" },
    { key: "settings", label: "Settings" }
  ]

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
  function close() { opened = false }
  function toggle() { opened ? close() : open("") }

  function refresh() {
    probeSetup.running = true
    if (ready) loadTab()
  }

  function loadTab() {
    if (tab === "history") { histProc.running = true; return }
    if (tab === "modes") { modesProc.running = true; return }
    if (tab === "models") { modelsProc.running = true; modesProc.running = true; return }
    if (tab === "dictionary") { dictProc.running = true; namesProc.running = true; return }
    if (tab === "settings") { configProc.running = true; return }
  }

  // A command changes config on disk, so everything on screen is re-read
  // after it rather than guessed at.
  function applyArgs(argv) {
    argRunner.command = argv
    argRunner.running = true
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
    applier.command = ["bash", "-lc", cmd]
    applier.running = true
  }

  onTabChanged: if (opened && ready) loadTab()

  IpcLink { id: link }

  Connections {
    target: link
    // A finished take is the one thing that can invalidate the view while it
    // is open, so the list follows it rather than polling.
    function onTakeFinished(text, rejected, changes, warnings) {
      if (root.opened && root.tab === "history") histProc.running = true
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
      }
    }
  }

  Process {
    id: histProc
    command: ["omavoi", "history", "-n", "40", "--json"]
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          var list = JSON.parse(text)
          root.takes = list.reverse()
          root.selected = 0
        } catch (e) { root.takes = [] }
      }
    }
  }

  Process {
    id: applier
    onExited: function (code, status) {
      root.pulling = ({})
      root.refresh()
    }
  }

  // Anything carrying user text goes as argv, never through a shell: a prompt
  // has spaces, quotes and newlines in it, and building a command line out of
  // that is a quoting bug waiting to happen.
  Process {
    id: argRunner
    onExited: function (code, status) { root.refresh() }
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
      Keys.onEscapePressed: root.close()

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

        ColumnLayout {
          anchors.fill: parent
          spacing: 0

          // ---- header -------------------------------------------------
          Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Style.space(44)
            color: Qt.darker(Color.popups.background, 1.25)

            RowLayout {
              anchors.fill: parent
              anchors.leftMargin: Style.space(18)
              anchors.rightMargin: Style.space(18)
              spacing: Style.space(20)

              Text {
                text: "OMAVOI"
                font.family: Style.font.family
                font.pixelSize: Style.font.subtitle
                font.letterSpacing: 3
                color: Color.foreground
              }

              RowLayout {
                Layout.fillHeight: true
                spacing: 0
                visible: root.ready
                Repeater {
                  model: root.tabs
                  Item {
                    Layout.fillHeight: true
                    implicitWidth: tabLabel.implicitWidth + Style.space(30)
                    Text {
                      id: tabLabel
                      anchors.centerIn: parent
                      text: modelData.label
                      font.family: Style.font.family
                      font.pixelSize: Style.font.body
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

              Text {
                text: root.ready
                      ? (link.state === "stopped" ? "daemon stopped" : link.state)
                      : ("setup " + root.setupReport.done + "/" + root.setupReport.total)
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                color: root.ready && link.state !== "stopped" ? "#9ece6a" : "#e0af68"
              }
            }
          }

          // ---- setup --------------------------------------------------
          Flickable {
            visible: !root.ready
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentHeight: setupCol.implicitHeight + root.pad * 2
            clip: true

            ColumnLayout {
              id: setupCol
              x: root.pad
              y: root.pad
              width: card.width - root.pad * 2
              spacing: Style.space(6)

              Text {
                text: "Two more pieces to install"
                font.family: Style.font.family
                font.pixelSize: Style.font.heading
                color: Color.foreground
              }
              Text {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: "Nothing here runs until you press it, and every step shows the "
                    + "exact command first. Omarchy deliberately runs nothing from inside "
                    + "a plugin folder, so this screen asks instead."
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                color: Color.muted
              }

              Repeater {
                model: root.setupReport.steps || []
                ColumnLayout {
                  Layout.fillWidth: true
                  Layout.topMargin: Style.space(12)
                  spacing: Style.space(4)

                  RowLayout {
                    spacing: Style.space(10)
                    Text {
                      text: modelData.done ? "󰄬" : (modelData.optional ? "󰅖" : "󰄰")
                      font.family: Style.font.family
                      font.pixelSize: Style.font.body
                      color: modelData.done ? "#9ece6a"
                           : (modelData.optional ? Color.muted : Color.accent)
                    }
                    Text {
                      text: modelData.title
                      font.family: Style.font.family
                      font.pixelSize: Style.font.body
                      color: Color.foreground
                    }
                    Text {
                      visible: modelData.optional && !modelData.done
                      text: "optional"
                      font.family: Style.font.family
                      font.pixelSize: Style.font.caption
                      color: Color.muted
                    }
                  }

                  Text {
                    Layout.leftMargin: Style.space(26)
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    text: modelData.detail
                    font.family: Style.font.family
                    font.pixelSize: Style.font.caption
                    color: Color.muted
                  }

                  RowLayout {
                    visible: !modelData.done && modelData.command
                    Layout.leftMargin: Style.space(26)
                    Layout.fillWidth: true
                    spacing: Style.space(10)

                    Rectangle {
                      Layout.fillWidth: true
                      implicitHeight: cmdText.implicitHeight + Style.space(12)
                      color: Qt.darker(Color.popups.background, 1.35)
                      border.width: 1
                      border.color: Color.muted
                      Text {
                        id: cmdText
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: Style.space(10)
                        text: "$ " + modelData.command
                        font.family: Style.font.family
                        font.pixelSize: Style.font.caption
                        color: Color.accent
                      }
                    }

                    Button {
                      text: modelData.needs_root ? "Copy" : "Run"
                      onClicked: {
                        if (modelData.needs_root) {
                          // Root work belongs in a terminal the user is
                          // looking at, not behind a button in a bar plugin.
                          root.run("wl-copy -- " + JSON.stringify(modelData.command))
                        } else {
                          root.run(modelData.command + " ; true")
                        }
                      }
                    }
                  }

                  Text {
                    visible: !modelData.done && modelData.note
                    Layout.leftMargin: Style.space(26)
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    text: modelData.note
                    font.family: Style.font.family
                    font.pixelSize: Style.font.caption
                    color: Qt.darker(Color.muted, 1.15)
                  }
                }
              }

              RowLayout {
                Layout.topMargin: Style.space(18)
                spacing: Style.space(10)
                Button { text: "Re-check"; onClicked: root.refresh() }
                Text {
                  text: "or run  omavoi setup  in a terminal — same steps, same order"
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                  color: Color.muted
                }
              }
            }
          }

          // ---- history ------------------------------------------------
          RowLayout {
            visible: root.ready && root.tab === "history"
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
              Layout.preferredWidth: Style.space(420)
              Layout.fillHeight: true
              color: Qt.darker(Color.popups.background, 1.12)

              ListView {
                id: list
                anchors.fill: parent
                clip: true
                model: root.takes
                delegate: Rectangle {
                  width: list.width
                  height: row.implicitHeight + Style.space(18)
                  color: index === root.selected ? Qt.rgba(Color.accent.r, Color.accent.g,
                                                           Color.accent.b, 0.12) : "transparent"
                  Rectangle {
                    width: 2; height: parent.height
                    color: index === root.selected ? Color.accent : "transparent"
                  }
                  ColumnLayout {
                    id: row
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: Style.space(14)
                    anchors.rightMargin: Style.space(14)
                    spacing: Style.space(3)
                    RowLayout {
                      Layout.fillWidth: true
                      Text {
                        text: (modelData.mode && modelData.mode.name) || "?"
                        font.family: Style.font.family
                        font.pixelSize: Style.font.caption
                        color: Color.muted
                      }
                      Item { Layout.fillWidth: true }
                      Text {
                        text: ((modelData.audio && modelData.audio.seconds) || 0).toFixed(1) + "s"
                        font.family: Style.font.family
                        font.pixelSize: Style.font.caption
                        color: (modelData.warnings && modelData.warnings.length)
                               ? "#e0af68" : Color.muted
                      }
                    }
                    Text {
                      Layout.fillWidth: true
                      elide: Text.ElideRight
                      text: modelData.text ? modelData.text
                                           : ("dropped — " + (modelData.rejected || ""))
                      font.family: Style.font.family
                      font.pixelSize: Style.font.body
                      color: modelData.text ? Color.foreground : Color.muted
                    }
                  }
                  MouseArea {
                    anchors.fill: parent
                    onClicked: root.selected = index
                  }
                }
                Text {
                  anchors.centerIn: parent
                  visible: root.takes.length === 0
                  text: "no takes yet — hold " + (link.hotkey || "your key") + " and talk"
                  font.family: Style.font.family
                  font.pixelSize: Style.font.body
                  color: Color.muted
                }
              }
            }

            // Detail. This is the answer to "why did it type that": raw model
            // output, what each rule changed, and the per-segment confidences.
            Flickable {
              Layout.fillWidth: true
              Layout.fillHeight: true
              clip: true
              contentHeight: detail.implicitHeight + root.pad * 2
              visible: root.take !== null

              ColumnLayout {
                id: detail
                x: root.pad
                y: root.pad
                width: parent.width - root.pad * 2
                spacing: Style.space(14)

                Text {
                  Layout.fillWidth: true
                  wrapMode: Text.Wrap
                  text: root.take ? (root.take.text || root.take.rejected || "") : ""
                  font.family: Style.font.family
                  font.pixelSize: Style.font.title
                  color: root.take && root.take.text ? Color.foreground : Color.muted
                }

                Flow {
                  Layout.fillWidth: true
                  spacing: Style.space(18)
                  Repeater {
                    model: {
                      if (!root.take) return []
                      var a = root.take.audio || {}, s = root.take.asr || {}
                      return [
                        { k: "audio", v: (a.seconds || 0).toFixed(2) + "s" },
                        { k: "level", v: (a.rms_dbfs || 0).toFixed(1) + " dBFS" },
                        { k: "decode", v: (s.decode_seconds || 0).toFixed(2) + "s" },
                        { k: "RTF", v: (s.rtf || 0).toFixed(3) },
                        { k: "model", v: s.model || "?" },
                        { k: "language", v: s.language || "?" },
                        { k: "mode", v: (root.take.mode && root.take.mode.name) || "?" },
                        { k: "injected", v: (root.take.inject && root.take.inject.method) || "—" }
                      ]
                    }
                    ColumnLayout {
                      spacing: 1
                      Text {
                        text: modelData.k
                        font.family: Style.font.family
                        font.pixelSize: Style.font.caption
                        color: Color.muted
                      }
                      Text {
                        text: modelData.v
                        font.family: Style.font.family
                        font.pixelSize: Style.font.body
                        color: Color.foreground
                      }
                    }
                  }
                }

                Text {
                  visible: root.take && root.take.raw_text
                           && root.take.raw_text !== root.take.text
                  Layout.fillWidth: true
                  wrapMode: Text.Wrap
                  text: "model said:  " + (root.take ? root.take.raw_text : "")
                  font.family: Style.font.family
                  font.pixelSize: Style.font.body
                  color: Color.muted
                }

                ColumnLayout {
                  Layout.fillWidth: true
                  spacing: Style.space(4)
                  visible: root.take && root.take.post
                           && root.take.post.changes && root.take.post.changes.length
                  Text {
                    text: "POST-PROCESSING"
                    font.family: Style.font.family
                    font.pixelSize: Style.font.caption
                    font.letterSpacing: 1
                    color: Color.muted
                  }
                  Repeater {
                    model: (root.take && root.take.post) ? root.take.post.changes : []
                    Text {
                      Layout.fillWidth: true
                      wrapMode: Text.Wrap
                      text: "· " + modelData
                      font.family: Style.font.family
                      font.pixelSize: Style.font.body
                      color: Color.foreground
                    }
                  }
                }

                ColumnLayout {
                  Layout.fillWidth: true
                  spacing: Style.space(4)
                  visible: root.take && root.take.asr && root.take.asr.segments
                           && root.take.asr.segments.length
                  Text {
                    text: "SEGMENT CONFIDENCE"
                    font.family: Style.font.family
                    font.pixelSize: Style.font.caption
                    font.letterSpacing: 1
                    color: Color.muted
                  }
                  Repeater {
                    model: (root.take && root.take.asr) ? root.take.asr.segments : []
                    RowLayout {
                      Layout.fillWidth: true
                      spacing: Style.space(12)
                      Text {
                        Layout.preferredWidth: Style.space(96)
                        text: (modelData.start || 0).toFixed(2) + "–" + (modelData.end || 0).toFixed(2)
                        font.family: Style.font.family
                        font.pixelSize: Style.font.caption
                        color: Color.muted
                      }
                      Rectangle {
                        Layout.preferredWidth: Style.space(92)
                        Layout.preferredHeight: 5
                        color: Qt.darker(Color.muted, 1.5)
                        Rectangle {
                          width: parent.width * Math.max(0, Math.min(1,
                                 1 + (modelData.avg_logprob || 0) / 1.5))
                          height: parent.height
                          color: (modelData.avg_logprob || 0) < -1.0 ? "#e0af68" : "#9ece6a"
                        }
                      }
                      Text {
                        Layout.preferredWidth: Style.space(52)
                        text: (modelData.avg_logprob || 0).toFixed(2)
                        font.family: Style.font.family
                        font.pixelSize: Style.font.caption
                        color: Color.muted
                      }
                      Text {
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                        text: modelData.text || ""
                        font.family: Style.font.family
                        font.pixelSize: Style.font.body
                        color: Color.foreground
                      }
                    }
                  }
                }

                Repeater {
                  model: root.take ? (root.take.warnings || []) : []
                  Text {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    text: "! " + modelData
                    font.family: Style.font.family
                    font.pixelSize: Style.font.caption
                    color: "#e0af68"
                  }
                }

                RowLayout {
                  Layout.topMargin: Style.space(6)
                  spacing: Style.space(8)
                  Button {
                    text: "Copy"
                    onClicked: root.run("omavoi last --raw | wl-copy")
                  }
                  Button {
                    text: "Play"
                    visible: root.take && root.take.wav
                    onClicked: root.run("pw-play " + JSON.stringify(root.take.wav))
                  }
                }
              }
            }
          }

          // ---- modes / models / dictionary / settings -----------------
          ModesView {
            visible: root.ready && root.tab === "modes"
            Layout.fillWidth: true
            Layout.fillHeight: true
            payload: root.modesData
            onCommand: function (c) { root.apply(c) }
            onCommandArgs: function (a) { root.applyArgs(a) }
          }

          ModelsView {
            visible: root.ready && root.tab === "models"
            Layout.fillWidth: true
            Layout.fillHeight: true
            payload: root.modelsData
            running: link.backend
            pulling: root.pulling
            onCommand: function (c) { root.apply(c) }
          }

          DictionaryView {
            visible: root.ready && root.tab === "dictionary"
            Layout.fillWidth: true
            Layout.fillHeight: true
            rules: root.dictData.rules || []
            names: root.namesData.names || []
            seed: root.namesData.seed || ""
            onCommand: function (c) { root.apply(c) }
          }

          SettingsView {
            visible: root.ready && root.tab === "settings"
            Layout.fillWidth: true
            Layout.fillHeight: true
            cfg: root.configData
            setupReport: root.setupReport
            onCommand: function (c) { root.apply(c) }
          }
        }
      }
    }
  }
}
