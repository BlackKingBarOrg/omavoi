import QtQuick
import QtQuick.Controls
import qs.Commons

// A themed multi-line field. qs.Ui's TextField is single-line, and a decoder
// hint or an LLM prompt is several sentences with deliberate line breaks.
//
// Edits commit when the field loses focus rather than on every keystroke:
// each commit rewrites config.toml and makes the daemon re-read it, and doing
// that per character would be absurd.
Rectangle {
  id: root
  property string text: ""
  property string placeholder: ""
  property int minLines: 2
  signal committed(string value)

  readonly property bool dirty: area.text !== root.text

  implicitHeight: Math.max(area.implicitHeight + Style.space(10),
                           Style.font.body * 1.7 * minLines + Style.space(10))
  color: Qt.darker(Color.popups.background, 1.06)
  border.width: 1
  border.color: area.activeFocus ? Color.accent
              : Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b,
                        root.dirty ? 0.55 : 0.22)
  radius: Style.cornerRadius

  function commit() {
    if (root.dirty) root.committed(area.text)
  }

  TextArea {
    id: area
    anchors.fill: parent
    anchors.margins: Style.space(5)
    text: root.text
    placeholderText: root.placeholder
    wrapMode: TextArea.Wrap
    selectByMouse: true
    font.family: Style.font.family
    font.pixelSize: Style.font.caption
    color: Color.foreground
    placeholderTextColor: Color.muted
    background: null
    onActiveFocusChanged: if (!activeFocus) root.commit()
    Keys.onPressed: function (e) {
      if ((e.key === Qt.Key_Return || e.key === Qt.Key_Enter)
          && (e.modifiers & Qt.ControlModifier)) {
        root.commit()
        e.accepted = true
      }
    }
  }

  Text {
    visible: root.dirty
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    anchors.margins: Style.space(4)
    text: "ctrl+enter to save"
    font.family: Style.font.family
    font.pixelSize: Style.font.caption
    color: Color.muted
  }
}
