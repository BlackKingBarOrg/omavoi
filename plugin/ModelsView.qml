import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Ui

// Two model families side by side, because they are not the same kind of
// thing. Exactly one speech engine runs; any number of LLMs can be defined,
// since different modes reach for different ones. Their costs differ too —
// a speech model is VRAM and RTF, an LLM is latency and, if remote, a key.
Item {
  id: root
  property var payload: ({ models: [], llm: [], vram: ({}), active: "", backend: "", root: "" })
  // What the daemon actually loaded, so an unapplied change is visible.
  property string running: ""
  property var pulling: ({})
  readonly property int pad: Style.space(20)
  signal command(string cmd)

  readonly property bool ggml: payload.backend === "local-whispercpp"
  readonly property var speechModels: (payload.models || []).filter(function (m) {
    return root.ggml ? m.fmt === "ggml" : m.fmt === "ct2"
  })
  readonly property bool stale: running !== "" && payload.active !== undefined
      && String(payload.active) !== ""
      && running.indexOf(String(payload.active).replace("ggml:", "")) === -1

  RowLayout {
    anchors.fill: parent
    spacing: 0

    // ================= SPEECH =================
    Flickable {
      Layout.fillHeight: true
      Layout.preferredWidth: Math.round(root.width * 0.58)
      clip: true
      contentHeight: speech.implicitHeight + root.pad * 2

      ColumnLayout {
        id: speech
        x: root.pad
        y: root.pad
        width: parent.width - root.pad * 2
        spacing: Style.space(9)

        RowLayout {
          spacing: Style.space(9)
          Text {
            text: "SPEECH"
            font.family: Style.font.family
            font.pixelSize: Style.font.subtitle
            font.letterSpacing: 2
            color: Color.foreground
          }
          Text {
            text: "audio → text · one runs"
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            color: Color.muted
          }
        }

        // -- engines, single choice --
        Repeater {
          model: [
            { id: "local-whispercpp", name: "Local · Vulkan",
              detail: "whisper.cpp · ggml weights · NVIDIA, AMD and Intel alike",
              note: "~10 MB of packages" },
            { id: "local-whisper", name: "Local · CUDA",
              detail: "faster-whisper · ct2 weights · NVIDIA only",
              note: "~2.2 GB of wheels" },
            { id: "api", name: "Remote API",
              detail: "OpenAI-compatible · OpenAI, Groq, SiliconFlow, a local server",
              note: "audio leaves this machine" }
          ]
          Rectangle {
            readonly property var eng: modelData
            readonly property bool on: root.payload.backend === eng.id
            Layout.fillWidth: true
            implicitHeight: engRow.implicitHeight + Style.space(16)
            color: on ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.08) : "transparent"
            border.width: 1
            border.color: on ? Color.accent
                             : Qt.rgba(Color.foreground.r, Color.foreground.g,
                                       Color.foreground.b, 0.2)
            radius: Style.cornerRadius

            RowLayout {
              id: engRow
              anchors.left: parent.left
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              anchors.leftMargin: Style.space(11)
              anchors.rightMargin: Style.space(11)
              spacing: Style.space(10)

              Rectangle {
                Layout.alignment: Qt.AlignVCenter
                width: Style.space(9); height: width
                radius: width / 2
                color: on ? Color.accent : "transparent"
                border.width: 1
                border.color: on ? Color.accent : Color.muted
              }
              Text {
                Layout.preferredWidth: Style.space(112)
                text: eng.name
                font.family: Style.font.family
                font.pixelSize: Style.font.body
                color: Color.foreground
              }
              Text {
                Layout.fillWidth: true
                elide: Text.ElideRight
                text: eng.detail
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                color: Color.muted
              }
              Text {
                text: eng.note
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                color: eng.id === "api" ? Color.urgent : Color.muted
              }
            }
            MouseArea {
              anchors.fill: parent
              cursorShape: Qt.PointingHandCursor
              onClicked: if (!on) root.command("omavoi config set speech.backend " + eng.id)
            }
          }
        }

        // -- the daemon has not caught up --
        Rectangle {
          Layout.fillWidth: true
          Layout.topMargin: Style.space(4)
          visible: root.stale
          implicitHeight: staleRow.implicitHeight + Style.space(16)
          color: Qt.rgba(Color.urgent.r, Color.urgent.g, Color.urgent.b, 0.09)
          border.width: 1
          border.color: Color.urgent
          radius: Style.cornerRadius
          RowLayout {
            id: staleRow
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.margins: Style.space(11)
            spacing: Style.space(10)
            ColumnLayout {
              Layout.fillWidth: true
              spacing: 1
              Text {
                text: "The daemon is still running what it started with"
                font.family: Style.font.family
                font.pixelSize: Style.font.body
                color: Color.foreground
              }
              Text {
                Layout.fillWidth: true
                elide: Text.ElideRight
                text: "loaded " + root.running + "   ·   configured " + root.payload.active
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                color: Color.muted
              }
            }
            Button {
              text: "Restart daemon"
              onClicked: root.command("systemctl --user restart omavoid")
            }
          }
        }

        // -- models --
        RowLayout {
          Layout.topMargin: Style.space(8)
          Layout.fillWidth: true
          Text {
            text: "MODELS · " + (root.ggml ? "ggml" : "ct2")
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            font.letterSpacing: 1
            color: Color.muted
          }
          Item { Layout.fillWidth: true }
          Text {
            text: "the format this engine runs"
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            color: Color.muted
          }
        }

        Repeater {
          model: root.speechModels
          RowLayout {
            readonly property var m: modelData
            Layout.fillWidth: true
            spacing: Style.space(10)

            Text {
              Layout.preferredWidth: Style.space(12)
              text: m.active ? "●" : (m.downloaded ? "○" : "")
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              color: m.active ? Color.accent : Color.muted
            }
            Text {
              Layout.preferredWidth: Style.space(178)
              text: m.key
              font.family: Style.font.family
              font.pixelSize: Style.font.body
              color: Color.foreground
            }
            Text {
              Layout.preferredWidth: Style.space(46)
              horizontalAlignment: Text.AlignRight
              text: (m.size_mb / 1024).toFixed(1) + "G"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              color: Color.muted
            }
            Text {
              Layout.fillWidth: true
              elide: Text.ElideRight
              text: m.note
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              color: m.tags.indexOf("recommended") >= 0 ? Color.foreground : Color.muted
            }
            RowLayout {
              Layout.preferredWidth: Style.space(180)
              spacing: Style.space(7)
              Item { Layout.fillWidth: true }
              Text {
                visible: m.downloaded && !m.ours
                text: "already on disk"
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                color: Color.muted
              }
              Text {
                visible: !m.downloaded && root.pulling[m.key] === true
                text: "downloading…"
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                color: Color.accent
              }
              Button {
                visible: !m.downloaded && root.pulling[m.key] !== true
                text: "Download"
                onClicked: root.command("omavoi model pull " + m.key)
              }
              Button {
                visible: m.downloaded && !m.active
                text: "Use"
                onClicked: root.command("omavoi model use " + m.key)
              }
              Button {
                visible: m.downloaded && m.ours && !m.active
                text: "Remove"
                onClicked: root.command("omavoi model rm " + m.key)
              }
            }
          }
        }

        Text {
          Layout.topMargin: Style.space(6)
          Layout.fillWidth: true
          wrapMode: Text.Wrap
          text: "Weights found outside " + (root.payload.root || "our store")
              + " are used where they lie and never deleted."
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
          color: Qt.darker(Color.muted, 1.1)
        }
      }
    }

    Rectangle {
      Layout.fillHeight: true
      Layout.preferredWidth: 1
      color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.18)
    }

    // ================= LLM =================
    Flickable {
      Layout.fillHeight: true
      Layout.fillWidth: true
      clip: true
      contentHeight: llm.implicitHeight + root.pad * 2

      ColumnLayout {
        id: llm
        x: root.pad
        y: root.pad
        width: parent.width - root.pad * 2
        spacing: Style.space(9)

        RowLayout {
          spacing: Style.space(9)
          Text {
            text: "LLM"
            font.family: Style.font.family
            font.pixelSize: Style.font.subtitle
            font.letterSpacing: 2
            color: Color.foreground
          }
          Text {
            text: "text → text · any number, named by modes"
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            color: Color.muted
          }
        }

        Repeater {
          model: root.payload.llm || []
          Rectangle {
            readonly property var l: modelData
            readonly property bool inUse: (l.used_by || []).length > 0
            Layout.fillWidth: true
            implicitHeight: llmBody.implicitHeight + Style.space(18)
            color: inUse ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.06)
                         : "transparent"
            border.width: 1
            border.color: inUse ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.7)
                                : Qt.rgba(Color.foreground.r, Color.foreground.g,
                                          Color.foreground.b, 0.2)
            radius: Style.cornerRadius

            ColumnLayout {
              id: llmBody
              anchors.left: parent.left
              anchors.right: parent.right
              anchors.top: parent.top
              anchors.margins: Style.space(11)
              spacing: Style.space(4)

              RowLayout {
                Layout.fillWidth: true
                spacing: Style.space(8)
                Text {
                  text: l.name
                  font.family: Style.font.family
                  font.pixelSize: Style.font.body
                  color: Color.foreground
                }
                Text {
                  Layout.fillWidth: true
                  elide: Text.ElideRight
                  text: l.model
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                  color: Color.muted
                }
                // Whether using it sends your words off the machine is the
                // one fact worth a badge.
                Text {
                  text: l.remote ? "remote" : "local"
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                  color: l.remote ? Color.urgent : Color.accent
                }
              }

              RowLayout {
                Layout.fillWidth: true
                spacing: Style.space(8)
                Text {
                  Layout.fillWidth: true
                  elide: Text.ElideRight
                  text: {
                    var bits = [l.backend]
                    if (l.base_url) bits.push(l.base_url)
                    if (l.key_env) bits.push(l.key_env + " " + l.key)
                    return bits.join("  ·  ")
                  }
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                  color: Color.muted
                }
                Text {
                  visible: l.key_env && !l.has_key
                  text: "no key"
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                  color: Color.urgent
                }
              }

              Text {
                Layout.fillWidth: true
                text: (l.used_by || []).length
                      ? "used by " + (l.used_by || []).join(", ")
                      : "not named by any mode — costs nothing until one does"
                font.family: Style.font.family
                font.pixelSize: Style.font.caption
                color: (l.used_by || []).length ? Color.accent : Qt.darker(Color.muted, 1.1)
              }
            }
          }
        }

        Text {
          Layout.fillWidth: true
          wrapMode: Text.Wrap
          text: "Endpoints live under [llm.<name>] — omavoi config edit. A key never "
              + "goes in the config: set its environment variable, or put it in "
              + "secrets.toml."
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
          color: Qt.darker(Color.muted, 1.1)
        }

        // -- VRAM --
        ColumnLayout {
          Layout.fillWidth: true
          Layout.topMargin: Style.space(12)
          visible: (root.payload.vram || {}).total_mb !== undefined
          spacing: Style.space(5)

          Text {
            text: "VRAM · " + ((root.payload.vram || {}).name || "")
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            font.letterSpacing: 1
            color: Color.muted
          }
          Rectangle {
            Layout.fillWidth: true
            implicitHeight: Style.space(14)
            color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.12)
            Rectangle {
              width: parent.width * Math.max(0, Math.min(1,
                     ((root.payload.vram || {}).used_mb || 0)
                     / ((root.payload.vram || {}).total_mb || 1)))
              height: parent.height
              color: Color.accent
              opacity: 0.65
            }
          }
          RowLayout {
            Layout.fillWidth: true
            Text {
              text: "in use across the whole machine"
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              color: Color.muted
            }
            Item { Layout.fillWidth: true }
            Text {
              text: (((root.payload.vram || {}).used_mb || 0) / 1024).toFixed(1) + " / "
                    + (((root.payload.vram || {}).total_mb || 0) / 1024).toFixed(1) + " GB"
              font.family: Style.font.family
              font.pixelSize: Style.font.body
              color: Color.foreground
            }
          }
          Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: "Keeping both resident is the point: a chain that loads weights per "
                + "take costs seconds, not milliseconds. Overcommit and the speech "
                + "model is what gets evicted — dictation goes ten times slower with "
                + "nothing to say why."
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            color: Qt.darker(Color.muted, 1.1)
          }
        }
      }
    }
  }
}
