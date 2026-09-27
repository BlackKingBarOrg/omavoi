import QtQuick
import QtQuick.Layouts
import Quickshell.Io
import qs.Commons
import qs.Ui

// The daemon is installed but something it needs is not. It can say what, so
// this stays a checklist rather than a wizard: every row is a thing that is
// missing and the command that would supply it, and the ones needing root are
// folded into a single prompt because polkit reports pacman as auth_admin and
// asks again for every call.
//
// Lifted out of Console.qml, where it was 171 of 1,058 lines and the last
// thing in that file that was a screen rather than the frame around one.
Item {
  id: view

  property var strings: null
  property var setupReport: ({ ready: false, done: 0, total: 5, steps: [] })
  property var rootPlan: []
  property bool daemonPresent: true
  property int pad: Style.space(22)

  // `strings` is null for the instant between creation and the console
  // setting it; every label here called straight through it and logged a
  // TypeError apiece on the way in.
  function t(k) { return view.strings ? view.strings.t(k) : k }
  function tf(k, a) { return view.strings ? view.strings.tf(k, a) : k }

  Tones { id: tones }

  // Counted, not asserted. The heading was the fixed string "Two more pieces
  // to install" sitting over a list the daemon computes — so it said two on a
  // machine that needed four, and two again on this one, where six of six
  // were already done.
  readonly property int missing: {
    var steps = (view.setupReport && view.setupReport.steps) || []
    var n = 0
    for (var i = 0; i < steps.length; i++) if (!steps[i].done) n++
    return n
  }

  // A step's title in the interface's language. The daemon's are English —
  // "Model weights (ggml:large-v3-turbo)" — and this is the second screen a
  // new user meets, straight after a first-run screen that is all in their
  // language (BUG-14). The key is stable; what is in the brackets is lifted
  // out of the daemon's title, and an unknown key keeps the daemon's words.
  function title(step) {
    var raw = String(step.title || "")
    var inner = (raw.match(/\(([^)]*)\)/) || [null, ""])[1]
    if (step.key === "tools") return view.t("setup.s.tools")
    if (step.key === "engine")
      return view.t(raw.indexOf("remote") >= 0 ? "setup.s.engineapi" : "setup.s.engine")
    if (step.key === "model") return view.tf("setup.s.model", inner.replace("ggml:", ""))
    if (step.key === "llm-engine") return view.t("setup.s.llm")
    if (step.key === "hotkey") return view.tf("setup.s.hotkey", inner.split(" ")[0])
    if (step.key === "service") return view.t("setup.s.service")
    return raw
  }
  // What the step is for, said once, for one that is still to do.
  function purpose(step) {
    return step.key === "tools" ? view.t("setup.d.tools")
         : step.key === "engine" ? view.t("setup.d.engine")
         : step.key === "model" ? view.t("setup.d.model")
         : step.key === "llm-engine" ? view.t("setup.d.llm")
         : step.key === "hotkey" ? view.t("setup.d.hotkey")
         : step.key === "service" ? view.t("setup.d.service")
         : ""
  }

  signal run(string cmd)
  signal refresh()

  Flickable {
    id: scroller
    anchors.fill: parent
    contentHeight: setupCol.implicitHeight + view.pad * 2
    clip: true

    ColumnLayout {
      id: setupCol
      x: view.pad
      y: view.pad
      // Its own width, not the console card's: `card.width` named an id in
      // Console.qml and resolved only because the context chain happened to
      // reach it. Anywhere else this view was 540 pixels wide.
      width: Math.min(view.width - view.pad * 2, Style.space(900))
      spacing: Style.space(6)

      OmText {
        text: view.missing > 0 ? view.tf("setup.title", view.missing)
                               : view.t("setup.titledone")
        size: "heading"
        color: Color.foreground
      }
      OmText {
        Layout.fillWidth: true
        Layout.maximumWidth: Style.space(680)
        wrapMode: Text.Wrap
        text: view.t("setup.blurb")
        color: Color.muted
      }

      Repeater {
        model: view.setupReport.steps || []
        ColumnLayout {
          Layout.fillWidth: true
          Layout.topMargin: Style.space(12)
          spacing: Style.space(4)

          RowLayout {
            spacing: Style.space(10)
            OmText {
              text: modelData.done ? "󰄬" : (modelData.optional ? "󰅖" : "󰄰")
              size: "body"
              color: modelData.done ? tones.good
                   : (modelData.optional ? Color.muted : Color.accent)
            }
            OmText {
              text: view.title(modelData)
              size: "body"
              color: Color.foreground
            }
            OmText {
              visible: modelData.optional && !modelData.done
              text: view.t("setup.optional")
              color: Color.muted
            }
          }

          OmText {
            visible: !modelData.done && view.purpose(modelData) !== ""
            Layout.leftMargin: Style.space(26)
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: view.purpose(modelData)
            color: Color.muted
          }
          // The daemon's own detail: a path, a list of programs, what is
          // missing. Specific and technical, so smaller and dimmer.
          OmText {
            Layout.leftMargin: Style.space(26)
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: modelData.detail
            color: Qt.darker(Color.muted, 1.15)
          }

          RowLayout {
            visible: !modelData.done && modelData.command
            Layout.leftMargin: Style.space(26)
            Layout.fillWidth: true
            spacing: Style.space(10)

            Rectangle {
              Layout.fillWidth: true
              implicitHeight: cmdText.implicitHeight + Style.space(12)
              color: Qt.darker(Color.popups.background, 1.35)
              border.width: 1
              border.color: Qt.rgba(Color.muted.r, Color.muted.g, Color.muted.b, 0.6)
              radius: Style.cornerRadius
              OmText {
                id: cmdText
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: Style.space(10)
                anchors.rightMargin: Style.space(10)
                elide: Text.ElideRight
                text: "$ " + modelData.command
                color: Color.accent
              }
            }

            Button {
              text: modelData.needs_root ? view.t("setup.copy")
                                         : view.t("setup.run")
              bordered: true
              fontSize: Style.font.caption
              onClicked: {
                if (modelData.needs_root) {
                  // Root work belongs in a terminal the user is
                  // looking at, not behind a button in a bar plugin.
                  view.run("wl-copy -- " + JSON.stringify(modelData.command))
                } else {
                  view.run(modelData.command + " ; true")
                }
              }
            }
          }

          // The daemon's note is English, written alongside its command. The
          // line above says what the step is for in the interface's
          // language, so the note goes only where it can be read as written.
          OmText {
            visible: !modelData.done && !!modelData.note
                     && (!view.strings || view.strings.active === "en")
            Layout.leftMargin: Style.space(26)
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: modelData.note
            color: Qt.darker(Color.muted, 1.15)
          }
        }
      }

      // Root steps, run here instead of sending you to a terminal.
      // Hidden by refresh() once there is nothing left needing root.
      ColumnLayout {
        visible: view.rootPlan.length > 0
        Layout.topMargin: Style.space(18)
        Layout.fillWidth: true
        spacing: Style.space(6)

        OmText {
          Layout.fillWidth: true
          Layout.maximumWidth: Style.space(680)
          wrapMode: Text.Wrap
          text: view.t("setup.rootblurb")
          color: Color.muted
        }

        // `view.strings`, not `strings`: inside the runner that name is the
        // runner's own property, so the binding was to itself and the plan
        // printed its keys — "first.willrun", "first.needspassword".
        StepRunner {
          id: setupRoot
          Layout.fillWidth: true
          strings: view.strings
          steps: view.rootPlan
          onFinished: view.refresh()
        }

        RowLayout {
          Layout.fillWidth: true
          spacing: Style.space(10)
          Button {
            visible: !setupRoot.running
            text: setupRoot.failure !== "" ? view.t("first.retry")
                                           : view.t("setup.rootrun")
            bordered: true
            fontSize: Style.font.caption
            onClicked: { setupRoot.reset(); setupRoot.begin() }
          }
          OmText {
            visible: setupRoot.running
            // `at` is -1 while idle, and steps[-1] is undefined.
            text: setupRoot.at >= 0 && setupRoot.at < view.rootPlan.length
                  ? view.tf("first.working", view.rootPlan[setupRoot.at].label)
                  : ""
            size: "body"
            color: Color.accent
          }
          OmText {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            visible: setupRoot.failure !== ""
            text: setupRoot.failure
            color: Color.urgent
          }
        }
      }

      RowLayout {
        Layout.topMargin: Style.space(18)
        spacing: Style.space(10)
        Button {
          text: view.t("setup.recheck")
          bordered: true
          fontSize: Style.font.caption
          onClicked: view.refresh()
        }
        OmText {
          text: view.t("setup.hint")
          color: Color.muted
        }
      }
    }
  }
}
