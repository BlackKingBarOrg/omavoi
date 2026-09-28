import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import Quickshell.Io
import qs.Commons
import qs.Ui

Item {
  id: root
  property var strings: null
  property var rules: []
  property var names: []
  property string seed: ""
  property int budget: 224
  property int seedChars: 0
  property var dropped: []
  property var cli: ["omavoi"]
  property var payload: ({ entries: [], modes: [] })
  property bool loaded: false
  property bool legacy: false
  property bool editing: false
  property bool more: false
  property bool corrections: false
  property bool discardPrompt: false
  property var original: ({})
  property var selectedModes: []
  property string draftBaseline: ""
  property string note: ""
  property string error: ""
  property string detail: ""
  property string previewText: ""
  property bool pendingActivation: false
  property var undoEntry: null
  // The editor's three options, which the draft is built from.
  property bool hintOn: true
  property bool caseOn: true
  property bool soundOn: false
  Tones { id: tones }
  readonly property bool busy: reader.running || writer.running
  readonly property int pad: Style.space(22)
  readonly property var filtered: (payload.entries || []).filter(function(e) {
    var q = search.text.trim().toLocaleLowerCase()
    return !q || (e.text + " " + e.aliases.join(" ")).toLocaleLowerCase().indexOf(q) >= 0
  })
  signal command(string cmd)
  signal commandArgs(var argv)
  signal changed()
  function t(k) { return strings ? strings.t(k) : k }
  function tf(k, value) { return strings ? strings.tf(k, value) : k }
  function refresh() { if (!busy) reader.running = true }
  function errorText(code) {
    var keys = {
      changed_elsewhere: "word.stale", duplicate_word: "word.duplicate",
      alias_conflict: "word.conflict", target_conflict: "word.conflict",
      invalid_text: "word.invalid", already_correct: "word.correct",
      invalid_mode: "word.invalidmode", not_found: "word.missing",
      restart_required: "word.restart"
    }
    return t(keys[code] || "word.failed")
  }
  function openEditor(entry) {
    original = entry ? JSON.parse(JSON.stringify(entry)) : ({})
    spelling.text = original.text || ""
    hintOn = original.recognition_hint !== false
    caseOn = original.normalize_case !== false
    soundOn = !!(original.phonetic && original.phonetic.enabled)
    selectedModes = (original.modes || []).slice()
    aliases.clear()
    ;(original.aliases || []).forEach(function(a) { aliases.append({value: a}) })
    corrections = aliases.count > 0
    more = false
    error = ""; detail = ""; previewText = ""; sample.text = ""
    discardPrompt = false
    editing = true
    draftBaseline = JSON.stringify(draft())
    spelling.forceActiveFocus()
  }
  function draft() {
    var values = []
    for (var i = 0; i < aliases.count; i++) {
      var value = aliases.get(i).value.trim()
      if (value) values.push(value)
    }
    return { id: original.id || "", text: spelling.text.trim(), aliases: values,
      enabled: original.enabled !== false, recognition_hint: hintOn,
      normalize_case: caseOn,
      phonetic: {enabled: soundOn, method: original.phonetic ? original.phonetic.method : "auto"},
      modes: selectedModes.slice() }
  }
  function closeEditor() {
    if (busy) return
    if (JSON.stringify(draft()) !== draftBaseline) { discardPrompt = true; return }
    editing = false
  }
  function send(action, body) {
    if (busy) return
    error = ""; detail = ""
    writer.action = action
    writer.pending = JSON.stringify(Object.assign({etag: payload.etag}, body || {}))
    writer.command = cli.concat(["vocabulary", action, "--json-input"])
    writer.stdinEnabled = true
    writer.running = true
  }
  function save() { if (spelling.text.trim() && !busy) send("save", {entry: draft()}) }
  function toggleEntry(entry) {
    var next = JSON.parse(JSON.stringify(entry))
    next.enabled = !next.enabled
    send("save", {entry: next})
  }
  onSelectedModesChanged: previewText = ""
  onVisibleChanged: if (visible) refresh()
  Component.onCompleted: if (visible) refresh()
  Keys.onEscapePressed: function(event) {
    // The row menu first, then the editor. Specific Keys handlers accept the
    // event by default; the console receives Escape when neither is open.
    if (root.menuEntry !== null) { root.menuEntry = null; event.accepted = true; return }
    event.accepted = editing
    if (editing) closeEditor()
  }

  Process {
    id: reader
    command: root.cli.concat(["vocabulary", "list", "--json"])
    stdout: StdioCollector { id: readOut }
    stderr: StdioCollector { id: readErr }
    onExited: function(code, status) {
      try {
        var value = JSON.parse(readOut.text)
        if (!value.ok) throw new Error(value.detail || "")
        root.payload = value
        root.loaded = true
        root.legacy = (value.migration_issues || []).length > 0
        root.detail = root.legacy ? value.migration_issues.join("\n") : ""
        root.error = ""
      } catch (e) {
        // An old daemon remains fully usable; other failures are not an empty list.
        var oldVersion = /invalid choice[^\n]*vocabulary/.test(String(readErr.text))
        root.legacy = oldVersion
        root.error = oldVersion ? "" : root.t("word.readfailed")
        root.detail = String(readErr.text || e)
      }
    }
  }
  Process {
    id: writer
    property string action: ""
    property string pending: ""
    stdinEnabled: true
    stdout: StdioCollector { id: writeOut }
    stderr: StdioCollector { id: writeErr }
    onStarted: {
      write(writer.pending)
      writer.pending = ""
      stdinEnabled = false
    }
    onExited: function(code, status) {
      try {
        var result = JSON.parse(writeOut.text)
        if (!result.ok) {
          root.error = root.errorText(result.error)
          root.detail = result.detail || ""
          return
        }
        if (action === "preview") {
          root.previewText = result.after
          return
        }
        root.pendingActivation = result.activation === "pending"
        root.note = root.t(root.pendingActivation ? "word.pending" : action === "remove" ? "word.deleted" : "word.saved")
        if (result.entries) root.payload = result
        if (action === "remove") root.undoEntry = result.removed
        else if (action !== "reload") root.undoEntry = null
        if (action === "save") {
          root.editing = false
          search.text = ""
        }
        root.changed()
      } catch (e) {
        root.error = root.t("word.failed")
        root.detail = String(writeErr.text || e)
      }
    }
  }
  ListModel { id: aliases }

  // The row menu: pause and delete. A QtQuick.Controls Menu is a window of
  // its own drawn in the platform's default style — light grey and in a
  // proportional font on a dark console — so it is drawn here instead, the
  // way the History tab draws its right-click menu.
  property var menuEntry: null
  property real menuX: 0
  property real menuY: 0
  function openMenu(entry, point) {
    root.menuEntry = entry
    root.menuX = point.x
    root.menuY = point.y
  }
  function fireMenu(key) {
    var entry = root.menuEntry
    root.menuEntry = null
    if (!entry) return
    if (key === "toggle") root.toggleEntry(entry)
    else if (key === "delete") root.send("remove", {id: entry.id})
  }

  ColumnLayout {
    anchors.fill: parent
    anchors.margins: root.pad
    spacing: Style.space(12)
    visible: !root.editing
    RowLayout {
      Layout.fillWidth: true
      spacing: Style.space(12)
      ColumnLayout {
        Layout.fillWidth: true
        spacing: Style.space(3)
        // In capitals, as every other page's section titles are written.
        OmText { text: root.t("nav.dictionary"); size: "subtitle"; font.letterSpacing: 1; font.capitalization: Font.AllUppercase; color: Color.foreground }
        OmText { Layout.fillWidth: true; Layout.maximumWidth: Style.space(680); wrapMode: Text.Wrap; text: root.t("word.intro"); color: Color.muted }
      }
      Item { Layout.fillWidth: true }
      Button {
        objectName: "addWord"
        text: root.t("word.add"); bordered: true; focusable: true
        fontSize: Style.font.caption
        visible: !root.legacy
        enabled: root.loaded && !root.busy
        onClicked: root.openEditor(null)
      }
    }
    OmText {
      visible: root.legacy
      Layout.fillWidth: true; wrapMode: Text.Wrap
      text: root.t("word.legacy"); color: Color.muted
    }
    OmText {
      visible: root.legacy && root.detail !== ""
      Layout.fillWidth: true; wrapMode: Text.Wrap
      text: root.detail; color: Color.muted
    }
    RowLayout {
      visible: root.note !== "" && !root.legacy
      Layout.fillWidth: true
      spacing: Style.space(10)
      OmText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.note; color: tones.good }
      Button { visible: root.pendingActivation; text: root.t("word.retry"); bordered: true; fontSize: Style.font.caption; focusable: true; onClicked: root.send("reload", {}) }
      Button { visible: !!root.undoEntry; text: root.t("word.undo"); bordered: true; fontSize: Style.font.caption; focusable: true; onClicked: root.send("restore", {entry: root.undoEntry}) }
    }
    OmText {
      visible: (root.payload.dropped || []).length > 0 && !root.legacy
      Layout.fillWidth: true; wrapMode: Text.Wrap
      text: root.tf("word.capacity", (root.payload.dropped || []).join(root.t("word.sep")))
      color: Color.muted
    }
    RowLayout {
      visible: root.error !== ""
      Layout.fillWidth: true
      spacing: Style.space(10)
      OmText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.error; color: Color.urgent }
      Button { text: root.t("word.retry"); bordered: true; fontSize: Style.font.caption; focusable: true; onClicked: root.refresh() }
    }
    TextField {
      id: search
      objectName: "dictionarySearch"
      visible: !root.legacy
      Layout.fillWidth: true
      placeholderText: root.t("word.search")
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
    }
    OmText {
      visible: !root.legacy && root.loaded && root.filtered.length === 0
      Layout.fillWidth: true; wrapMode: Text.Wrap
      text: root.t(search.text ? "word.noresults" : "word.empty"); color: Color.muted
    }
    OmText { visible: !root.loaded && !root.legacy && !root.error; text: root.t("word.loading"); color: Color.muted }
    // One line per word, and the line is the way in: clicking it edits the
    // word. Each row was a boxed card with a full-size "Edit word" button in
    // it, and a page of fifteen of them was fifteen boxes and fifteen
    // identical buttons.
    ListView {
      id: entries
      objectName: "dictionaryList"
      visible: !root.legacy
      Layout.fillWidth: true; Layout.fillHeight: true
      clip: true
      model: root.filtered
      spacing: 0
      Controls.ScrollBar.vertical: Controls.ScrollBar {}
      delegate: Rectangle {
        id: row
        required property var modelData
        required property int index
        width: entries.width
        height: rowContent.implicitHeight + Style.space(18)
        color: rowHover.containsMouse
               ? Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.05)
               : "transparent"
        Rectangle {
          anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
          height: 1
          color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.08)
        }
        MouseArea {
          id: rowHover
          anchors.fill: parent
          hoverEnabled: true
          cursorShape: Qt.PointingHandCursor
          enabled: !root.busy
          onClicked: root.openEditor(row.modelData)
        }
        RowLayout {
          id: rowContent
          anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
          anchors.leftMargin: Style.space(10); anchors.rightMargin: Style.space(4)
          spacing: Style.space(8)
          ColumnLayout {
            Layout.fillWidth: true
            spacing: Style.space(2)
            // fillWidth here too: a layout can only stretch through a child
            // that can, and on a word with no corrections the only other
            // one is hidden -- the buttons then took the slack between them.
            RowLayout {
              Layout.fillWidth: true
              spacing: Style.space(8)
              OmText {
                Layout.maximumWidth: rowContent.width - Style.space(140)
                wrapMode: Text.WrapAnywhere; size: "body"
                text: row.modelData.text
                color: row.modelData.enabled ? Color.foreground : Color.muted
              }
              OmText {
                visible: !row.modelData.enabled
                text: root.t("word.paused")
                color: tones.warn
              }
              Item { Layout.fillWidth: true }
            }
            OmText {
              visible: row.modelData.aliases.length > 0
              Layout.fillWidth: true; wrapMode: Text.WrapAnywhere
              // The list's own comma: 、 in Chinese and Japanese, ", " elsewhere.
              // It was 、 in every language, so an English row read
              // "Corrects: hyperland、hyper land".
              text: root.tf("word.corrects", row.modelData.aliases.slice(0, 2).join(root.t("word.sep")))
                    + (row.modelData.aliases.length > 2 ? "  +" + (row.modelData.aliases.length - 2) : "")
              color: Color.muted
            }
          }
          Button {
            text: root.t("word.edit"); focusable: true; enabled: !root.busy
            fontSize: Style.font.caption
            onClicked: root.openEditor(row.modelData)
          }
          Button {
            text: "⋯"; focusable: true; enabled: !root.busy
            fontSize: Style.font.caption
            Accessible.name: root.t("word.more")
            onClicked: root.openMenu(row.modelData, mapToItem(root, width - Style.space(190), height))
          }
        }
      }
    }
    Loader {
      visible: root.legacy; active: root.legacy
      Layout.fillWidth: true; Layout.fillHeight: true
      sourceComponent: LegacyDictionaryView {
        strings: root.strings; rules: root.rules; names: root.names
        seed: root.seed; budget: root.budget; seedChars: root.seedChars; dropped: root.dropped
        onCommand: function(c) { root.command(c) }
        onCommandArgs: function(a) { root.commandArgs(a) }
      }
    }
  }

  // ---- the editor -------------------------------------------------------
  //
  // The three options and the modes were QtQuick.Controls check boxes in the
  // platform's style: grey squares, and labels in a proportional font among
  // monospaced ones. They are chips, as every on/off choice in this console
  // is, lit when the thing happens.
  Rectangle {
    anchors.fill: parent
    visible: root.editing
    color: Color.popups.background
    Flickable {
      id: editorScroll
      anchors.fill: parent; anchors.margins: root.pad
      clip: true; contentHeight: editorColumn.implicitHeight
      Controls.ScrollBar.vertical: Controls.ScrollBar {}
      ColumnLayout {
        id: editorColumn
        width: Math.min(editorScroll.width - Style.space(12), Style.space(720))
        spacing: Style.space(10)
        OmText { text: root.t(root.original.id ? "word.edit" : "word.add"); size: "heading"; color: Color.foreground }
        OmText { Layout.topMargin: Style.space(6); text: root.t("word.spelling"); size: "body"; color: Color.muted }
        TextField {
          id: spelling
          objectName: "dictionarySpelling"
          Layout.fillWidth: true
          placeholderText: root.t("word.examples")
          maximumLength: 400
          font.family: Style.font.family
          onAccepted: root.save()
          onTextEdited: root.previewText = ""
        }
        OmText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.t("word.spaces"); color: Qt.darker(Color.muted, 1.1) }

        // -- misspellings --
        Button {
          objectName: "dictionaryWrong"
          Layout.topMargin: Style.space(6)
          text: (root.corrections ? "󰅀  " : "󰅂  ") + root.t("word.wrong")
          focusable: true
          onClicked: { root.corrections = !root.corrections; if (root.corrections && !aliases.count) aliases.append({value: ""}) }
        }
        ColumnLayout {
          visible: root.corrections
          Layout.fillWidth: true
          Layout.leftMargin: Style.space(18)
          spacing: Style.space(6)
          OmText { text: root.t("word.heard"); size: "body"; color: Color.muted }
          Repeater {
            model: aliases
            RowLayout {
              required property int index
              required property string value
              Layout.fillWidth: true
              spacing: Style.space(8)
              TextField {
                Layout.fillWidth: true; text: value
                font.family: Style.font.family
                onTextEdited: { aliases.setProperty(index, "value", text); root.previewText = "" }
                onAccepted: focus = false
              }
              Button { text: root.t("word.removealias"); fontSize: Style.font.caption; focusable: true; onClicked: aliases.remove(index) }
            }
          }
          Button { text: "+ " + root.t("word.another"); bordered: true; fontSize: Style.font.caption; focusable: true; onClicked: aliases.append({value: ""}) }
          OmText {
            Layout.fillWidth: true; wrapMode: Text.Wrap
            text: root.tf("word.replacehelp", spelling.text || "…"); color: Qt.darker(Color.muted, 1.1)
          }
        }

        // -- more options --
        Button {
          objectName: "dictionaryMore"
          text: (root.more ? "󰅀  " : "󰅂  ") + root.t("word.more")
          focusable: true
          onClicked: root.more = !root.more
        }
        ColumnLayout {
          visible: root.more
          Layout.fillWidth: true
          Layout.leftMargin: Style.space(18)
          spacing: Style.space(6)
          OmChip {
            objectName: "dictionaryHint"
            label: root.t("word.hint"); on: root.hintOn
            onClicked: root.hintOn = !root.hintOn
          }
          OmText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.t("word.hinthelp"); color: Qt.darker(Color.muted, 1.1) }
          OmChip {
            Layout.topMargin: Style.space(4)
            visible: spelling.text.toUpperCase() !== spelling.text.toLowerCase()
            label: root.t("word.case"); on: root.caseOn
            onClicked: { root.caseOn = !root.caseOn; root.previewText = "" }
          }
          OmChip {
            Layout.topMargin: Style.space(4)
            label: root.t("word.sound"); on: root.soundOn
            onClicked: { root.soundOn = !root.soundOn; root.previewText = "" }
          }
          OmText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.t("word.soundhelp"); color: Qt.darker(Color.muted, 1.1) }

          OmText { Layout.topMargin: Style.space(8); text: root.t("word.scope"); size: "body"; color: Color.muted }
          Flow {
            Layout.fillWidth: true; spacing: Style.space(6)
            OmChip {
              label: root.t("word.allmodes"); on: root.selectedModes.length === 0
              onClicked: root.selectedModes = on ? [root.payload.active_mode || "default"] : []
            }
            Repeater {
              model: root.payload.modes || []
              OmChip {
                required property string modelData
                label: modelData
                on: root.selectedModes.indexOf(modelData) >= 0
                onClicked: {
                  var next = root.selectedModes.filter(function(m) { return m !== modelData })
                  if (!on) next.push(modelData)
                  root.selectedModes = next
                }
              }
            }
          }

          OmText { Layout.topMargin: Style.space(8); text: root.t("word.previewhelp"); Layout.fillWidth: true; wrapMode: Text.Wrap; color: Qt.darker(Color.muted, 1.1) }
          Controls.TextArea {
            id: sample
            onTextChanged: root.previewText = ""
            objectName: "dictionarySample"
            Layout.fillWidth: true; Layout.minimumHeight: Style.space(75)
            placeholderText: root.t("word.sample"); wrapMode: TextEdit.Wrap
            font.family: Style.font.family; font.pixelSize: Style.font.caption
            color: Color.foreground; placeholderTextColor: Color.muted; selectByMouse: true
            background: Rectangle {
              color: Qt.darker(Color.popups.background, 1.06)
              border.width: 1
              border.color: sample.activeFocus ? Color.accent
                            : Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.22)
              radius: Style.cornerRadius
            }
          }
          Button {
            text: root.t("word.preview"); bordered: true; fontSize: Style.font.caption; focusable: true
            enabled: !root.busy && sample.text.trim() !== "" && spelling.text.trim() !== ""
            onClicked: root.send("preview", {entry: root.draft(), text: sample.text,
              mode: root.selectedModes.length ? root.selectedModes[0] : root.payload.active_mode})
          }
          OmText { visible: root.previewText !== ""; Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.previewText; size: "body"; color: Color.foreground }
        }
        OmText {
          visible: root.caseOn && /^[A-Z]{1,3}$/.test(spelling.text.trim())
          Layout.fillWidth: true; wrapMode: Text.Wrap
          text: root.tf("word.casewarning", spelling.text.toLowerCase() + " → " + spelling.text)
          color: tones.warn
        }
        OmText { visible: root.error !== ""; Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.error; color: Color.urgent }
        OmText { visible: root.error !== "" && root.detail !== ""; Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.detail; color: Color.muted }
        Button { visible: root.error !== ""; text: root.t("word.refresh"); bordered: true; fontSize: Style.font.caption; focusable: true; enabled: !root.busy; onClicked: root.refresh() }
        RowLayout {
          Layout.topMargin: Style.space(8)
          visible: !root.discardPrompt
          spacing: Style.space(8)
          Button { objectName: "dictionarySave"; text: root.t("word.save"); bordered: true; fontSize: Style.font.caption; focusable: true; enabled: !root.busy && spelling.text.trim() !== ""; onClicked: root.save() }
          Button { text: root.t("word.cancel"); fontSize: Style.font.caption; focusable: true; enabled: !root.busy; onClicked: root.closeEditor() }
        }
        OmText { visible: root.discardPrompt; Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.t("word.discardhelp"); size: "body"; color: Color.foreground }
        RowLayout {
          visible: root.discardPrompt
          spacing: Style.space(8)
          Button { text: root.t("word.keepediting"); bordered: true; fontSize: Style.font.caption; focusable: true; onClicked: root.discardPrompt = false }
          Button { text: root.t("word.discard"); foreground: Color.urgent; fontSize: Style.font.caption; focusable: true; onClicked: { root.editing = false; root.discardPrompt = false } }
        }
      }
    }
  }

  // ---- the row menu itself ------------------------------------------------
  MouseArea {
    anchors.fill: parent
    z: 50
    visible: root.menuEntry !== null
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    onClicked: root.menuEntry = null

    Rectangle {
      x: Math.max(Style.space(4), Math.min(root.menuX, parent.width - width - Style.space(4)))
      y: Math.max(Style.space(4), Math.min(root.menuY, parent.height - height - Style.space(4)))
      width: Style.space(220)
      height: menuRows.implicitHeight + Style.space(10)
      color: Color.popups.background
      radius: Style.cornerRadius
      border.width: 1
      border.color: Color.popups.border
      // Swallow clicks so a miss between two rows does not dismiss.
      MouseArea { anchors.fill: parent }
      ColumnLayout {
        id: menuRows
        anchors.fill: parent
        anchors.margins: Style.space(5)
        spacing: 0
        Repeater {
          model: root.menuEntry
                 ? [{ key: "toggle", label: root.t(root.menuEntry.enabled ? "word.pause" : "word.resume") },
                    { key: "delete", label: root.t("word.delete"), danger: true }]
                 : []
          Rectangle {
            readonly property bool danger: modelData.danger === true
            Layout.fillWidth: true
            implicitHeight: menuLabel.implicitHeight + Style.space(14)
            radius: Style.cornerRadius
            color: menuHover.containsMouse
                   ? (danger ? Qt.rgba(Color.urgent.r, Color.urgent.g, Color.urgent.b, 0.18)
                             : Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.08))
                   : "transparent"
            Rectangle {
              visible: parent.danger && index > 0
              width: parent.width - Style.space(12)
              height: 1
              anchors.top: parent.top
              anchors.horizontalCenter: parent.horizontalCenter
              color: Qt.rgba(Color.muted.r, Color.muted.g, Color.muted.b, 0.35)
            }
            OmText {
              id: menuLabel
              anchors.left: parent.left; anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              anchors.leftMargin: Style.space(12); anchors.rightMargin: Style.space(12)
              elide: Text.ElideRight
              text: modelData.label
              size: "body"
              color: parent.danger ? Color.urgent : Color.foreground
            }
            MouseArea {
              id: menuHover
              anchors.fill: parent
              hoverEnabled: true
              cursorShape: Qt.PointingHandCursor
              onClicked: root.fireMenu(modelData.key)
            }
          }
        }
      }
    }
  }
}
