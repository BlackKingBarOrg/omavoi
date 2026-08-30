import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Ui

// Two kinds of entry, because they solve different problems. A rule needs you
// to know what the model got wrong. A name does not — and for CJK you never
// will, since the manglings are an open set of homophones — so a name is
// written once, correctly, and matched by sound.
Flickable {
  id: root
  property var rules: []
  property var names: []
  property string seed: ""
  property int budget: 224
  property int pad: Style.space(22)
  property string sub: "rules"
  signal command(string cmd)

  contentHeight: col.implicitHeight + pad * 2
  clip: true

  ColumnLayout {
    id: col
    x: root.pad
    y: root.pad
    width: root.width - root.pad * 2
    spacing: Style.space(12)

    ButtonGroup {
      options: ["rules", "names"]
      value: root.sub
      onChanged: function (v) { root.sub = v }
    }

    // ---- rules -----------------------------------------------------
    Text {
      visible: root.sub === "rules"
      Layout.fillWidth: true
      wrapMode: Text.Wrap
      text: "heard → meant. A decoder prompt is a hint the model may ignore; this is "
          + "the guarantee. The longest key is tried first, so a shorter one it "
          + "contains can never fire."
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      color: Color.muted
    }
    Repeater {
      model: root.sub === "rules" ? root.rules : []
      RowLayout {
        readonly property var r: modelData
        Layout.fillWidth: true
        spacing: Style.space(10)
        Text {
          Layout.preferredWidth: Style.space(180)
          text: r.heard
          font.family: Style.font.family
          font.pixelSize: Style.font.body
          color: Color.foreground
        }
        Text {
          text: "→"
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
          color: Color.muted
        }
        Text {
          Layout.preferredWidth: Style.space(180)
          text: r.meant
          font.family: Style.font.family
          font.pixelSize: Style.font.body
          color: Color.foreground
        }
        Text {
          Layout.fillWidth: true
          visible: r.shadowed_by !== ""
          text: "never fires — shadowed by \"" + r.shadowed_by + "\""
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
          color: "#e0af68"
        }
        Item { Layout.fillWidth: r.shadowed_by === "" }
        Button {
          text: "Remove"
          onClicked: root.command("omavoi dict rm " + JSON.stringify(r.heard))
        }
      }
    }

    // ---- names -----------------------------------------------------
    Text {
      visible: root.sub === "names"
      Layout.fillWidth: true
      wrapMode: Text.Wrap
      text: "Write only the correct form. Names are seeded into the decoder prompt so "
          + "the model produces them, and matched by sound afterwards so homophones "
          + "collapse back. Matching stays off until a dry run has been looked at — "
          + "it is the one thing here that can damage text that was already right."
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      color: Color.muted
    }
    Repeater {
      model: root.sub === "names" ? root.names : []
      RowLayout {
        readonly property var n: modelData
        Layout.fillWidth: true
        spacing: Style.space(10)
        Text {
          Layout.preferredWidth: Style.space(150)
          text: n.name
          font.family: Style.font.family
          font.pixelSize: Style.font.body
          color: Color.foreground
        }
        Text {
          Layout.preferredWidth: Style.space(170)
          text: n.key
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
          color: Color.muted
        }
        Text {
          Layout.preferredWidth: Style.space(80)
          text: n.match
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
          color: Color.muted
        }
        Text {
          Layout.preferredWidth: Style.space(110)
          text: n.enabled ? "matching" : "seed only"
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
          color: n.enabled ? "#9ece6a" : Color.muted
        }
        Item { Layout.fillWidth: true }
        Button {
          text: "Remove"
          onClicked: root.command("omavoi names rm " + JSON.stringify(n.name))
        }
      }
    }
    RowLayout {
      visible: root.sub === "names"
      Layout.topMargin: Style.space(8)
      spacing: Style.space(10)
      Button { text: "Dry run"; onClicked: root.command("omavoi names dryrun") }
      Button { text: "Enable matching"; onClicked: root.command("omavoi names enable") }
      Text {
        Layout.fillWidth: true
        elide: Text.ElideRight
        text: "prompt: " + (root.seed || "(none)")
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        color: Color.muted
      }
    }

    Text {
      Layout.topMargin: Style.space(12)
      Layout.fillWidth: true
      wrapMode: Text.Wrap
      text: root.sub === "rules"
            ? "Add one with  omavoi dict add <heard> <meant>"
            : "Add several at once with  omavoi names add <name> <name> …"
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      color: Color.muted
    }
  }
}
