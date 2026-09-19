import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Io
import qs.Commons
import qs.Ui

// A URL, a key and a model id — for either family's remote endpoint.
//
// Everything else that used to be on screen here — key_env, key_name,
// timeout, temperature — is machinery, and putting it up made a mechanism
// look like a decision. It lives in the config file for anyone who needs it.
//
// Written once because the speech side had none of this at all: the console
// offered a "remote API" engine card for speech and there was nowhere to put
// the URL, so the engine could be selected and never configured. Building a
// second copy of the LLM panel is how the two would have drifted the way the
// rows and the cards did.
//
// Three fields, and only three. The speech backend does ship provider
// presets, and a row of them was here for one revision — but a menu of
// vendor names is a list of things to read about, not something to fill in,
// and it made four controls out of a job that has three. The presets still
// work from the config file, and the placeholders show whichever values one
// is currently supplying, so a blank field never hides a surprise.
ColumnLayout {
  id: fields

  property var strings: null
  // What `omavoi config set` writes under: "llm.api" or "speech.api".
  property string prefix: ""
  // What `omavoi secrets set` stores the key as.
  property string secretName: ""
  // What answers "does this endpoint work", as argv.
  property var checkArgv: []

  property string baseUrl: ""
  property string model: ""
  property bool hasKey: false
  // "env", "file" or "" — which of the two the daemon will actually read.
  property string keySource: ""
  property string keyEnv: ""
  // The value that applies when the field is left empty, shown as the
  // placeholder so a preset is visible rather than magic.
  property string defaultBaseUrl: ""
  property string defaultModel: ""

  signal command(string cmd)
  // Anything carrying typed text goes as argv. A base_url or a model id is
  // whatever someone pasted, and JSON.stringify is JSON quoting, not shell
  // quoting: "$(…)" and backticks still run inside double quotes.
  signal commandArgs(var argv)

  function t(k) { return fields.strings ? fields.strings.t(k) : k }
  function tf(k, a) { return fields.strings ? fields.strings.tf(k, a) : k }

  spacing: Style.space(5)

  property string keyNote: ""
  property string checkNote: ""
  property bool checkOk: false
  property var checkModels: []

  // The key goes over stdin, never in a command line: a value in argv is
  // readable from /proc by every process running as this user for as long as
  // the command lives.
  Process {
    id: keyWriter
    command: ["omavoi", "secrets", "set", fields.secretName]
    stdinEnabled: true
    property string pending: ""
    function send(value) {
      keyWriter.pending = value
      fields.keyNote = ""
      keyWriter.running = true
    }
    onStarted: {
      // Written once the pipe exists, then closed so the reader sees EOF.
      keyWriter.write(keyWriter.pending)
      keyWriter.pending = ""
      keyWriter.stdinEnabled = false
    }
    onExited: function (code, status) {
      fields.keyNote = code === 0 ? fields.t("models.f.key.saved")
                                  : fields.t("models.f.key.failed")
      keyField.text = ""
      fields.command("omavoi config show --json")
    }
  }

  Process {
    id: checker
    command: fields.checkArgv
    stdout: StdioCollector {
      onStreamFinished: {
        var r = ({})
        try { r = JSON.parse(text) } catch (e) { r = ({ ok: false, error: text }) }
        fields.checkOk = r.ok === true
        fields.checkModels = r.ok === true ? (r.models || []) : []
        // tf, not t: the string carries a %1 for the count, and plain t left
        // the placeholder on screen with the number stuck on after it.
        fields.checkNote = r.ok === true
          ? fields.tf("models.f.testok", (r.models || []).length)
          : String(r.error || fields.t("models.f.testfail"))
      }
    }
  }

  // -- url and model --------------------------------------------------------
  Repeater {
    model: [
      { key: "url", label: fields.t("models.f.url") },
      { key: "model", label: fields.t("models.f.model") }
    ]
    RowLayout {
      readonly property var f: modelData
      readonly property string now: f.key === "url" ? fields.baseUrl : fields.model
      Layout.fillWidth: true
      spacing: Style.space(9)
      OmText {
        Layout.preferredWidth: Style.space(52)
        text: f.label
        color: Color.muted
      }
      TextField {
        Layout.fillWidth: true
        Layout.maximumWidth: Style.space(320)
        text: now
        placeholderText: f.key === "url" ? fields.defaultBaseUrl
                                         : fields.defaultModel
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        onEditingFinished: {
          if (text === now) return
          fields.commandArgs(
            ["omavoi", "config", "set",
             fields.prefix + "." + (f.key === "url" ? "base_url" : "model"),
             String(text)])
        }
      }
    }
  }

  // -- the key --------------------------------------------------------------
  RowLayout {
    Layout.fillWidth: true
    spacing: Style.space(9)
    OmText {
      Layout.preferredWidth: Style.space(52)
      text: fields.t("models.f.key")
      color: Color.muted
    }
    TextField {
      id: keyField
      Layout.fillWidth: true
      Layout.maximumWidth: Style.space(320)
      echoMode: TextInput.Password
      placeholderText: fields.t("models.f.key.place")
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      onAccepted: if (text !== "") keyWriter.send(text)
    }
    Button {
      enabled: keyField.text !== ""
      text: fields.t("models.f.key.save")
      onClicked: keyWriter.send(keyField.text)
    }
    OmText {
      Layout.fillWidth: true
      elide: Text.ElideRight
      // Which one is in use, not merely that one exists. The environment
      // wins over the file, so a variable left over from a shell profile
      // silently beats the key just saved here — and "a key is stored" was
      // true in both cases.
      text: fields.keyNote !== "" ? fields.keyNote
            : fields.keySource === "env"
              ? fields.tf("models.f.key.fromenv", fields.keyEnv)
            : fields.keySource === "file" ? fields.t("models.f.key.fromfile")
            : (fields.hasKey ? fields.t("models.f.key.have") : "")
      wrapMode: Text.Wrap
      color: fields.keyNote !== "" ? Color.accent
             : fields.keySource === "env" ? "#e0af68" : Color.muted
    }
  }

  // -- does it answer? ------------------------------------------------------
  RowLayout {
    Layout.fillWidth: true
    Layout.topMargin: Style.space(3)
    spacing: Style.space(9)
    Button {
      enabled: (fields.checkArgv || []).length > 0
      text: fields.t("models.f.test")
      onClicked: { fields.checkNote = fields.t("models.f.testing"); checker.running = true }
    }
    OmText {
      Layout.fillWidth: true
      wrapMode: Text.Wrap
      text: fields.checkNote
      color: fields.checkOk ? "#9ece6a" : Color.urgent
    }
  }

  // Offered rather than typed: the check already returned the list, and a
  // model id from memory is the commonest thing to get wrong.
  Flow {
    Layout.fillWidth: true
    spacing: Style.space(6)
    visible: fields.checkModels.length > 0
    Repeater {
      model: fields.checkModels
      OmChip {
        readonly property string mid: modelData
        label: mid
        on: mid === fields.model
        onClicked: fields.commandArgs(
          ["omavoi", "config", "set", fields.prefix + ".model", String(mid)])
      }
    }
  }
}
