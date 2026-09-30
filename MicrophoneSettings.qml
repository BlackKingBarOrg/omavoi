import QtQuick
import QtQuick.Layouts
import Quickshell.Io
import qs.Commons
import qs.Ui

ColumnLayout {
  id: root
  property var strings: null
  property string target: ""
  property bool recordingBusy: false
  property var devices: []
  property string result: ""
  signal commandArgs(var argv)
  function t(key) { return strings ? strings.t(key) : key }
  spacing: Style.space(10)
  SectionTitle { title: root.t("mic.title"); note: root.t("mic.note") }
  Process {
    id: reader
    command: ["pw-dump"]
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          root.devices = JSON.parse(text).filter(function(n) {
            return n.type === "PipeWire:Interface:Node" && n.info && n.info.props
                   && n.info.props["media.class"] === "Audio/Source"
          }).map(function(n) {
            return { value: String(n.info.props["node.name"]),
                     label: String(n.info.props["node.description"] || n.info.props["node.nick"] || n.info.props["node.name"]) }
          })
        } catch (e) { root.devices = [] }
      }
    }
  }
  Component.onCompleted: reader.running = true
  Process {
    id: tester
    command: ["python3", decodeURIComponent(Qt.resolvedUrl("tools/microphone_test.py").toString().replace(/^file:\/\//, "")), "--target", root.target]
    stdout: StdioCollector {
      onStreamFinished: {
        try {
          var response = JSON.parse(text)
          root.result = root.t(response.ok ? (response.quiet ? "mic.quiet" : "mic.done") : "mic.failed")
        } catch (e) { root.result = root.t("mic.failed") }
      }
    }
  }
  RowLayout {
    Layout.fillWidth: true
    spacing: Style.space(10)
    Dropdown {
      objectName: "microphonePicker"
      Layout.fillWidth: true
      Layout.maximumWidth: Style.space(450)
      showLabel: false
      enabled: !tester.running && !root.recordingBusy
      Binding on value { value: root.target }
      options: {
        var out = [{ value: "", label: root.t("mic.default") }].concat(root.devices)
        if (root.target && !out.some(function(d) { return d.value === root.target }))
          out.push({ value: root.target, label: root.target + " · " + root.t("mic.unavailable") })
        return out
      }
      onChanged: function(v) { root.commandArgs(["omavoi", "config", "set", "audio.target", v]) }
    }
    Button {
      text: root.t("mic.refresh"); bordered: true; fontSize: Style.font.caption
      enabled: !reader.running
      onClicked: reader.running = true
    }
    Item { Layout.fillWidth: true }
  }
  RowLayout {
    Layout.fillWidth: true
    spacing: Style.space(10)
    Button {
      objectName: "testMicrophone"
      text: root.t("mic.test"); bordered: true; fontSize: Style.font.caption
      enabled: !tester.running && !root.recordingBusy
      onClicked: { root.result = ""; tester.running = true }
    }
    OmText {
      Layout.fillWidth: true; wrapMode: Text.Wrap
      text: tester.running ? root.t("mic.testing") : root.result || root.t("mic.testnote")
      color: Color.muted
    }
  }
}
