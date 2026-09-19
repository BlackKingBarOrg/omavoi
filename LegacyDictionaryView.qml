import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Io
import qs.Commons
import qs.Ui

// Two kinds of entry, because they solve different problems. A rule needs you
// to know what the model got wrong. A name does not — and for CJK you never
// will, since the manglings are an open set of homophones — so a name is
// written once, correctly, and matched by sound.
Flickable {
  id: root
  property var rules: []
  property var names: []
  property string seed: ""
  property int budget: 224
  // `budget` was here from the start with nothing passing a value in and
  // nothing reading it. The cap is real — seed_text stops at it — so names
  // past it were listed on this page as seeded and handed to nothing.
  property int seedChars: 0
  property var dropped: []
  property int pad: Style.space(22)
  property string sub: "rules"
  property var strings: null

  signal command(string cmd)
  // Anything carrying user text, which a dictionary key always does.
  signal commandArgs(var argv)

  // The dry run, read rather than discarded.
  //
  // It used to go out through `command`, which runs the thing and throws its
  // stdout away — so the one button on this page whose entire output *is* the
  // answer looked inert, while the blurb above it says matching stays off
  // until a dry run has been looked at. There was nowhere to look. Its own
  // Process, like the endpoint check in EndpointFields, because what comes
  // back has to reach the screen.
  property string dryRun: ""
  property bool dryRunning: false
  property bool dryRunDone: false
  Process {
    id: dryRunner
    command: ["omavoi", "names", "dryrun"]
    onRunningChanged: root.dryRunning = dryRunner.running
    stdout: StdioCollector {
      onStreamFinished: {
        root.dryRun = String(text).trim()
        root.dryRunDone = true
      }
    }
  }

  // `strings` is null for the instant between creation and the Loader setting
  // it, so the key stands in until then rather than a blank.
  function t(k) { return root.strings ? root.strings.t(k) : k }
  function tf(k, a) { return root.strings ? root.strings.tf(k, a) : k }

  contentHeight: col.implicitHeight + pad * 2
  clip: true

  ColumnLayout {
    id: col
    x: root.pad
    y: root.pad
    width: root.width - root.pad * 2
    spacing: Style.space(12)

    ButtonGroup {
      options: [{ value: "rules", label: root.t("dict.rules") },
                { value: "names", label: root.t("dict.names") }]
      value: root.sub
      onChanged: function (v) { root.sub = v }
    }

    // ---- rules -----------------------------------------------------
    OmText {
      visible: root.sub === "rules"
      Layout.fillWidth: true
      wrapMode: Text.Wrap
      text: root.t("dict.blurb")
      color: Color.muted
    }
    Repeater {
      model: root.sub === "rules" ? root.rules : []
      RowLayout {
        readonly property var r: modelData
        Layout.fillWidth: true
        spacing: Style.space(10)
        OmText {
          Layout.preferredWidth: Style.space(180)
          text: r.heard
          size: "body"
          color: Color.foreground
        }
        OmText {
          text: "→"
          color: Color.muted
        }
        OmText {
          Layout.preferredWidth: Style.space(180)
          text: r.meant
          size: "body"
          color: Color.foreground
        }
        OmText {
          Layout.fillWidth: true
          visible: r.shadowed_by !== ""
          text: root.t("dict.shadowed") + "\"" + r.shadowed_by + "\""
          color: "#e0af68"
        }
        Item { Layout.fillWidth: r.shadowed_by === "" }
        Button {
          text: root.t("dict.remove")
          onClicked: root.commandArgs(["omavoi", "dict", "rm", String(r.heard)])
        }
      }
    }

    // ---- names -----------------------------------------------------
    OmText {
      visible: root.sub === "names"
      Layout.fillWidth: true
      wrapMode: Text.Wrap
      text: root.t("dict.namesblurb")
      color: Color.muted
    }
    Repeater {
      model: root.sub === "names" ? root.names : []
      RowLayout {
        readonly property var n: modelData
        Layout.fillWidth: true
        spacing: Style.space(10)
        OmText {
          Layout.preferredWidth: Style.space(150)
          text: n.name
          size: "body"
          color: Color.foreground
        }
        OmText {
          Layout.preferredWidth: Style.space(170)
          text: n.key
          color: Color.muted
        }
        OmText {
          Layout.preferredWidth: Style.space(80)
          text: n.match
          color: Color.muted
        }
        OmText {
          Layout.preferredWidth: Style.space(110)
          text: n.enabled ? root.t("dict.matching") : root.t("dict.seedonly")
          color: n.enabled ? "#9ece6a" : Color.muted
        }
        Item { Layout.fillWidth: true }
        Button {
          text: root.t("dict.remove")
          onClicked: root.commandArgs(["omavoi", "names", "rm", String(n.name)])
        }
      }
    }
    RowLayout {
      visible: root.sub === "names"
      Layout.topMargin: Style.space(8)
      spacing: Style.space(10)
      Button {
        text: root.t("dict.dryrun")
        enabled: !root.dryRunning
        onClicked: {
          root.dryRun = ""
          root.dryRunDone = false
          dryRunner.running = true
        }
      }
      Button {
        text: root.t("dict.enable")
        onClicked: root.command("omavoi names enable")
      }
      OmText {
        Layout.fillWidth: true
        elide: Text.ElideRight
        text: root.t("dict.prompt") + (root.seed || root.t("dict.none"))
        color: Color.muted
      }
      OmText {
        visible: (root.dropped || []).length > 0
        text: root.tf("dict.overbudget", (root.dropped || []).length)
        color: "#e0af68"
      }
    }

    // What it said. Bordered rather than loose text, because it is output
    // from a command and not another sentence of ours — and the page is a
    // Flickable, so a long report scrolls with everything else.
    Rectangle {
      visible: root.sub === "names"
               && (root.dryRunning || root.dryRunDone)
      Layout.fillWidth: true
      implicitHeight: dryCol.implicitHeight + Style.space(20)
      color: Qt.darker(Color.popups.background, 1.35)
      border.width: 1
      border.color: Qt.rgba(Color.foreground.r, Color.foreground.g,
                            Color.foreground.b, 0.25)
      radius: Style.cornerRadius

      ColumnLayout {
        id: dryCol
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Style.space(11)
        spacing: Style.space(6)

        RowLayout {
          Layout.fillWidth: true
          OmText {
            text: root.dryRunning ? root.t("dict.dryrun.running")
                                  : root.t("dict.dryrun")
            font.letterSpacing: 1
            color: Color.muted
          }
          Item { Layout.fillWidth: true }
          OmChip {
            visible: !root.dryRunning
            label: root.t("models.f.close")
            on: false
            onClicked: { root.dryRun = ""; root.dryRunDone = false }
          }
        }

        OmText {
          visible: root.dryRunDone
          Layout.fillWidth: true
          wrapMode: Text.Wrap
          text: root.dryRun !== "" ? root.dryRun : root.t("dict.dryrun.none")
          color: root.dryRun !== "" ? Color.foreground : Color.muted
        }
      }
    }

    // This page could list, remove, dry-run and enable — and not add. The
    // line that used to sit here told you to open a terminal and run
    // `omavoi dict add`, which is a page documenting its own hole.
    //
    // argv, not a command line: a dictionary key is user text with spaces in
    // it — "hyper land" is the whole point of the feature — and the rule in
    // Console.qml is that user text never goes through a shell.
    RowLayout {
      visible: root.sub === "rules"
      Layout.topMargin: Style.space(12)
      Layout.fillWidth: true
      spacing: Style.space(8)
      OmText { text: root.t("dict.heard"); color: Color.muted }
      TextField {
        id: heardField
        Layout.preferredWidth: Style.space(180)
        placeholderText: root.t("dict.heardph")
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        onAccepted: addRule.go()
      }
      OmText { text: root.t("dict.meant"); color: Color.muted }
      TextField {
        id: meantField
        Layout.preferredWidth: Style.space(180)
        placeholderText: root.t("dict.meantph")
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        onAccepted: addRule.go()
      }
      Button {
        id: addRule
        enabled: heardField.text.trim() !== "" && meantField.text.trim() !== ""
        text: root.t("dict.add")
        function go() {
          if (!enabled) return
          root.commandArgs(["omavoi", "dict", "add",
                            heardField.text.trim(), meantField.text.trim()])
          heardField.text = ""
          meantField.text = ""
        }
        onClicked: go()
      }
      Item { Layout.fillWidth: true }
    }

    RowLayout {
      visible: root.sub === "names"
      Layout.topMargin: Style.space(12)
      Layout.fillWidth: true
      spacing: Style.space(8)
      TextField {
        id: nameField
        Layout.fillWidth: true
        Layout.maximumWidth: Style.space(430)
        placeholderText: root.t("dict.nameph")
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        onAccepted: addNames.go()
      }
      Button {
        id: addNames
        enabled: nameField.text.trim() !== ""
        text: root.t("dict.add")
        function go() {
          if (!enabled) return
          // `names add` takes several and the placeholder says so, so the
          // field is split rather than sent as one improbable name.
          var parts = nameField.text.trim().split(/\s+/)
          if (!parts.length) return
          root.commandArgs(["omavoi", "names", "add"].concat(parts))
          nameField.text = ""
        }
        onClicked: go()
      }
      Item { Layout.fillWidth: true }
    }
  }
}
