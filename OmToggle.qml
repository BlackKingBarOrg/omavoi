import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Ui

// Compact, model-owned switch. The track makes independent settings distinct
// from the chips used for mutually exclusive choices.
Item {
  id: root
  property string label: ""
  property bool on: false
  signal clicked()
  implicitWidth: body.implicitWidth
  implicitHeight: Math.max(body.implicitHeight, Style.space(30))
  activeFocusOnTab: true
  Accessible.role: Accessible.CheckBox
  Accessible.name: label
  Accessible.checkable: true
  Accessible.checked: on
  Accessible.onToggleAction: if (enabled) clicked()
  Keys.onSpacePressed: if (enabled) clicked()
  Keys.onReturnPressed: if (enabled) clicked()
  Keys.onEnterPressed: if (enabled) clicked()
  opacity: enabled ? 1 : 0.5
  RowLayout {
    id: body
    anchors.verticalCenter: parent.verticalCenter
    spacing: Style.space(7)
    ToggleSwitch { checked: root.on; interactive: false; hasCursor: root.activeFocus || mouse.containsMouse; cursorRing: true }
    OmText { text: root.label; color: Color.foreground }
  }
  MouseArea {
    id: mouse
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    onClicked: { root.forceActiveFocus(); root.clicked() }
  }
}
