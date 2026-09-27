import QtQuick
import QtQuick.Layouts
import qs.Commons

// A section's title and the one line under it that says what the section is
// for. The same on every tab: each had its own — caption and muted on
// Settings, subtitle with a note beside it on Models, caption in three
// colours on Modes — so the one thing that should tell a page's parts apart
// was the least consistent thing on it.
//
// The note is optional, and it is a sentence for someone who has not read
// the code: what this part does for you, not how.
ColumnLayout {
  id: section

  property string title: ""
  property string note: ""
  // A rule above, which every section but a page's first one has.
  property bool rule: true

  Layout.fillWidth: true
  spacing: Style.space(3)

  Rectangle {
    visible: section.rule
    Layout.fillWidth: true
    Layout.preferredHeight: 1
    Layout.bottomMargin: Style.space(14)
    color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.12)
  }
  OmText {
    text: section.title
    size: "subtitle"
    font.letterSpacing: 1
    color: Color.foreground
  }
  OmText {
    visible: section.note !== ""
    Layout.fillWidth: true
    Layout.maximumWidth: Style.space(680)
    wrapMode: Text.Wrap
    text: section.note
    color: Color.muted
  }
}
