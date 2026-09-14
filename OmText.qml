import QtQuick
import qs.Commons

// A Text that already knows the font.
//
// Every label in this plugin repeated the same two lines — the family, then
// one of six sizes — 189 times. That is not a style problem: it is two lines
// of noise around every string, and the size, which is the only part that
// varies, was the harder of the two to see.
//
// `size` names the token rather than carrying the number, so a theme that
// redefines caption moves these with it. The chain is written out instead of
// indexing Style.font[size] because a binding on a computed property name
// does not re-evaluate when that property changes, and the whole point is to
// follow the theme.
//
// Input controls keep their own font lines: a TextField is not a label, and
// six of them set the same pair for a different reason.
Text {
  property string size: "caption"

  font.family: Style.font.family
  font.pixelSize: size === "body" ? Style.font.body
                : size === "bodySmall" ? Style.font.bodySmall
                : size === "subtitle" ? Style.font.subtitle
                : size === "title" ? Style.font.title
                : size === "heading" ? Style.font.heading
                : size === "display" ? Style.font.display
                : Style.font.caption
}
