import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Ui

// What is left once Modes took the contextual choices and Models took the
// weights: the physical and the global. A key, a microphone, an overlay, and
// what stays on disk.
Flickable {
  id: root
  property var cfg: ({})
  property var setupReport: ({ steps: [] })
  property int pad: Style.space(22)
  signal command(string cmd)

  function get(path, fallback) {
    var node = root.cfg
    var parts = path.split(".")
    for (var i = 0; i < parts.length; i++) {
      if (!node || node[parts[i]] === undefined) return fallback
      node = node[parts[i]]
    }
    return node
  }

  contentHeight: col.implicitHeight + pad * 2
  clip: true

  ColumnLayout {
    id: col
    x: root.pad
    y: root.pad
    width: root.width - root.pad * 2
    spacing: Style.space(18)

    // ---- hotkey ----------------------------------------------------
    ColumnLayout {
      Layout.fillWidth: true
      spacing: Style.space(8)
      Text {
        text: "HOTKEY"
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        font.letterSpacing: 1
        color: Color.muted
      }
      RowLayout {
        Layout.fillWidth: true
        Text {
          Layout.preferredWidth: Style.space(160)
          text: "key"
          font.family: Style.font.family
          font.pixelSize: Style.font.body
          color: Color.muted
        }
        Text {
          text: root.get("hotkey.key", "?")
          font.family: Style.font.family
          font.pixelSize: Style.font.body
          color: Color.foreground
        }
      }
      RowLayout {
        Layout.fillWidth: true
        Text {
          Layout.preferredWidth: Style.space(160)
          text: "behaviour"
          font.family: Style.font.family
          font.pixelSize: Style.font.body
          color: Color.muted
        }
        ButtonGroup {
          options: ["push_to_talk", "toggle"]
          value: root.get("hotkey.mode", "push_to_talk")
          onChanged: function (v) { root.command("omavoi config set hotkey.mode " + v) }
        }
      }
      Text {
        Layout.maximumWidth: Style.space(760)
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: "Read from evdev, below xkb, so the key stays where it physically is even "
            + "if your layout remaps it. A modifier cannot be bound in Hyprland instead: "
            + "pressing one changes the modmask, which fires the release binding at once "
            + "and records a 0.0s take."
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        color: Qt.darker(Color.muted, 1.15)
      }
    }

    // ---- audio -----------------------------------------------------
    ColumnLayout {
      Layout.fillWidth: true
      spacing: Style.space(8)
      Text {
        text: "AUDIO"
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        font.letterSpacing: 1
        color: Color.muted
      }
      Repeater {
        model: [
          { k: "audio.preroll_seconds", label: "pre-roll", unit: "s",
            why: "Audio kept from before the key went down. Lower it and the first "
               + "syllable starts going missing while PipeWire opens the stream." },
          { k: "audio.tail_seconds", label: "tail", unit: "s", why: "" },
          { k: "audio.warn_rms_dbfs", label: "warn below", unit: " dBFS", why: "" },
          { k: "audio.max_seconds", label: "max take", unit: "s", why: "" }
        ]
        ColumnLayout {
          readonly property var row: modelData
          Layout.fillWidth: true
          spacing: Style.space(2)
          RowLayout {
            Layout.fillWidth: true
            Text {
              Layout.preferredWidth: Style.space(160)
              text: row.label
              font.family: Style.font.family
              font.pixelSize: Style.font.body
              color: Color.muted
            }
            Text {
              text: root.get(row.k, "?") + row.unit
              font.family: Style.font.family
              font.pixelSize: Style.font.body
              color: Color.foreground
            }
          }
          Text {
            visible: row.why !== ""
            Layout.maximumWidth: Style.space(760)
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: row.why
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            color: Qt.darker(Color.muted, 1.15)
          }
        }
      }
    }

    // ---- hud -------------------------------------------------------
    ColumnLayout {
      Layout.fillWidth: true
      spacing: Style.space(8)
      Text {
        text: "HUD"
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        font.letterSpacing: 1
        color: Color.muted
      }
      RowLayout {
        Layout.fillWidth: true
        Text {
          Layout.preferredWidth: Style.space(160)
          text: "keep the result up"
          font.family: Style.font.family
          font.pixelSize: Style.font.body
          color: Color.muted
        }
        ButtonGroup {
          options: ["always", "changed", "never"]
          value: root.get("ui.hud_dwell", "changed")
          onChanged: function (v) { root.command("omavoi config set ui.hud_dwell " + v) }
        }
      }
      Text {
        Layout.maximumWidth: Style.space(760)
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: "\"changed\" is the default: a dwell you always pay for turns into noise "
            + "the moment you dictate two sentences in a row, but a silent correction "
            + "you never saw is worse."
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        color: Qt.darker(Color.muted, 1.15)
      }
      RowLayout {
        Layout.fillWidth: true
        Text {
          Layout.preferredWidth: Style.space(160)
          text: "notifications"
          font.family: Style.font.family
          font.pixelSize: Style.font.body
          color: Color.muted
        }
        OmChip {
          label: root.get("ui.notify", true) === true ? "on" : "off"
          on: root.get("ui.notify", true) === true
          onClicked: root.command(
            "omavoi config set ui.notify " + (on ? "false" : "true"))
        }
      }
    }

    // ---- history and privacy ---------------------------------------
    ColumnLayout {
      Layout.fillWidth: true
      spacing: Style.space(8)
      Text {
        text: "HISTORY"
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        font.letterSpacing: 1
        color: Color.muted
      }
      RowLayout {
        Layout.fillWidth: true
        Text {
          Layout.preferredWidth: Style.space(160)
          text: "keep audio for"
          font.family: Style.font.family
          font.pixelSize: Style.font.body
          color: Color.muted
        }
        Text {
          text: root.get("history.keep_audio", 0) + " takes"
          font.family: Style.font.family
          font.pixelSize: Style.font.body
          color: Color.foreground
        }
      }
      Text {
        Layout.maximumWidth: Style.space(760)
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: "Stored audio is what makes re-running a take on another model, and the "
            + "names dry run, possible. Set it to 0 and those go away with it."
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        color: Qt.darker(Color.muted, 1.15)
      }

      Rectangle {
        Layout.fillWidth: true
        Layout.topMargin: Style.space(6)
        implicitHeight: privacy.implicitHeight + Style.space(20)
        color: "transparent"
        border.width: 1
        border.color: Qt.rgba(Color.muted.r, Color.muted.g, Color.muted.b, 0.6)

        ColumnLayout {
          id: privacy
          anchors.left: parent.left
          anchors.right: parent.right
          anchors.top: parent.top
          anchors.margins: Style.space(10)
          spacing: Style.space(4)
          Text {
            text: "Audio never leaves this machine"
            font.family: Style.font.family
            font.pixelSize: Style.font.body
            color: "#9ece6a"
          }
          Text {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: "Speech runs on the local GPU in every mode. A mode whose LLM step is "
                + "a remote model does send the transcribed text out — the Modes tab "
                + "shows which ones have a step at all."
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            color: Color.muted
          }
        }
      }
    }

    RowLayout {
      Layout.topMargin: Style.space(6)
      spacing: Style.space(8)
      Button { text: "Edit config"; onClicked: root.command("omavoi config path") }
      Button { text: "Restart daemon"; onClicked: root.command("systemctl --user restart omavoid") }
      Text {
        Layout.fillWidth: true
        text: "everything here is  ~/.config/omavoi/config.toml"
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        color: Color.muted
      }
    }
  }
}
