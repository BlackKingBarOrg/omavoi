import QtQuick
import QtQuick.Layouts
import qs.Commons

// The title of a section that opens and closes: Advanced on Modes and
// Settings, the rest of the numbers on a take, the machinery on Models.
//
// Closed, it names what inside has been moved off its default. Folding a
// setting away is only safe while a changed one still shows, or the fold is
// where settings go to be forgotten.
Item {
  id: fold

  property string title: ""
  property bool open: false
  // What the closed fold says beside its title; empty says nothing.
  property string summary: ""
  // A rule above, as a section title has.
  property bool rule: true

  signal toggled()
  activeFocusOnTab: true
  Accessible.role: Accessible.Button
  Accessible.name: title
  Accessible.onPressAction: toggled()
  Keys.onSpacePressed: toggled()
  Keys.onReturnPressed: toggled()
  Keys.onEnterPressed: toggled()

  Layout.fillWidth: true
  implicitHeight: body.implicitHeight

  ColumnLayout {
    id: body
    width: parent.width
    spacing: 0

    Rectangle {
      visible: fold.rule
      Layout.fillWidth: true
      Layout.preferredHeight: 1
      Layout.bottomMargin: Style.space(14)
      color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.12)
    }
    RowLayout {
      Layout.fillWidth: true
      spacing: Style.space(10)
      // The shell's own chevrons, the ones its dropdowns draw.
      OmText {
        text: fold.open ? "󰅀" : "󰅂"
        size: "subtitle"
        color: Color.muted
      }
      OmText {
        text: fold.title
        size: "subtitle"
        font.letterSpacing: 1
        color: fold.activeFocus ? Color.accent : Color.foreground
      }
      OmText {
        objectName: "foldSummary"
        visible: !fold.open && fold.summary !== ""
        Layout.fillWidth: true
        elide: Text.ElideRight
        text: fold.summary
        color: Color.accent
      }
      Item { Layout.fillWidth: true }
    }
  }

  MouseArea {
    anchors.fill: parent
    cursorShape: Qt.PointingHandCursor
    onClicked: { fold.forceActiveFocus(); fold.toggled() }
  }
}
