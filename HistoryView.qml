import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Ui

// The history tab: the takes down the left, one take in full on the right.
//
// It was the only tab still living inside Console.qml — Modes, Models,
// Dictionary and Settings had all been components for a while — and it was
// 307 of that file's 1,058 lines. Nothing here changed on the way out.
//
// `take` is derived rather than passed: the console owns the list and the
// index, and two sources for the same thing is how they disagree.
Item {
  id: view

  property var strings: null
  property var takes: []
  // Bound from the console and never written here: assigning to a bound
  // property removes the binding, so one click would have cut this view off
  // from every later change to the console's own index.
  property int selected: 0
  property int pad: Style.space(22)
  // What the daemon says the key is, for the empty state's instruction.
  property string hotkey: ""

  readonly property var take: (takes && takes.length > selected)
                              ? takes[selected] : null

  signal run(string cmd)
  signal pick(int index)

  RowLayout {
    anchors.fill: parent
    spacing: 0

    Rectangle {
      Layout.preferredWidth: Style.space(420)
      Layout.fillHeight: true
      color: Qt.darker(Color.popups.background, 1.12)

      ListView {
        id: list
        anchors.fill: parent
        clip: true
        model: view.takes
        delegate: Rectangle {
          width: list.width
          height: row.implicitHeight + Style.space(18)
          color: index === view.selected ? Qt.rgba(Color.accent.r, Color.accent.g,
                                                   Color.accent.b, 0.12) : "transparent"
          Rectangle {
            width: 2; height: parent.height
            color: index === view.selected ? Color.accent : "transparent"
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
              OmText {
                text: (modelData.mode && modelData.mode.name) || "?"
                color: Color.muted
              }
              Item { Layout.fillWidth: true }
              OmText {
                text: ((modelData.audio && modelData.audio.seconds) || 0).toFixed(1) + "s"
                color: (modelData.warnings && modelData.warnings.length)
                       ? "#e0af68" : Color.muted
              }
            }
            OmText {
              Layout.fillWidth: true
              elide: Text.ElideRight
              text: modelData.text ? modelData.text
                                   : (view.strings.t("hist.dropped")
                                      + (modelData.rejected || ""))
              size: "body"
              color: modelData.text ? Color.foreground : Color.muted
            }
          }
          MouseArea {
            anchors.fill: parent
            onClicked: view.pick(index)
          }
        }
        OmText {
          anchors.centerIn: parent
          visible: view.takes.length === 0
          text: view.strings.tf("hist.none", view.hotkey || view.strings.t("hist.yourkey"))
          size: "body"
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
      contentHeight: detail.implicitHeight + view.pad * 2
      visible: view.take !== null

      ColumnLayout {
        id: detail
        x: view.pad
        y: view.pad
        width: parent.width - view.pad * 2
        spacing: Style.space(14)

        OmText {
          Layout.fillWidth: true
          wrapMode: Text.Wrap
          text: view.take ? (view.take.text || view.take.rejected || "") : ""
          size: "title"
          color: view.take && view.take.text ? Color.foreground : Color.muted
        }

        Flow {
          Layout.fillWidth: true
          spacing: Style.space(18)
          Repeater {
            model: {
              if (!view.take) return []
              var a = view.take.audio || {}, s = view.take.asr || {}
              return [
                { k: view.strings.t("hist.audio"), v: (a.seconds || 0).toFixed(2) + "s" },
                { k: view.strings.t("hist.level"),
                  v: (a.rms_dbfs || 0).toFixed(1) + " dBFS" },
                { k: view.strings.t("hist.decode"),
                  v: (s.decode_seconds || 0).toFixed(2) + "s" },
                { k: "RTF", v: (s.rtf || 0).toFixed(3) },
                { k: view.strings.t("hist.model"), v: s.model || "?" },
                { k: view.strings.t("hist.language"), v: s.language || "?" },
                { k: view.strings.t("hist.mode"),
                  v: (view.take.mode && view.take.mode.name) || "?" },
                { k: view.strings.t("hist.injected"),
                  v: (view.take.inject && view.take.inject.method) || "—" }
              ]
            }
            ColumnLayout {
              spacing: 1
              OmText {
                text: modelData.k
                color: Color.muted
              }
              OmText {
                text: modelData.v
                size: "body"
                color: Color.foreground
              }
            }
          }
        }

        // ---- what went wrong -------------------------------
        //
        // These were recorded all along and shown only as a tint on
        // the duration in the list. A step that falls through returns
        // the previous text, so the take looks like plain dictation
        // and the reason it is plain dictation was unreadable.
        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(4)
          visible: !!(view.take && (view.take.warnings || []).length)
          OmText {
            text: view.strings.t("hist.problems")
            font.letterSpacing: 1
            color: Color.urgent
          }
          Repeater {
            model: (view.take && view.take.warnings) ? view.take.warnings : []
            OmText {
              Layout.fillWidth: true
              wrapMode: Text.Wrap
              text: "· " + modelData
              size: "body"
              color: "#e0af68"
            }
          }
        }

        // ---- the chain, step by step -----------------------------
        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(4)
          visible: !!(view.take && (view.take.steps || []).length)
          OmText {
            text: view.strings.t("hist.steps")
            font.letterSpacing: 1
            color: Color.muted
          }
          Repeater {
            model: (view.take && view.take.steps) ? view.take.steps : []
            RowLayout {
              readonly property var st: modelData
              readonly property bool fell: st.kept === true
              Layout.fillWidth: true
              spacing: Style.space(10)
              OmText {
                Layout.preferredWidth: Style.space(14)
                text: fell ? "✕" : "✓"
                color: fell ? Color.urgent : "#9ece6a"
              }
              OmText {
                Layout.preferredWidth: Style.space(90)
                text: st.llm || "?"
                size: "body"
                color: Color.foreground
              }
              OmText {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: fell
                      ? (view.strings.t("hist.fellthrough")
                         + (st.error ? " — " + st.error : ""))
                      : ((st.seconds !== undefined
                          ? st.seconds.toFixed(2) + "s  " : "")
                         + (st.model || ""))
                color: fell ? "#e0af68" : Color.muted
              }
            }
          }
        }

        OmText {
          visible: !!(view.take && view.take.raw_text
                      && view.take.raw_text !== view.take.text)
          Layout.fillWidth: true
          wrapMode: Text.Wrap
          text: view.strings.t("hist.said") + (view.take ? view.take.raw_text : "")
          size: "body"
          color: Color.muted
        }

        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(4)
          visible: !!(view.take && view.take.post
                      && (view.take.post.changes || []).length)
          OmText {
            text: view.strings.t("hist.post")
            font.letterSpacing: 1
            color: Color.muted
          }
          Repeater {
            model: (view.take && view.take.post) ? view.take.post.changes : []
            OmText {
              Layout.fillWidth: true
              wrapMode: Text.Wrap
              text: "· " + modelData
              size: "body"
              color: Color.foreground
            }
          }
        }

        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(4)
          visible: !!(view.take && view.take.asr
                      && (view.take.asr.segments || []).length)
          OmText {
            text: view.strings.t("hist.segments")
            font.letterSpacing: 1
            color: Color.muted
          }
          Repeater {
            model: (view.take && view.take.asr) ? view.take.asr.segments : []
            RowLayout {
              Layout.fillWidth: true
              spacing: Style.space(12)
              OmText {
                Layout.preferredWidth: Style.space(96)
                text: (modelData.start || 0).toFixed(2) + "–" + (modelData.end || 0).toFixed(2)
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
              OmText {
                Layout.preferredWidth: Style.space(52)
                text: (modelData.avg_logprob || 0).toFixed(2)
                color: Color.muted
              }
              OmText {
                Layout.fillWidth: true
                elide: Text.ElideRight
                text: modelData.text || ""
                size: "body"
                color: Color.foreground
              }
            }
          }
        }

        Repeater {
          model: view.take ? (view.take.warnings || []) : []
          OmText {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: "! " + modelData
            color: "#e0af68"
          }
        }

        RowLayout {
          Layout.topMargin: Style.space(6)
          spacing: Style.space(8)
          Button {
            text: view.strings.t("hist.copy")
            onClicked: view.run("omavoi last --raw | wl-copy")
          }
          Button {
            text: view.strings.t("hist.play")
            visible: !!(view.take && view.take.wav)
            onClicked: view.run("pw-play " + JSON.stringify(view.take.wav))
          }
        }
      }
    }
  }
}
