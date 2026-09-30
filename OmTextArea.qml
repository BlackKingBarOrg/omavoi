import QtQuick
import QtQuick.Controls
import qs.Commons

// A themed multi-line field. qs.Ui's TextField is single-line, and a decoder
// hint or an LLM prompt is several sentences with deliberate line breaks.
//
// Save is explicit. Drafts live in the owning view so switching modes or
// refreshing a repeater never discards text that has not been saved.
Rectangle {
  id: root
  // Handed down like every other view's, because this control has three
  // words of its own and they were the only English left on a Chinese
  // Modes tab.
  property var strings: null
  function t(k) { return root.strings ? root.strings.t(k) : k }
  property alias editor: area
  property string text: ""
  property string placeholder: ""
  property int minLines: 2
  // Changing this reloads the field from `text`. Typing breaks the binding on
  // area.text, so without it switching modes would leave the previous mode's
  // prompt on screen — editable, and about to be saved to the wrong place.
  property string key: ""
  signal committed(string value)
  property var drafts: ({})
  property bool loading: false
  property string loadedKey: ""
  signal draftEdited(string draftKey, var value)
  function syncDraft() {
    root.loading = true
    var draft = root.drafts[root.key]
    var value = draft !== undefined ? draft : root.text
    if (area.text !== value) area.text = value
    root.loadedKey = root.key
    root.loading = false
    if (draft !== undefined && draft === root.text) root.draftEdited(root.key, undefined)
  }
  Timer { id: syncSoon; interval: 0; onTriggered: root.syncDraft() }
  Component.onCompleted: syncSoon.restart()

  readonly property bool dirty: area.text !== root.text

  onKeyChanged: syncSoon.restart()
  onTextChanged: syncSoon.restart()
  onDraftsChanged: syncSoon.restart()

  implicitHeight: Math.max(area.implicitHeight + Style.space(10),
                           Style.font.body * 1.7 * minLines + Style.space(10))
                  + (root.dirty ? Style.space(26) : 0)
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
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.margins: Style.space(5)
    height: parent.height - Style.space(10) - (root.dirty ? Style.space(26) : 0)
    onTextChanged: {
      if (!root.loading && root.loadedKey === root.key)
        root.draftEdited(root.key, text === root.text ? undefined : text)
    }
    placeholderText: root.placeholder
    wrapMode: TextArea.Wrap
    selectByMouse: true
    font.family: Style.font.family
    font.pixelSize: Style.font.caption
    color: Color.foreground
    placeholderTextColor: Color.muted
    background: null
    Keys.onPressed: function (e) {
      if ((e.key === Qt.Key_Return || e.key === Qt.Key_Enter)
          && (e.modifiers & Qt.ControlModifier)) {
        root.commit()
        e.accepted = true
      }
    }
  }

  // An explicit Save, not a commit on focus loss. Losing focus is not an
  // intent: clicking away, closing the panel or tabbing all read the same,
  // and a prompt saved because you looked elsewhere is worse than one you
  // have to press a button for.
  Row {
    visible: root.dirty
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    anchors.margins: Style.space(5)
    spacing: Style.space(6)

    OmText {
      anchors.verticalCenter: parent.verticalCenter
      text: root.t("edit.unsaved")
      color: Color.urgent
    }
    OmChip {
      label: root.t("edit.revert")
      on: false
      onClicked: { root.draftEdited(root.key, undefined); root.syncDraft() }
    }
    OmChip {
      // The shortcut is not translated: ⌃⏎ is the key, not a word.
      label: root.t("edit.save") + "  ⌃⏎"
      on: true
      onClicked: root.commit()
    }
  }
}
