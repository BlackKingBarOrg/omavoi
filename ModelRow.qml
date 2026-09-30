import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Ui

// One row, both families.
//
// A speech entry and an LLM entry carry the same fifteen fields and mean the
// same things by them — key, size, note, tags, downloaded, ours, running,
// active, fits, needed_mb. The only reason the two tables looked different is
// that the row was written twice, and then drifted. So it is written once.
// `useCommand` is the single real difference: choosing a speech model writes
// the speech model, choosing LLM weights writes them into the local
// configuration.
//
// Two lines, not one. On one line the note had whatever the name, size,
// languages and actions left over, and every note in the catalogue arrived
// cut off mid-word — "Twice the do…", "The strongest Chin…" — though the note
// is the one thing a person choosing between two models reads (UX-03). The
// name and size are the first line, the note and the languages wrap under it.
RowLayout {
  id: row

  property var m: ({})
  property var strings: null
  // Keys with a download in flight, so the button can become a word.
  property var pulling: ({})
  property string useCommand: ""

  signal command(string cmd)

  function t(k) { return row.strings ? row.strings.t(k) : k }

  Layout.fillWidth: true
  Layout.topMargin: Style.space(4)
  spacing: Style.space(10)

  ColumnLayout {
    Layout.fillWidth: true
    spacing: Style.space(2)
    RowLayout {
      Layout.fillWidth: true
      spacing: Style.space(10)
      // The name a person chooses by. `ggml:` and `llm:` are the file format
      // and the family, which this table's own heading already says.
      OmText {
        text: String(m.key || "").replace("ggml:", "").replace("llm:", "")
        size: "body"
        color: Color.foreground
      }
      OmText {
        text: row.t("models.downloadsize") + " " + (m.size_mb / 1024).toFixed(1) + " GB"
        color: Color.muted
      }
      // Won't-fit is worth saying before the download, not after — and never
      // about the model that is loaded right now, whose own weights are most
      // of what the free-VRAM figure is missing.
      OmText {
        visible: m.fits === false && m.running !== true
        text: row.t("models.needs") + " " + (m.needed_mb / 1024).toFixed(1) + " GB"
        color: Color.urgent
      }
      OmText {
        visible: (m.tags || []).indexOf("recommended") >= 0
        text: row.t("models.recommended")
        color: Color.accent
      }
      Item { Layout.fillWidth: true }
    }
    OmText {
      Layout.fillWidth: true
      wrapMode: Text.Wrap
      text: m.note || ""
      color: (m.tags || []).indexOf("recommended") >= 0 ? Color.foreground
                                                        : Color.muted
    }
    // Which languages this one is any good at — the half someone comparing
    // two models needs, and the one that says the default speech model is a
    // distillation and is not even across languages.
    OmText {
      visible: String(m.languages || "") !== ""
      Layout.fillWidth: true
      wrapMode: Text.Wrap
      text: String(m.languages || "")
      color: Qt.darker(Color.muted, 1.15)
    }
  }

  RowLayout {
    Layout.alignment: Qt.AlignTop
    spacing: Style.space(7)
    OmText {
      visible: m.running === true || m.active === true || (m.downloaded && m.ours)
      text: row.t(m.running ? "models.running" : m.active ? "models.default" : "models.downloaded")
      color: Color.accent
    }
    // Found where another tool put it, and used where it lies rather than
    // downloaded again. True of either family.
    OmText {
      visible: m.downloaded && !m.ours && m.running !== true
      text: row.t("models.ondisk")
      color: Color.muted
    }
    // A three-gigabyte download used to say "downloading" and nothing else
    // until it finished, so a slow mirror and a stalled one looked alike.
    //
    // The percentage is capped below 100 for the last rounded mebibyte —
    // arriving at 100% while still going is worse than arriving at 99.
    // tools/check_catalogue.py measures the sizes it is computed from.
    OmText {
      visible: !m.downloaded && row.pulling[m.key] === true
      text: {
        var done = Number(m.bytes_now || 0)
        var total = Number(m.size_mb || 0) * 1048576
        if (done <= 0 || total <= 0) return row.t("models.downloading")
        return row.t("models.downloading") + "  "
               + (done / 1048576).toFixed(0) + " / " + Math.round(m.size_mb)
               + " MB  " + Math.min(99, Math.floor(100 * done / total)) + "%"
      }
      color: Color.accent
    }
    Button {
      visible: !m.downloaded && row.pulling[m.key] !== true
      text: row.t("models.download")
      bordered: true
      fontSize: Style.font.caption
      onClicked: row.command("omavoi model pull " + m.key)
    }
    Button {
      visible: m.downloaded && !m.active && row.useCommand !== ""
      text: row.t("models.use")
      bordered: true
      fontSize: Style.font.caption
      onClicked: row.command(row.useCommand)
    }
    // Never the weights something is pointing at, and never the ones a
    // server has open.
    Button {
      visible: m.downloaded && m.ours && !m.active && m.running !== true
      text: row.t("models.remove")
      foreground: Color.urgent
      fontSize: Style.font.caption
      onClicked: row.command("omavoi model rm " + m.key)
    }
  }
}
