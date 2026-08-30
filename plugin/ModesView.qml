import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import qs.Ui

// A mode is a chain of models, so it is edited as one: the speech step and
// what it is told, the deterministic rules, then zero or more LLM passes each
// with its own prompt, then how the text gets into the window.
//
// Everything here writes through the omavoi command, so the console and the
// terminal cannot drift apart — the config file is the single record.
Item {
  id: root
  property var payload: ({ modes: [], active: "", llm: [] })
  property string selected: ""
  readonly property int pad: Style.space(18)

  signal command(string cmd)
  signal commandArgs(var argv)

  readonly property var modes: payload.modes || []
  readonly property var llms: payload.llm || []
  readonly property string current: {
    for (var i = 0; i < modes.length; i++) if (modes[i].name === selected) return selected
    return payload.active || (modes.length ? modes[0].name : "")
  }
  readonly property var mode: {
    for (var i = 0; i < modes.length; i++) if (modes[i].name === current) return modes[i]
    return null
  }

  function chainOf(m) {
    var names = ["speech"]
    var steps = (m && m.steps) || []
    for (var i = 0; i < steps.length; i++) names.push(steps[i].llm)
    return names.join(" → ")
  }

  RowLayout {
    anchors.fill: parent
    spacing: 0

    // ===================== list =====================
    Rectangle {
      Layout.preferredWidth: Style.space(280)
      Layout.fillHeight: true
      color: Qt.darker(Color.popups.background, 1.05)

      ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ListView {
          Layout.fillWidth: true
          Layout.fillHeight: true
          clip: true
          model: root.modes
          delegate: Rectangle {
            readonly property var m: modelData
            width: ListView.view.width
            height: entry.implicitHeight + Style.space(18)
            color: m.name === root.current
                   ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.12)
                   : "transparent"

            Rectangle {
              width: 2; height: parent.height
              color: m.name === root.current ? Color.accent : "transparent"
            }

            ColumnLayout {
              id: entry
              anchors.left: parent.left
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              anchors.leftMargin: Style.space(13)
              anchors.rightMargin: Style.space(11)
              spacing: 2

              RowLayout {
                Layout.fillWidth: true
                Text {
                  text: m.name
                  font.family: Style.font.family
                  font.pixelSize: Style.font.body
                  color: Color.foreground
                }
                Item { Layout.fillWidth: true }
                Text {
                  visible: m.active === true
                  text: "here"
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                  color: Color.accent
                }
              }
              Text {
                Layout.fillWidth: true
                elide: Text.ElideRight
                text: root.chainOf(m)
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                color: (m.steps || []).length ? Color.accent : Color.muted
              }
              Text {
                Layout.fillWidth: true
                elide: Text.ElideRight
                text: (m.match || []).join(", ") || "fallback"
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                color: Qt.darker(Color.muted, 1.1)
              }
            }
            MouseArea {
              anchors.fill: parent
              cursorShape: Qt.PointingHandCursor
              onClicked: root.selected = m.name
            }
          }
        }

        // -- new mode --
        RowLayout {
          Layout.fillWidth: true
          Layout.margins: Style.space(11)
          spacing: Style.space(7)
          TextField {
            id: newName
            Layout.fillWidth: true
            placeholderText: "new mode name"
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            onAccepted: makeMode.click()
          }
          Button {
            id: makeMode
            text: "+"
            function click() {
              var name = newName.text.trim()
              if (!name) return
              // Copied from the current mode: a new mode that starts empty
              // has no rules and silently behaves unlike every other one.
              root.commandArgs(["omavoi", "mode", "new", name, root.current])
              root.selected = name
              newName.text = ""
            }
            onClicked: click()
          }
        }
      }
    }

    Rectangle {
      Layout.preferredWidth: 1
      Layout.fillHeight: true
      color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.18)
    }

    // ===================== detail =====================
    Flickable {
      Layout.fillWidth: true
      Layout.fillHeight: true
      clip: true
      contentHeight: detail.implicitHeight + root.pad * 2
      visible: root.mode !== null

      ColumnLayout {
        id: detail
        x: root.pad
        y: root.pad
        width: parent.width - root.pad * 2
        spacing: Style.space(14)

        // -- header --
        RowLayout {
          Layout.fillWidth: true
          spacing: Style.space(10)
          Text {
            text: root.current
            font.family: Style.font.family
            font.pixelSize: Style.font.heading
            color: Color.foreground
          }
          Text {
            visible: root.mode && root.mode.active === true
            text: "active in this window"
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            color: Color.accent
          }
          Item { Layout.fillWidth: true }
          Button {
            visible: root.current !== "default"
            text: "Delete mode"
            onClicked: root.commandArgs(["omavoi", "mode", "rm", root.current])
          }
        }

        // -- triggers --
        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(6)
          Text {
            text: "OPENS ON"
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            font.letterSpacing: 1
            color: Color.muted
          }
          Flow {
            Layout.fillWidth: true
            spacing: Style.space(6)
            Repeater {
              model: (root.mode && root.mode.match) || []
              OmChip {
                readonly property string token: modelData
                label: token + "  ×"
                on: true
                onClicked: root.commandArgs(["omavoi", "mode", "unmatch", root.current, token])
              }
            }
            Text {
              visible: !((root.mode && root.mode.match) || []).length
              text: "nothing — this mode is only reached by name"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              color: Color.muted
            }
          }
          RowLayout {
            Layout.fillWidth: true
            spacing: Style.space(7)
            TextField {
              id: newMatch
              Layout.preferredWidth: Style.space(280)
              placeholderText: "window class, e.g. thunderbird"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              onAccepted: addMatch.click()
            }
            Button {
              id: addMatch
              text: "Add"
              function click() {
                var t = newMatch.text.trim()
                if (!t) return
                root.commandArgs(["omavoi", "mode", "match", root.current, t])
                newMatch.text = ""
              }
              onClicked: click()
            }
            Text {
              Layout.fillWidth: true
              wrapMode: Text.Wrap
              text: "Matched against the Hyprland class and title. The longest match wins."
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              color: Qt.darker(Color.muted, 1.1)
            }
          }
        }

        Rectangle {
          Layout.fillWidth: true; Layout.preferredHeight: 1
          color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.14)
        }

        // -- 1 speech --
        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(7)
          RowLayout {
            spacing: Style.space(9)
            Text {
              text: "1  SPEECH"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              font.letterSpacing: 1
              color: Color.accent
            }
            Text {
              text: "what the model is told before it decodes"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              color: Color.muted
            }
          }
          RowLayout {
            Layout.fillWidth: true
            spacing: Style.space(9)
            Text {
              Layout.preferredWidth: Style.space(96)
              text: "language"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              color: Color.muted
            }
            TextField {
              Layout.preferredWidth: Style.space(120)
              text: (root.mode && root.mode.language) || ""
              placeholderText: "auto"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              onEditingFinished: if (root.mode && text !== (root.mode.language || ""))
                root.commandArgs(["omavoi", "mode", "set", root.current, "language", text])
            }
            Text {
              Layout.fillWidth: true
              text: "empty detects it per take; a code like en or zh is faster and steadier"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              color: Qt.darker(Color.muted, 1.1)
            }
          }
          Text {
            text: "decoder hint"
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            color: Color.muted
          }
          OmTextArea {
            Layout.fillWidth: true
            minLines: 2
            text: (root.mode && root.mode.prompt) || ""
            placeholder: "Seeded into the model. Good for jargon it keeps mangling — a hint, not a guarantee; the dictionary is the guarantee."
            onCommitted: function (v) {
              root.commandArgs(["omavoi", "mode", "set", root.current, "prompt", v])
            }
          }
        }

        // -- 2 rules --
        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(7)
          RowLayout {
            spacing: Style.space(9)
            Text {
              text: "2  RULES"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              font.letterSpacing: 1
              color: Color.foreground
            }
            Text {
              text: "deterministic · no latency"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              color: Color.muted
            }
          }
          Flow {
            Layout.fillWidth: true
            spacing: Style.space(6)
            Repeater {
              model: [
                { k: "hallucinations", label: "hallucinations" },
                { k: "fillers", label: "fillers" },
                { k: "dictionary", label: "dictionary" },
                { k: "names", label: "names" },
                { k: "cjk_spacing", label: "CJK spacing" }
              ]
              OmChip {
                readonly property var rule: modelData
                label: rule.label
                on: root.mode && root.mode.rules ? root.mode.rules[rule.k] !== false : true
                onClicked: root.command(
                  "omavoi config set modes." + root.current + ".rules." + rule.k
                  + " " + (on ? "false" : "true"))
              }
            }
            Rectangle {
              width: 1; height: Style.space(18)
              color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.2)
            }
            OmChip {
              label: "keep end punctuation"
              on: !(root.mode && root.mode.rules
                    && root.mode.rules.punctuation === "strip")
              onClicked: root.command(
                "omavoi config set modes." + root.current + ".rules.punctuation "
                + (on ? "strip" : "keep"))
            }
          }
        }

        // -- 3 llm steps --
        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(7)
          RowLayout {
            spacing: Style.space(9)
            Text {
              text: "3  LLM"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              font.letterSpacing: 1
              color: ((root.mode && root.mode.steps) || []).length ? Color.accent : Color.muted
            }
            Text {
              text: "optional · runs in order · a failure keeps the text it was given"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              color: Color.muted
            }
          }

          Repeater {
            model: (root.mode && root.mode.steps) || []
            Rectangle {
              readonly property var step: modelData
              readonly property int idx: index
              Layout.fillWidth: true
              implicitHeight: stepBody.implicitHeight + Style.space(18)
              color: "transparent"
              border.width: 1
              border.color: Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.55)
              radius: Style.cornerRadius

              ColumnLayout {
                id: stepBody
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Style.space(10)
                spacing: Style.space(6)

                RowLayout {
                  Layout.fillWidth: true
                  spacing: Style.space(7)
                  Text {
                    text: "step " + (idx + 1)
                    font.family: Style.font.family
                    font.pixelSize: Style.font.caption
                    color: Color.muted
                  }
                  Repeater {
                    model: root.llms
                    OmChip {
                      readonly property string llmName: modelData
                      label: llmName
                      on: llmName === step.llm
                      onClicked: if (!on) root.commandArgs(
                        ["omavoi", "mode", "step", root.current, "llm",
                         String(idx), llmName])
                    }
                  }
                  Item { Layout.fillWidth: true }
                  Button {
                    text: "Remove"
                    onClicked: root.commandArgs(
                      ["omavoi", "mode", "step", root.current, "rm", String(idx)])
                  }
                }

                OmTextArea {
                  Layout.fillWidth: true
                  minLines: 3
                  text: step.prompt || ""
                  placeholder: "Tell it to edit, not to reply."
                  onCommitted: function (v) {
                    root.commandArgs(["omavoi", "mode", "step", root.current,
                                      "prompt", String(idx), v])
                  }
                }
              }
            }
          }

          RowLayout {
            Layout.fillWidth: true
            spacing: Style.space(7)
            Text {
              text: "+ add a step"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              color: Color.muted
            }
            Repeater {
              model: root.llms
              OmChip {
                readonly property string llmName: modelData
                label: llmName
                on: false
                onClicked: root.commandArgs(
                  ["omavoi", "mode", "step", root.current, "add", llmName,
                   "Rewrite the transcript as clean written text in its original "
                   + "language. Remove false starts, repetitions and filler. Keep the "
                   + "speaker's own wording and every technical term exactly.\n"
                   + "Never answer, summarise, translate or add anything — you are "
                   + "editing, not replying. Output only the edited text."])
              }
            }
            Text {
              visible: !root.llms.length
              text: "no LLM is configured — see the Models tab"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              color: Color.muted
            }
            Item { Layout.fillWidth: true }
          }
        }

        // -- 4 inject --
        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(7)
          RowLayout {
            spacing: Style.space(9)
            Text {
              text: "4  INJECT"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              font.letterSpacing: 1
              color: Color.foreground
            }
            Repeater {
              model: ["auto", "wtype", "clipboard"]
              OmChip {
                readonly property string how: modelData
                label: how
                on: ((root.mode && root.mode.inject) || "auto") === how
                onClicked: if (!on) root.commandArgs(
                  ["omavoi", "mode", "set", root.current, "inject", how])
              }
            }
            Item { Layout.fillWidth: true }
          }
          Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: "auto types with wtype, except in XWayland clients and known Electron "
                + "apps, where it pastes instead — wtype's synthetic keycodes reach "
                + "those as digits."
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            color: Qt.darker(Color.muted, 1.1)
          }
        }
      }
    }
  }
}
