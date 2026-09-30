import QtQuick
import QtQuick.Controls as Controls
import "UiLabels.js" as Labels
import QtQuick.Layouts
import qs.Commons
import qs.Ui

// The history tab: the takes down the left, one take in full on the right.
//
// It was the only tab still living inside Console.qml — Modes, Models,
// Dictionary and Settings had all been components for a while — and it was
// 307 of that file's 1,058 lines.
//
// `take` is derived rather than passed: the console owns the list and the
// index, and two sources for the same thing is how they disagree.
//
// The detail is in two halves, like the settings: what a person reading back
// a take wants — what it typed, what went wrong, what the AI steps did, what
// the model actually heard — and, folded underneath, the numbers behind it.
// Every sentence the daemon writes about a take is English and written for a
// log; the ones this view knows are said in the interface's language, and
// the daemon's own words stay in the fold, verbatim.
Item {
  id: view

  property var strings: null
  property var takes: []
  property bool hasMore: false
  property bool loading: false
  signal loadMore()
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
  // The numbers behind a take, folded; open stays open from take to take.
  property bool detailsOpen: false

  readonly property var take: (takes && takes.length > selected)
                              ? takes[selected] : null

  // argv rather than a command line: all three of these carry a sentence
  // somebody dictated, and a sentence has spaces, quotes and newlines in it.
  signal runArgs(var argv)
  signal pick(int index)
  signal remove(string id)

  Tones { id: tones }

  // `strings` is null for the instant between creation and the console
  // setting it; every other view already guarded this, and this one logged
  // a TypeError per label on each opening instead.
  function t(k) { return view.strings ? view.strings.t(k) : k }
  function tf(k, a) { return view.strings ? view.strings.tf(k, a) : k }
  function fmt(k, a, b, c) {
    return view.t(k).replace("%1", a).replace("%2", b).replace("%3", c === undefined ? "" : c)
  }

  // -- the daemon's sentences, in the reader's language ---------------------

  // When a take was, as briefly as it can be said: the time today, "yesterday"
  // and the time, and the date beyond that.
  function when(ts) {
    if (!ts) return ""
    var d = new Date(ts * 1000)
    var now = new Date()
    var day = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    var hm = Qt.formatDateTime(d, "hh:mm")
    if (d >= day) return hm
    if (d >= new Date(day.getTime() - 86400000)) return view.tf("hist.yesterday", hm)
    if (d.getFullYear() === now.getFullYear()) return Qt.formatDateTime(d, "MM-dd hh:mm")
    return Qt.formatDateTime(d, "yyyy-MM-dd")
  }
  // Why a take typed nothing.
  function dropped(reason) {
    var r = String(reason || "")
    var m = r.match(/^only ([\d.]+)s, below/)
    if (m) return view.tf("hist.drop.short", Number(m[1]).toFixed(1))
    if (r === "empty" || r === "nothing left after post-processing"
        || r.indexOf("all text segments rejected") === 0)
      return view.t("hist.drop.nospeech")
    if (r.indexOf("transcription failed") === 0) return view.t("hist.drop.failed")
    return r
  }
  function llmName(name) {
    return name === "agent" ? view.t("models.k.agent")
         : name === "api" ? view.t("models.k.api")
         : name === "local" ? view.t("models.k.local")
         : String(name || "?")
  }
  function warning(w) {
    var s = String(w || ""), m
    if ((m = s.match(/^input is quiet: rms (-?[\d.]+) dBFS/)))
      return view.tf("hist.w.quiet", m[1])
    if ((m = s.match(/^step (\d+) \(([^)]+)\) fell through: (.*)$/)))
      return view.fmt("hist.w.step", m[1], view.llmName(m[2]), m[3])
    if ((m = s.match(/^step (\d+): llm '([^']+)' unavailable — (.*)$/)))
      return view.fmt("hist.w.step", m[1], view.llmName(m[2]), m[3])
    if (s.indexOf("the ring buffer wrapped") === 0) return view.t("hist.w.wrapped")
    if (s.indexOf("low confidence") === 0) return view.t("hist.w.lowconf")
    if (s.indexOf("a segment may be silence") === 0) return view.t("hist.w.silence")
    if (s.indexOf("this is an X11 window and xdotool") === 0) return view.t("hist.w.noxdotool")
    if (s.indexOf("Chinese script conversion failed") === 0) return view.t("hist.w.script")
    if ((m = s.match(/^injection fell back to (\S+)/))) return view.tf("hist.w.fellback", m[1])
    if (s.indexOf("injection failed") === 0) return view.t("hist.w.injectfailed")
    return s
  }
  // What a rule did to the text.
  function change(c) {
    var s = String(c || "")
    if (s === "fillers") return view.t("hist.c.fillers")
    if (s === "deduped") return view.t("hist.c.deduped")
    if (s === "cjk spacing") return view.t("hist.c.spacing")
    if (s === "line breaks folded" || s.indexOf("newlines folded") === 0) return view.t("hist.c.lines")
    if (s.indexOf("punctuation=") === 0) return view.t("hist.c.punct")
    if (s.indexOf("dictionary: ") === 0) return view.tf("hist.c.dictionary", s.slice(12).replace(/×\d+/g, ""))
    if (s.indexOf("names: ") === 0) return view.tf("hist.c.dictionary", s.slice(7).replace(/->/g, "→"))
    if (s.indexOf("segment ") === 0 && s.indexOf("silence") >= 0) return view.t("hist.c.silence")
    if (s === "Chinese script: zh-Hans") return view.t("hist.c.hans")
    if (s === "Chinese script: zh-Hant") return view.t("hist.c.hant")
    return s
  }

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
    if (t.text) out.push({ key: "copy", label: view.t("hist.copy") })
    if (t.wav) out.push({ key: "play", label: view.t("hist.play") })
    out.push({ key: "delete", label: view.t("hist.delete"), danger: true })
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
      // The console card's bottom-left corner, less its border, so a theme
      // that rounds its windows does not get a square pane poking out.
      bottomLeftRadius: Math.max(0, Style.cornerRadius - Math.max(1, Style.space(2)))
      color: Qt.darker(Color.popups.background, 1.12)

      ListView {
        id: list
        anchors.fill: parent
        anchors.bottomMargin: historyFooter.height
        clip: true
        Controls.ScrollBar.vertical: Controls.ScrollBar {}
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
              spacing: Style.space(8)
              // When, first: it is what a list of takes is read by, and it
              // was the one thing the row did not say (UX-06).
              OmText {
                text: view.when(modelData.ts)
                color: Color.muted
              }
              OmText {
                Layout.fillWidth: true
                elide: Text.ElideRight
                text: Labels.mode((modelData.mode && modelData.mode.name) || "?", view.strings)
                color: Qt.darker(Color.muted, 1.15)
              }
              OmText {
                text: ((modelData.audio && modelData.audio.seconds) || 0).toFixed(1) + "s"
                color: (modelData.warnings && modelData.warnings.length)
                       ? tones.warn : Color.muted
              }
            }
            OmText {
              Layout.fillWidth: true
              elide: Text.ElideRight
              maximumLineCount: 2
              wrapMode: Text.Wrap
              text: modelData.text ? modelData.text
                                   : view.tf("hist.droppedas", view.dropped(modelData.rejected))
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
          width: parent.width - Style.space(40)
          horizontalAlignment: Text.AlignHCenter
          wrapMode: Text.Wrap
          visible: view.takes.length === 0
          text: view.tf("hist.none", view.hotkey || view.t("hist.yourkey"))
          size: "body"
          color: Color.muted
        }
      }

      RowLayout {
        id: historyFooter
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        anchors.margins: Style.space(10)
        height: view.takes.length > 0 ? implicitHeight + Style.space(10) : 0
        visible: view.takes.length > 0
        OmText { Layout.fillWidth: true; text: view.tf("hist.showing", view.takes.length); color: Color.muted }
        Button {
          visible: view.hasMore
          text: view.t("hist.more"); bordered: true; fontSize: Style.font.caption
          enabled: !view.loading
          onClicked: view.loadMore()
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

    // Detail. This is the answer to "why did it type that".
    Flickable {
      id: pane
      Layout.fillWidth: true
      Layout.fillHeight: true
      clip: true
      Controls.ScrollBar.vertical: Controls.ScrollBar {}
      contentHeight: detail.implicitHeight + view.pad * 2
      visible: view.take !== null

      ColumnLayout {
        id: detail
        x: view.pad
        y: view.pad
        width: Math.min(pane.width - view.pad * 2, Style.space(900))
        spacing: Style.space(18)

        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(6)
          OmText {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: view.take ? (view.take.text || view.dropped(view.take.rejected)) : ""
            size: "title"
            color: view.take && view.take.text ? Color.foreground : Color.muted
          }
          // Mode, length and when. The eight-number strip that stood here is
          // under the numbers fold below.
          OmText {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: {
              if (!view.take) return ""
              var parts = [Labels.mode((view.take.mode && view.take.mode.name) || "?", view.strings),
                           ((view.take.audio && view.take.audio.seconds) || 0).toFixed(1) + "s"]
              var w = view.when(view.take.ts)
              if (w !== "") parts.push(w)
              return parts.join("  ·  ")
            }
            color: Color.muted
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
          spacing: Style.space(6)
          visible: !!(view.take && (view.take.warnings || []).length)
          OmText {
            text: view.t("hist.problems")
            size: "subtitle"
            font.letterSpacing: 1
            color: tones.warn
          }
          Repeater {
            model: (view.take && view.take.warnings) ? view.take.warnings : []
            OmText {
              Layout.fillWidth: true
              Layout.maximumWidth: Style.space(760)
              wrapMode: Text.Wrap
              text: "· " + view.warning(modelData)
              size: "body"
              color: Color.foreground
            }
          }
        }

        // ---- the AI steps ------------------------------------------
        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(6)
          visible: !!(view.take && (view.take.steps || []).length)
          OmText {
            text: view.t("modes.s3")
            size: "subtitle"
            font.letterSpacing: 1
            color: Color.foreground
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
                color: fell ? Color.urgent : tones.good
              }
              OmText {
                Layout.preferredWidth: Style.space(130)
                text: view.llmName(st.llm)
                size: "body"
                color: Color.foreground
              }
              OmText {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: fell
                      ? view.t("hist.fellthrough")
                      : (st.seconds !== undefined ? view.tf("hist.took", st.seconds.toFixed(1)) : "")
                color: fell ? tones.warn : Color.muted
              }
            }
          }
        }

        // What the recognizer heard, when something changed it.
        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(6)
          visible: !!(view.take && view.take.raw_text
                      && view.take.raw_text !== view.take.text)
          OmText {
            text: view.t("hist.said")
            size: "subtitle"
            font.letterSpacing: 1
            color: Color.foreground
          }
          OmText {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: view.take ? view.take.raw_text : ""
            size: "body"
            color: Color.muted
          }
        }

        // What the rules did to it, in words.
        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(6)
          visible: !!(view.take && view.take.post
                      && (view.take.post.changes || []).length)
          OmText {
            text: view.t("hist.post")
            size: "subtitle"
            font.letterSpacing: 1
            color: Color.foreground
          }
          Repeater {
            model: (view.take && view.take.post) ? view.take.post.changes : []
            OmText {
              Layout.fillWidth: true
              wrapMode: Text.Wrap
              text: "· " + view.change(modelData)
              size: "body"
              color: Color.foreground
            }
          }
        }

        RowLayout {
          // Not there at all for a dropped take, which has neither: an empty
          // row still costs the column's spacing on both sides.
          visible: !!view.take
          spacing: Style.space(8)
          // Copy used to run `omavoi last --raw`, which is two takes away
          // from this one: the last take rather than the selected one, and
          // the model's raw output rather than what was actually typed. The
          // console already has the take in hand, so it copies that.
          Button {
            text: view.t("hist.copy")
            bordered: true
            fontSize: Style.font.caption
            visible: !!(view.take && view.take.text)
            onClicked: view.runArgs(["wl-copy", "--", String(view.take.text)])
          }
          Button {
            text: view.t("hist.play")
            bordered: true
            fontSize: Style.font.caption
            visible: !!(view.take && view.take.wav)
            onClicked: view.runArgs(["pw-play", String(view.take.wav)])
          }
          Button {
            text: "⋯"; bordered: true; fontSize: Style.font.caption
            Accessible.name: view.t("word.more")
            onClicked: view.openMenu(view.take, view.selected, mapToItem(view, 0, height))
          }
        }

        OmText {
          visible: !!view.take && !view.take.wav
          Layout.fillWidth: true; wrapMode: Text.Wrap
          text: view.t("hist.noaudio"); color: Color.muted
        }

        // ---- the numbers ------------------------------------------------
        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(12)
          FoldHeader {
            objectName: "historyDetails"
            title: view.t("hist.details")
            open: view.detailsOpen
            onToggled: view.detailsOpen = !view.detailsOpen
          }
          ColumnLayout {
            visible: view.detailsOpen
            Layout.fillWidth: true
            spacing: Style.space(14)

            Flow {
              Layout.fillWidth: true
              spacing: Style.space(18)
              Repeater {
                model: {
                  if (!view.take) return []
                  var a = view.take.audio || {}, s = view.take.asr || {}
                  return [
                    { k: view.t("hist.audio"), v: (a.seconds || 0).toFixed(2) + "s" },
                    { k: view.t("hist.level"), v: (a.rms_dbfs || 0).toFixed(1) + " dBFS" },
                    { k: view.t("hist.decode"), v: (s.decode_seconds || 0).toFixed(2) + "s" },
                    { k: "RTF", v: (s.rtf || 0).toFixed(3) },
                    { k: view.t("hist.model"), v: String(s.model || "?").replace("ggml:", "") },
                    { k: view.t("hist.language"), v: s.language || "?" },
                    { k: view.t("hist.injected"),
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
            OmText {
              Layout.fillWidth: true
              Layout.maximumWidth: Style.space(680)
              wrapMode: Text.Wrap
              text: view.t("hist.rtfnote")
              color: Qt.darker(Color.muted, 1.1)
            }

            // The daemon's own words for what went wrong, verbatim, for
            // anyone who wants the number the friendly sentence rounded.
            ColumnLayout {
              Layout.fillWidth: true
              spacing: Style.space(4)
              visible: !!(view.take && ((view.take.warnings || []).length || view.take.rejected))
              OmText {
                text: view.t("hist.raw")
                color: Color.muted
              }
              Repeater {
                model: view.take ? (view.take.warnings || []).concat(view.take.rejected ? [view.take.rejected] : []) : []
                OmText {
                  Layout.fillWidth: true
                  wrapMode: Text.Wrap
                  text: "· " + modelData
                  color: Qt.darker(Color.muted, 1.1)
                }
              }
            }

            ColumnLayout {
              Layout.fillWidth: true
              spacing: Style.space(4)
              visible: !!(view.take && view.take.asr
                          && (view.take.asr.segments || []).length)
              OmText {
                text: view.t("hist.segments")
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
                      color: segmentRow.logProbability < -1.0 ? tones.warn : tones.good
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
