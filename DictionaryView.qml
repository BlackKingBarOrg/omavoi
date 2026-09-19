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
    hints.checked = original.recognition_hint !== false
    casing.checked = original.normalize_case !== false
    sound.checked = !!(original.phonetic && original.phonetic.enabled)
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
      enabled: original.enabled !== false, recognition_hint: hints.checked,
      normalize_case: casing.checked,
      phonetic: {enabled: sound.checked, method: original.phonetic ? original.phonetic.method : "auto"},
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
  Keys.onEscapePressed: function(event) { if (editing) { closeEditor(); event.accepted = true } }

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

  ColumnLayout {
    anchors.fill: parent
    anchors.margins: root.pad
    spacing: Style.space(12)
    visible: !root.editing
    RowLayout {
      Layout.fillWidth: true
      OmText { text: root.t("nav.dictionary"); size: "title"; color: Color.foreground }
      Item { Layout.fillWidth: true }
      Button {
        text: root.t("word.add"); bordered: true; focusable: true
        visible: !root.legacy
        enabled: root.loaded && !root.busy
        onClicked: root.openEditor(null)
      }
    }
    OmText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.t("word.intro"); color: Color.muted }
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
      OmText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.note; color: Color.foreground }
      Button { visible: root.pendingActivation; text: root.t("word.retry"); focusable: true; onClicked: root.send("reload", {}) }
      Button { visible: !!root.undoEntry; text: root.t("word.undo"); focusable: true; onClicked: root.send("restore", {entry: root.undoEntry}) }
    }
    OmText {
      visible: (root.payload.dropped || []).length > 0 && !root.legacy
      Layout.fillWidth: true; wrapMode: Text.Wrap
      text: root.t("word.capacity") + " " + (root.payload.dropped || []).join("、")
      color: Color.muted
    }
    RowLayout {
      visible: root.error !== ""
      Layout.fillWidth: true
      OmText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.error; color: Color.urgent }
      Button { text: root.t("word.retry"); focusable: true; onClicked: root.refresh() }
    }
    TextField {
      id: search
      objectName: "dictionarySearch"
      visible: !root.legacy
      Layout.fillWidth: true
      placeholderText: root.t("word.search")
    }
    OmText {
      visible: !root.legacy && root.loaded && root.filtered.length === 0
      Layout.fillWidth: true; wrapMode: Text.Wrap
      text: root.t(search.text ? "word.noresults" : "word.empty"); color: Color.muted
    }
    OmText { visible: !root.loaded && !root.legacy && !root.error; text: root.t("word.loading"); color: Color.muted }
    ListView {
      id: entries
      visible: !root.legacy
      Layout.fillWidth: true; Layout.fillHeight: true
      clip: true
      model: root.filtered
      spacing: Style.space(8)
      Controls.ScrollBar.vertical: Controls.ScrollBar {}
      delegate: Rectangle {
        id: row
        required property var modelData
        width: entries.width
        height: rowContent.implicitHeight + Style.space(20)
        color: Qt.darker(Color.popups.background, 1.12)
        border.width: 1
        border.color: Qt.darker(Color.muted, 2.2)
        radius: Style.cornerRadius
        RowLayout {
          id: rowContent
          anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
          anchors.margins: Style.space(10)
          spacing: Style.space(8)
          ColumnLayout {
            Layout.fillWidth: true
            OmText {
              Layout.fillWidth: true; wrapMode: Text.WrapAnywhere; size: "body"
              text: row.modelData.text + (row.modelData.enabled ? "" : " · " + root.t("word.paused"))
              color: row.modelData.enabled ? Color.foreground : Color.muted
            }
            OmText {
              visible: row.modelData.aliases.length > 0
              Layout.fillWidth: true; wrapMode: Text.WrapAnywhere
              text: root.t("word.from") + " " + row.modelData.aliases.slice(0, 2).join("、")
                    + (row.modelData.aliases.length > 2 ? "  +" + (row.modelData.aliases.length - 2) : "")
              color: Color.muted
            }
          }
          Button { text: root.t("word.edit"); bordered: true; focusable: true; enabled: !root.busy; onClicked: root.openEditor(row.modelData) }
          Button {
            text: "⋯"; focusable: true; bordered: true; enabled: !root.busy
            Accessible.name: root.t("word.more")
            onClicked: rowMenu.open()
            Controls.Menu {
              id: rowMenu
              Controls.MenuItem { text: root.t(row.modelData.enabled ? "word.pause" : "word.resume"); onTriggered: root.toggleEntry(row.modelData) }
              Controls.MenuItem { text: root.t("word.delete"); onTriggered: root.send("remove", {id: row.modelData.id}) }
            }
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
        spacing: Style.space(12)
        OmText { text: root.t(root.original.id ? "word.edit" : "word.add"); size: "title"; color: Color.foreground }
        OmText { text: root.t("word.spelling"); color: Color.foreground }
        TextField {
          id: spelling
          objectName: "dictionarySpelling"
          Layout.fillWidth: true
          placeholderText: root.t("word.examples")
          maximumLength: 400
          onAccepted: root.save()
          onTextEdited: root.previewText = ""
        }
        OmText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.t("word.spaces"); color: Color.muted }
        Button {
          text: (root.corrections ? "▾ " : "▸ ") + root.t("word.wrong")
          focusable: true
          onClicked: { root.corrections = !root.corrections; if (root.corrections && !aliases.count) aliases.append({value: ""}) }
        }
        ColumnLayout {
          visible: root.corrections
          Layout.fillWidth: true
          OmText { text: root.t("word.heard"); color: Color.foreground }
          Repeater {
            model: aliases
            RowLayout {
              required property int index
              required property string value
              Layout.fillWidth: true
              TextField {
                Layout.fillWidth: true; text: value
                onTextEdited: { aliases.setProperty(index, "value", text); root.previewText = "" }
                onAccepted: focus = false
              }
              Button { text: root.t("word.removealias"); focusable: true; onClicked: aliases.remove(index) }
            }
          }
          Button { text: root.t("word.another"); focusable: true; onClicked: aliases.append({value: ""}) }
          OmText {
            Layout.fillWidth: true; wrapMode: Text.Wrap
            text: root.tf("word.replacehelp", spelling.text || "…"); color: Color.muted
          }
        }
        Button { text: (root.more ? "▾ " : "▸ ") + root.t("word.more"); focusable: true; onClicked: root.more = !root.more }
        ColumnLayout {
          visible: root.more
          Layout.fillWidth: true
          Controls.CheckBox { id: hints; text: root.t("word.hint"); palette.windowText: Color.foreground }
          OmText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.t("word.hinthelp"); color: Color.muted }
          Controls.CheckBox { id: casing; visible: spelling.text.toUpperCase() !== spelling.text.toLowerCase(); onToggled: root.previewText = ""; text: root.t("word.case"); palette.windowText: Color.foreground }
          Controls.CheckBox { id: sound; onToggled: root.previewText = ""; text: root.t("word.sound"); palette.windowText: Color.foreground }
          OmText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.t("word.soundhelp"); color: Color.muted }
          OmText { text: root.t("word.scope"); color: Color.foreground }
          Controls.CheckBox {
            text: root.t("word.allmodes"); checked: root.selectedModes.length === 0; palette.windowText: Color.foreground
            onClicked: root.selectedModes = checked ? [] : [root.payload.active_mode || "default"]
          }
          Flow {
            Layout.fillWidth: true; spacing: Style.space(6)
            Repeater {
              model: root.payload.modes || []
              Controls.CheckBox {
                required property string modelData
                text: modelData; palette.windowText: Color.foreground
                checked: root.selectedModes.indexOf(modelData) >= 0
                onClicked: {
                  var next = root.selectedModes.filter(function(m) { return m !== modelData })
                  if (checked) next.push(modelData)
                  root.selectedModes = next
                }
              }
            }
          }
          OmText { text: root.t("word.previewhelp"); Layout.fillWidth: true; wrapMode: Text.Wrap; color: Color.muted }
          Controls.TextArea {
            id: sample
            onTextChanged: root.previewText = ""
            objectName: "dictionarySample"
            Layout.fillWidth: true; Layout.minimumHeight: Style.space(75)
            placeholderText: root.t("word.sample"); wrapMode: TextEdit.Wrap
            color: Color.foreground; placeholderTextColor: Color.muted; selectByMouse: true
            background: Rectangle { color: "transparent"; border.width: 1; border.color: Color.muted }
          }
          Button {
            text: root.t("word.preview"); bordered: true; focusable: true
            enabled: !root.busy && sample.text.trim() !== "" && spelling.text.trim() !== ""
            onClicked: root.send("preview", {entry: root.draft(), text: sample.text,
              mode: root.selectedModes.length ? root.selectedModes[0] : root.payload.active_mode})
          }
          OmText { visible: root.previewText !== ""; Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.previewText; color: Color.foreground }
        }
        OmText {
          visible: casing.checked && /^[A-Z]{1,3}$/.test(spelling.text.trim())
          Layout.fillWidth: true; wrapMode: Text.Wrap
          text: root.tf("word.casewarning", spelling.text.toLowerCase() + " → " + spelling.text)
          color: Color.muted
        }
        OmText { visible: root.error !== ""; Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.error; color: Color.urgent }
        OmText { visible: root.error !== "" && root.detail !== ""; Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.detail; color: Color.muted }
        Button { visible: root.error !== ""; text: root.t("word.refresh"); focusable: true; enabled: !root.busy; onClicked: root.refresh() }
        RowLayout {
          visible: !root.discardPrompt
          Button { text: root.t("word.cancel"); bordered: true; focusable: true; enabled: !root.busy; onClicked: root.closeEditor() }
          Button { text: root.t("word.save"); bordered: true; focusable: true; enabled: !root.busy && spelling.text.trim() !== ""; onClicked: root.save() }
        }
        OmText { visible: root.discardPrompt; Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.t("word.discardhelp"); color: Color.foreground }
        RowLayout {
          visible: root.discardPrompt
          Button { text: root.t("word.keepediting"); bordered: true; focusable: true; onClicked: root.discardPrompt = false }
          Button { text: root.t("word.discard"); bordered: true; focusable: true; onClicked: { root.editing = false; root.discardPrompt = false } }
        }
      }
    }
  }
}
