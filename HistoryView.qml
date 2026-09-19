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
  // What the last delete said when it refused. Nothing else on this tab
  // reports anything, so without this a delete against a daemon too old to
  // have `omavoi history rm` -- the plugin updates separately from it --
  // does nothing and says nothing about why.
  property string error: ""

  readonly property var take: (takes && takes.length > selected)
                              ? takes[selected] : null

  // argv rather than a command line: all three of these carry a sentence
  // somebody dictated, and a sentence has spaces, quotes and newlines in it.
  signal runArgs(var argv)
  signal pick(int index)
  signal remove(string id)

  // ---- the right-click menu ---------------------------------------------
  //
  // The take it was opened on rather than the row's index: the list reloads
  // while the menu is up -- finishing a take does it -- and an index would by
  // then name a different take than the one that was clicked. Delete has to
  // mean the row you pointed at.
  property var menuTake: null
  property real menuX: 0
  property real menuY: 0
  readonly property bool menuOpen: view.menuTake !== null

  readonly property var menuActions: {
    var t = view.menuTake
    if (!t) return []
    var out = []
    // A dropped take has no text to copy, and a take old enough for
    // `history.keep_audio` to have swept it has no recording to play.
    if (t.text) out.push({ key: "copy", label: view.strings.t("hist.copy") })
    if (t.wav) out.push({ key: "play", label: view.strings.t("hist.play") })
    out.push({ key: "delete", label: view.strings.t("hist.delete"), danger: true })
    return out
  }

  function openMenu(take, index, point) {
    // Selected as well as pointed at, so the detail on the right is the take
    // the menu is about.
    view.pick(index)
    view.menuTake = take
    view.menuX = point.x
    view.menuY = point.y
  }

  // Returns whether there was a menu to close, so the console can tell an
  // Escape that means "this menu" from one that means "the whole console".
  function dismissMenu() {
    if (!view.menuOpen) return false
    view.menuTake = null
    return true
  }

  function fire(key) {
    var t = view.menuTake
    view.dismissMenu()
    if (!t) return
    if (key === "copy") view.runArgs(["wl-copy", "--", String(t.text || "")])
    else if (key === "play") view.runArgs(["pw-play", String(t.wav || "")])
    else if (key === "delete") view.remove(String(t.id || ""))
  }

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
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onClicked: function (mouse) {
              if (mouse.button === Qt.RightButton)
                view.openMenu(modelData, index, mapToItem(view, mouse.x, mouse.y))
              else
                view.pick(index)
            }
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

      Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: errorText.implicitHeight + Style.space(14)
        visible: view.error !== ""
        color: Qt.rgba(Color.urgent.r, Color.urgent.g, Color.urgent.b, 0.16)
        OmText {
          id: errorText
          anchors.left: parent.left
          anchors.right: parent.right
          anchors.verticalCenter: parent.verticalCenter
          anchors.leftMargin: Style.space(14)
          anchors.rightMargin: Style.space(14)
          wrapMode: Text.Wrap
          text: view.error
          color: Color.urgent
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
              id: segmentRow
              readonly property bool hasConfidence: typeof modelData.avg_logprob === "number"
                                                    && isFinite(modelData.avg_logprob)
              readonly property real logProbability: hasConfidence ? modelData.avg_logprob : 0
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
                  visible: segmentRow.hasConfidence
                  width: parent.width * Math.max(0, Math.min(1,
                         1 + segmentRow.logProbability / 1.5))
                  height: parent.height
                  color: segmentRow.logProbability < -1.0 ? "#e0af68" : "#9ece6a"
                }
              }
              OmText {
                Layout.preferredWidth: Style.space(52)
                text: segmentRow.hasConfidence ? segmentRow.logProbability.toFixed(2) : "—"
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

        // The warnings used to be repeated here as well, under no heading and
        // with a different bullet, half a page below the "what went wrong"
        // block that already lists them. That block is the one with the
        // heading, so this one goes.

        RowLayout {
          Layout.topMargin: Style.space(6)
          spacing: Style.space(8)
          // Copy used to run `omavoi last --raw`, which is two takes away
          // from this one: the last take rather than the selected one, and
          // the model's raw output rather than what was actually typed. The
          // console already has the take in hand, so it copies that.
          Button {
            text: view.strings.t("hist.copy")
            visible: !!(view.take && view.take.text)
            onClicked: view.runArgs(["wl-copy", "--", String(view.take.text)])
          }
          Button {
            text: view.strings.t("hist.play")
            visible: !!(view.take && view.take.wav)
            onClicked: view.runArgs(["pw-play", String(view.take.wav)])
          }
        }
      }
    }
  }

  // ---- the menu itself ---------------------------------------------------
  //
  // Drawn inside this tab rather than as a QtQuick.Controls Menu, which is
  // its own window: the console is a layer-shell surface holding keyboard
  // focus exclusively, and a second window over it is a thing to get wrong
  // for no gain. The full-size MouseArea is what makes a click anywhere else
  // dismiss it.
  MouseArea {
    anchors.fill: parent
    z: 50
    visible: view.menuOpen
    hoverEnabled: true
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    onClicked: view.dismissMenu()

    Rectangle {
      id: menuCard
      x: Math.max(Style.space(4),
                  Math.min(view.menuX, parent.width - width - Style.space(4)))
      y: Math.max(Style.space(4),
                  Math.min(view.menuY, parent.height - height - Style.space(4)))
      width: Style.space(190)
      height: menuRows.implicitHeight + Style.space(10)
      color: Color.popups.background
      radius: Style.cornerRadius
      border.width: 1
      border.color: Color.popups.border

      // Swallow clicks so a miss between two rows does not fall through to
      // the dismissal behind the card.
      MouseArea { anchors.fill: parent }

      ColumnLayout {
        id: menuRows
        anchors.fill: parent
        anchors.margins: Style.space(5)
        spacing: 0

        Repeater {
          model: view.menuActions
          Rectangle {
            readonly property bool danger: modelData.danger === true
            Layout.fillWidth: true
            implicitHeight: menuLabel.implicitHeight + Style.space(14)
            radius: Style.cornerRadius
            color: menuHover.containsMouse
                   ? (danger ? Qt.rgba(Color.urgent.r, Color.urgent.g,
                                       Color.urgent.b, 0.18)
                             : Qt.rgba(Color.foreground.r, Color.foreground.g,
                                       Color.foreground.b, 0.08))
                   : "transparent"

            // A hairline above the destructive row, where there is something
            // above it: a delete one pixel from a copy is a delete you make
            // by accident.
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
              anchors.left: parent.left
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              anchors.leftMargin: Style.space(12)
              anchors.rightMargin: Style.space(12)
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
              onClicked: view.fire(modelData.key)
            }
          }
        }
      }
    }
  }
}
