import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Io
import qs.Commons
import qs.Ui

// A complete form: nothing is written on focus loss. The key uses stdin;
// the remaining fields form one queued action, with activation last.
ColumnLayout {
  id: fields
  property var strings: null
  property string prefix: ""
  property string secretName: ""
  property var checkArgv: []
  property string baseUrl: ""
  property string model: ""
  property bool hasKey: false
  property string keySource: ""
  property string keyEnv: ""
  property string defaultBaseUrl: ""
  property string defaultModel: ""
  property bool activateOnSave: false
  property bool saving: false
  property string draftUrl: ""
  property string draftModel: ""
  property string baselineUrl: ""
  property string baselineModel: ""
  property bool initialized: false
  readonly property bool dirty: draftUrl !== baselineUrl || draftModel !== baselineModel || keyField.text !== ""
  readonly property bool needsSave: dirty || activateOnSave || draftUrl.trim() !== baseUrl || draftModel.trim() !== model
  readonly property bool busy: saving || keyWriter.running
  property string keyNote: ""
  property string checkNote: ""
  property bool checkOk: false
  property var checkModels: []
  signal command(string cmd)
  signal commandArgs(var argv)
  signal commandBatch(var commands)
  function t(k) { return strings ? strings.t(k) : k }
  function tf(k, a) { return strings ? strings.tf(k, a) : k }
  function sync() {
    var url = baseUrl || defaultBaseUrl
    var chosen = model || defaultModel
    if (!initialized || draftUrl === baselineUrl) draftUrl = url
    if (!initialized || draftModel === baselineModel) draftModel = chosen
    baselineUrl = url
    baselineModel = chosen
    initialized = true
  }
  Component.onCompleted: sync()
  onBaseUrlChanged: syncSoon.restart()
  onModelChanged: syncSoon.restart()
  onDefaultBaseUrlChanged: syncSoon.restart()
  onDefaultModelChanged: syncSoon.restart()
  Timer { id: syncSoon; interval: 0; onTriggered: fields.sync() }
  function commitFields() {
    var commands = [
      ["omavoi", "config", "set", prefix + ".base_url", draftUrl.trim()],
      ["omavoi", "config", "set", prefix + ".model", draftModel.trim()]
    ]
    if (activateOnSave) commands.push(["omavoi", "config", "set", "speech.backend", "api"])
    commandBatch(commands)
  }
  function save() {
    if (busy || checker.running) return
    if (!/^https?:\/\/[^\s/]+/.test(draftUrl.trim()) || !draftModel.trim()) {
      checkOk = false; checkNote = t("api.invalid"); return
    }
    checkNote = ""
    if (keyField.text !== "") keyWriter.send(keyField.text)
    else commitFields()
  }
  spacing: Style.space(8)
  Tones { id: tones }
  Process {
    id: keyWriter
    command: ["omavoi", "secrets", "set", fields.secretName]
    stdinEnabled: true
    property string pending: ""
    function send(value) {
      pending = value
      stdinEnabled = true
      fields.keyNote = ""
      running = true
    }
    onStarted: { write(pending); pending = ""; stdinEnabled = false }
    onExited: function(code, status) {
      fields.keyNote = fields.t(code === 0 ? "models.f.key.saved" : "models.f.key.failed")
      if (code === 0) { keyField.text = ""; fields.commitFields() }
    }
  }
  Process {
    id: checker
    command: fields.checkArgv
    stdout: StdioCollector {
      onStreamFinished: {
        var response = ({})
        try { response = JSON.parse(text) } catch(e) {}
        fields.checkOk = response.ok === true
        fields.checkModels = fields.checkOk ? response.models || [] : []
        fields.checkNote = fields.checkOk
          ? fields.tf("models.f.testok", fields.checkModels.length)
          : fields.t("models.f.testfail") + (response.error ? "\n" + response.error : "")
      }
    }
  }
  RowLayout {
    Layout.fillWidth: true
    OmText { Layout.preferredWidth: Style.space(100); text: fields.t("models.f.url"); color: Color.muted }
    TextField {
      objectName: "endpointUrl"
      Layout.fillWidth: true; Layout.maximumWidth: Style.space(430)
      text: fields.draftUrl
      enabled: !fields.busy && !checker.running
      font.family: Style.font.family; font.pixelSize: Style.font.caption
      onTextEdited: { fields.draftUrl = text; fields.checkNote = ""; fields.checkModels = [] }
      onAccepted: fields.save()
    }
  }
  RowLayout {
    Layout.fillWidth: true
    OmText { Layout.preferredWidth: Style.space(100); text: fields.t("models.f.model"); color: Color.muted }
    TextField {
      objectName: "endpointModel"
      Layout.fillWidth: true; Layout.maximumWidth: Style.space(430)
      text: fields.draftModel
      enabled: !fields.busy && !checker.running
      font.family: Style.font.family; font.pixelSize: Style.font.caption
      onTextEdited: fields.draftModel = text
      onAccepted: fields.save()
    }
  }
  RowLayout {
    Layout.fillWidth: true
    OmText { Layout.preferredWidth: Style.space(100); text: fields.t("models.f.key"); color: Color.muted }
    TextField {
      id: keyField
      objectName: "endpointKey"
      Layout.fillWidth: true; Layout.maximumWidth: Style.space(430)
      enabled: !fields.busy && !checker.running
      echoMode: TextInput.Password
      placeholderText: fields.t("models.f.key.place")
      font.family: Style.font.family; font.pixelSize: Style.font.caption
      onAccepted: fields.save()
    }
  }
  OmText {
    Layout.fillWidth: true; wrapMode: Text.Wrap
    text: fields.keyNote || (fields.keySource === "env" ? fields.tf("models.f.key.fromenv", fields.keyEnv)
          : fields.keySource === "file" ? fields.t("models.f.key.fromfile")
          : fields.hasKey ? fields.t("models.f.key.have") : "")
    visible: text !== ""
    color: fields.keySource === "env" ? tones.warn : Color.muted
  }
  Flow {
    Layout.fillWidth: true; spacing: Style.space(8)
    Button {
      objectName: "saveEndpoint"
      text: fields.activateOnSave ? fields.t("api.enable") : fields.t("models.f.key.save")
      enabled: !fields.busy && !checker.running && fields.needsSave
      bordered: true; fontSize: Style.font.caption
      onClicked: fields.save()
    }
    Button {
      visible: fields.dirty
      text: fields.t("edit.revert"); bordered: true; fontSize: Style.font.caption
      enabled: !fields.busy
      onClicked: { fields.draftUrl = fields.baselineUrl; fields.draftModel = fields.baselineModel; keyField.text = ""; fields.checkNote = "" }
    }
    Button {
      objectName: "testEndpoint"
      text: fields.t("models.f.test"); bordered: true; fontSize: Style.font.caption
      enabled: !fields.busy && !checker.running && !fields.needsSave && fields.checkArgv.length > 0
      onClicked: { fields.checkNote = fields.t("models.f.testing"); checker.running = true }
    }
  }
  OmText {
    Layout.fillWidth: true; wrapMode: Text.Wrap
    text: fields.checkNote || fields.t("api.savenote")
    color: fields.checkNote !== "" && !fields.checkOk && !checker.running ? Color.urgent : Color.muted
  }
  SearchableDropdown {
    objectName: "endpointModels"
    visible: fields.checkModels.length > 0
    Layout.fillWidth: true; Layout.maximumWidth: Style.space(540)
    showLabel: false
    Binding on value { value: fields.draftModel }
    options: fields.checkModels.map(function(id) { return { value: id, label: id } })
    placeholderText: fields.t("api.search")
    triggerLabel: fields.t("models.f.model")
    emptyText: fields.t("modes.langempty")
    onChanged: function(value) { fields.draftModel = value }
  }
}
