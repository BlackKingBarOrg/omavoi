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

  signal run(string cmd)
  signal refresh()

  Flickable {
    anchors.fill: parent
    contentHeight: setupCol.implicitHeight + view.pad * 2
    clip: true

    ColumnLayout {
      id: setupCol
      x: view.pad
      y: view.pad
      width: card.width - view.pad * 2
      spacing: Style.space(6)

      OmText {
        text: view.missing > 0 ? view.strings.tf("setup.title", view.missing)
                               : view.strings.t("setup.titledone")
        size: "heading"
        color: Color.foreground
      }
      OmText {
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: view.strings.t("setup.blurb")
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
              color: modelData.done ? "#9ece6a"
                   : (modelData.optional ? Color.muted : Color.accent)
            }
            OmText {
              text: modelData.title
              size: "body"
              color: Color.foreground
            }
            OmText {
              visible: modelData.optional && !modelData.done
              text: "optional"
              color: Color.muted
            }
          }

          OmText {
            Layout.leftMargin: Style.space(26)
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: modelData.detail
            color: Color.muted
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
              border.color: Color.muted
              OmText {
                id: cmdText
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: Style.space(10)
                text: "$ " + modelData.command
                color: Color.accent
              }
            }

            Button {
              text: modelData.needs_root ? view.strings.t("setup.copy")
                                         : view.strings.t("setup.run")
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

          OmText {
            visible: !modelData.done && modelData.note
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
          wrapMode: Text.Wrap
          text: view.strings.t("setup.rootblurb")
          color: Color.muted
        }

        StepRunner {
          id: setupRoot
          Layout.fillWidth: true
          strings: strings
          steps: view.rootPlan
          onFinished: view.refresh()
        }

        RowLayout {
          Layout.fillWidth: true
          spacing: Style.space(10)
          Button {
            visible: !setupRoot.running
            text: setupRoot.failure !== "" ? view.strings.t("first.retry")
                                           : view.strings.t("setup.rootrun")
            onClicked: { setupRoot.reset(); setupRoot.begin() }
          }
          OmText {
            visible: setupRoot.running
            // `at` is -1 while idle, and steps[-1] is undefined.
            text: setupRoot.at >= 0 && setupRoot.at < view.rootPlan.length
                  ? view.strings.tf("first.working", view.rootPlan[setupRoot.at].label)
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
        Button { text: view.strings.t("setup.recheck"); onClicked: view.refresh() }
        OmText {
          text: view.strings.t("setup.hint")
          color: Color.muted
        }
      }
    }
  }
}
