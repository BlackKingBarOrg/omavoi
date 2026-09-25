import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import qs.Ui

// A mode is a chain of models, so it is edited as one: the speech step and
// what it is told, the deterministic rules, then zero or more LLM passes each
// with its own prompt, then how the text gets into the window.
//
// On screen the chain is split in two. What changes how a mode reads — the
// language, the cleanup you would notice, the AI steps — is always open.
// What the defaults already get right — the voice model, the recognition
// hint, the rules nobody turns off, how the text is typed — folds away under
// Advanced, and the closed fold names anything moved off its default, so a
// changed setting is never out of sight.
//
// Everything here writes through the omavoi command, so the console and the
// terminal cannot drift apart — the config file is the single record.
Item {
  id: root
  property var payload: ({ modes: [], active: "", llm: [] })
  property string selected: ""
  readonly property int pad: Style.space(18)
  // One column for the label of every labelled row, and one measure for
  // prose. The notes ran the full width of the pane — 190 characters a line
  // on a wide monitor — and the prompt boxes with them.
  readonly property int labelWidth: Style.space(150)
  readonly property int noteWidth: Style.space(680)
  readonly property int columnWidth: Style.space(880)

  property var strings: null
  // `omavoi model list --json`: what is on disk, and which llm entries exist.
  property var catalogue: ({ models: [], llm: [] })

  // Only what is downloaded — a mode changes the model, never the engine.
  // The format test that used to be here chose between ggml and ct2, and
  // ct2 was the faster-whisper engine's; there is one local format now.
  readonly property var speechChoices: (catalogue.models || []).filter(function (m) {
    return m.kind === "speech" && m.downloaded && m.fmt === "ggml"
  })
  // A catalogue key without its format prefix. `ggml:large-v3-turbo` is how
  // the CLI names the file and what is written to the config; the half after
  // the colon is the part someone is choosing between, and `ggml` is a file
  // format nobody picks a model by. The LLM rows below already did this.
  function plain(key) {
    return String(key || "").replace("ggml:", "").replace("llm:", "")
  }
  // Which model the global setting points at, so the chip that means "no
  // override" can name it rather than only say that it follows something.
  readonly property string defaultSpeech: {
    var all = catalogue.models || []
    for (var i = 0; i < all.length; i++)
      if (all[i].kind === "speech" && all[i].active === true)
        return root.plain(all[i].key)
    return ""
  }
  // `withModel` is false wherever a weights row sits directly underneath: the
  // model shown here comes from the *configuration*, so a step pinned to
  // other weights was labelled with the ones it is not going to run — the
  // same fault as reporting the config file instead of the live binding, at a
  // smaller scale. Below the picker the kind is all this chip has to say.
  function llmLabel(name, withModel) {
    var kind = name === "agent" ? root.t("models.k.agent")
             : name === "api" ? root.t("models.k.api")
             : name === "local" ? root.t("models.k.local")
             : name
    var m = root.llmModelOf(name)
    // The model only where it is a choice: the local weights, or an endpoint
    // whose model the user set. An agent uses its own default.
    if (withModel !== false && m !== "" && name !== "agent")
      return kind + "  " + root.plain(m)
    return kind
  }
  // Weights a step can be pointed at: the LLM catalogue, downloaded only. A
  // mode changes the model, never the engine — the same rule the speech list
  // above follows.
  readonly property var weightChoices: (catalogue.models || []).filter(function (m) {
    return m.kind === "llm" && m.downloaded
  })
  // Only one of the three configurations runs weights from the catalogue. An
  // agent brings its own model and an endpoint's is set where the endpoint
  // is, so offering a choice there would write a value nothing reads.
  function isLocalLlm(name) {
    var l = catalogue.llm || []
    for (var i = 0; i < l.length; i++)
      if (l[i].name === name)
        return ["llama-local", "llama.cpp", "llamacpp"]
                 .indexOf(String(l[i].backend || "")) >= 0
    return false
  }
  function llmModelOf(name) {
    var l = catalogue.llm || []
    for (var i = 0; i < l.length; i++)
      if (l[i].name === name) return String(l[i].model || "")
    return ""
  }
  // The mode a click just refused to enter, so the reason appears next to the
  // mode rather than only in a log the user will never open.
  property string blocked: ""
  // Advanced stays open across modes once opened: it is a way of looking at
  // the page, not a property of one mode.
  property bool advancedOpen: false
  // "+ add a rewrite step" has asked which LLM. A pick, Cancel or another
  // mode closes the question.
  property bool adding: false
  onCurrentChanged: root.adding = false

  signal command(string cmd)
  signal commandArgs(var argv)

  // `strings` is null for the instant between creation and the Loader setting
  // it, so the key stands in until then rather than a blank.
  function t(k) { return root.strings ? root.strings.t(k) : k }
  function tf(k, a) { return root.strings ? root.strings.tf(k, a) : k }

  readonly property var modes: payload.modes || []
  // Window matching is hidden for now. It wants tuning per application before
  // it earns its keep, and until then every surface it owns is a control that
  // is configured and inert — worse than no control, because it invites you
  // to set it and then quietly does nothing with it.
  //
  // Nothing behind the UI is touched: `mode.match` still lives in the config,
  // `omavoi mode match/unmatch/auto` still work, and the daemon still follows
  // the focused window if it was switched on. This is the whole switch.
  readonly property bool showWindowMatch: false

  readonly property var switching: payload.switching || ({ by_window: false, mode: "default" })
  readonly property bool byWindow: switching.by_window === true
  readonly property var llms: payload.llm || []
  readonly property string current: {
    for (var i = 0; i < modes.length; i++) if (modes[i].name === selected) return selected
    return payload.active || (modes.length ? modes[0].name : "")
  }
  readonly property var mode: {
    for (var i = 0; i < modes.length; i++) if (modes[i].name === current) return modes[i]
    return null
  }
  readonly property var rules: (root.mode && root.mode.rules) || ({})
  readonly property string language: (root.mode && root.mode.language) || "auto"
  readonly property string inject: (root.mode && root.mode.inject) || "auto"

  // Which Chinese characters come out is its own setting where the daemon
  // has it, and only asked where a take can carry Chinese at all: on auto,
  // or listening for Chinese or Cantonese. A mode pinned to Thai keeps the
  // value and does not show a question it cannot use.
  readonly property bool scriptShown: root.payload.script_supported === true
                                      && ["auto", "zh", "yue"].indexOf(root.language) >= 0

  // My dictionary, for this mode. Two flags before the dictionary was one
  // list — corrections and names — and a config from then may still have
  // one on and the other off, which the chip reports rather than flattens.
  readonly property bool dictCorrections: root.rules.vocabulary !== undefined
                                          ? root.rules.vocabulary
                                          : root.rules.dictionary !== false
                                            && root.payload.post_enabled !== false
  readonly property bool dictNames: root.rules.vocabulary !== undefined
                                    ? root.rules.vocabulary : root.rules.names !== false
  readonly property bool dictOn: root.dictCorrections && root.dictNames

  function injectLabel(how) {
    return how === "wtype" ? root.t("modes.inject.type")
         : how === "clipboard" ? root.t("modes.inject.clipboard")
         : how === "auto" ? root.t("modes.inject.auto")
         : how
  }
  function languageLabel(m, code) {
    var opts = (m && m.input_languages) || []
    for (var i = 0; i < opts.length; i++) if (opts[i].value === code) return opts[i].label
    return code
  }

  // What sets a mode apart, for the list. The line under each name used to
  // be the chain, "speech → System agent": every mode starts with speech, so
  // it said nothing, and code and terminal read the same as default though
  // one pastes and the other drops the full stop.
  //
  // Apart from default, that is. The other modes inherit what they do not
  // state, so default's Simplified Chinese on every line would be default's
  // trait printed five times; each line keeps only where its mode differs.
  // Steps are not inherited and always count.
  function summaryOf(m) {
    if (!m) return ""
    var base = null
    for (var b = 0; b < root.modes.length; b++)
      if (root.modes[b].name === "default") base = root.modes[b]
    function own(value, key) {
      return m.name === "default" || !base || value !== String(base[key] || "")
    }
    var parts = []
    var steps = m.steps || []
    if (steps.length) {
      var names = []
      for (var i = 0; i < steps.length; i++)
        names.push(root.llmLabel(steps[i].llm, false))
      parts.push(root.tf("modes.sum.ai", names.join(" → ")))
    }
    var lang = m.language || "auto"
    if (lang !== "auto" && own(lang, "language")) parts.push(root.languageLabel(m, lang))
    // Only where a take can carry Chinese, as the row that sets it.
    var script = ["auto", "zh", "yue"].indexOf(lang) >= 0 ? String(m.script || "") : ""
    if (script !== "" && own(script, "script"))
      parts.push(root.t(script === "zh-Hant" ? "modes.sum.hant" : "modes.sum.hans"))
    var punct = String((m.rules || {}).punctuation || "keep")
    if (punct === "strip" && (m.name === "default" || !base
                              || punct !== String((base.rules || {}).punctuation || "keep")))
      parts.push(root.t("modes.sum.nopunct"))
    var how = m.inject || "auto"
    if (how !== "auto" && own(how, "inject"))
      parts.push(root.t(how === "wtype" ? "modes.sum.type" : "modes.sum.paste"))
    return parts.length ? parts.join(" · ") : root.t("modes.sum.plain")
  }

  // The advanced settings this mode has moved off their defaults, for the
  // closed fold. Folding a setting away is only safe while a changed one
  // still shows: code pastes and terminal sends default's hint, and a
  // closed section would otherwise hide both.
  function advancedChanges() {
    var m = root.mode
    if (!m) return []
    function kv(k, v) { return root.t("modes.adv.kv").replace("%1", k).replace("%2", v) }
    var out = []
    if (m.speech_model) out.push(kv(root.t("modes.speechmodel"), root.plain(m.speech_model)))
    if (m.prompt) out.push(root.t("modes.decoderhint"))
    if (root.rules.hallucinations === false)
      out.push(kv(root.t("modes.r.hallucinations"), root.t("set.off")))
    if (root.payload.vocabulary_supported === true && !root.dictOn)
      out.push(kv(root.t("word.use"), root.dictCorrections !== root.dictNames
                                      ? root.t("word.partial") : root.t("set.off")))
    if (root.inject !== "auto") out.push(kv(root.t("modes.s4"), root.injectLabel(root.inject)))
    return out
  }

  RowLayout {
    anchors.fill: parent
    spacing: 0

    // ===================== list =====================
    Rectangle {
      Layout.preferredWidth: Style.space(280)
      Layout.fillHeight: true
      color: Qt.darker(Color.popups.background, 1.05)

      ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // How the mode gets picked at all, and the switch for it.
        //
        // The matching controls are hidden until they are finished, and the
        // switch was one of them -- so a machine left following the window
        // had a mode list whose clicks did nothing, a line of orange text
        // saying so, and no way back except `omavoi mode auto off` at a
        // terminal. The switch is the one part of that UI that works without
        // the rest: the match lists are already in the config whether or not
        // they can be edited here.
        //
        // Above the list, because "which of these two is deciding" is the
        // question a mode list cannot answer on its own. It sat above the
        // detail pane first, where it read as a setting of whichever mode was
        // open, and as a chip whose label was its own state.
        ColumnLayout {
          Layout.fillWidth: true
          Layout.margins: Style.space(11)
          spacing: Style.space(6)
          OmText {
            text: root.t("modes.pick.title")
            color: Color.muted
          }
          ButtonGroup {
            objectName: "switching"
            options: [{ value: "fixed", label: root.t("modes.fixed") },
                      { value: "window", label: root.t("modes.following") }]
            value: root.byWindow ? "window" : "fixed"
            fontSize: Style.font.caption
            onChanged: function (v) {
              root.commandArgs(["omavoi", "mode", "auto", v === "window" ? "on" : "off"])
            }
          }
          OmText {
            visible: root.byWindow
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: root.t("modes.hiddenauto")
            color: "#e0af68"
          }
        }

        Rectangle {
          Layout.fillWidth: true
          Layout.preferredHeight: 1
          color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.12)
        }

        ListView {
          Layout.fillWidth: true
          Layout.fillHeight: true
          clip: true
          model: root.modes
          delegate: Rectangle {
            readonly property var m: modelData
            width: ListView.view.width
            height: entry.implicitHeight + Style.space(18)
            color: m.name === root.current
                   ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.12)
                   : "transparent"

            Rectangle {
              width: 2; height: parent.height
              color: m.name === root.current ? Color.accent : "transparent"
            }

            ColumnLayout {
              id: entry
              anchors.left: parent.left
              anchors.right: parent.right
              anchors.verticalCenter: parent.verticalCenter
              anchors.leftMargin: Style.space(13)
              anchors.rightMargin: Style.space(11)
              spacing: 2

              RowLayout {
                Layout.fillWidth: true
                OmText {
                  text: m.name
                  size: "body"
                  color: Color.foreground
                }
                Item { Layout.fillWidth: true }
                OmText {
                  visible: m.active === true
                  text: root.t("modes.here")
                  color: Color.accent
                }
              }
              OmText {
                Layout.fillWidth: true
                elide: Text.ElideRight
                text: root.summaryOf(m)
                color: (m.steps || []).length ? Color.accent : Color.muted
              }
              OmText {
                visible: root.showWindowMatch
                Layout.fillWidth: true
                elide: Text.ElideRight
                text: (m.match || []).join(", ") || root.t("modes.fallback")
                color: Qt.darker(Color.muted, 1.1)
              }
              // A mode that cannot load its model is not a mode you can be in.
              OmText {
                visible: m.vram_known === true && m.fits === false
                Layout.fillWidth: true
                elide: Text.ElideRight
                text: root.tf("modes.wontfit", (m.needs_mb / 1024).toFixed(1) + "G")
                color: Color.urgent
              }
            }
            MouseArea {
              anchors.fill: parent
              cursorShape: Qt.PointingHandCursor
              // Clicking a mode uses it, not merely opens it for editing.
              // Selecting-without-switching is what a list of modes looks
              // like it does least, and switching is instant and reversible.
              // With window matching on there is nothing to switch, so a
              // click only selects.
              onClicked: {
                // Selecting always works — you need to open a mode to fix the
                // step that does not fit. Only entering it is refused, and the
                // CLI refuses the same switch for the same reason.
                root.selected = m.name
                if (m.vram_known === true && m.fits === false) {
                  root.blocked = m.name
                  return
                }
                root.blocked = ""
                if (!root.byWindow && (root.switching.mode || "default") !== m.name)
                  root.commandArgs(["omavoi", "mode", "use", m.name])
              }
            }
          }
        }

        // -- new mode --
        RowLayout {
          Layout.fillWidth: true
          Layout.margins: Style.space(11)
          spacing: Style.space(7)
          TextField {
            id: newName
            Layout.fillWidth: true
            placeholderText: root.t("modes.newname")
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            onAccepted: makeMode.click()
          }
          Button {
            id: makeMode
            text: "+"
            function click() {
              var name = newName.text.trim()
              if (!name) return
              // Copied from the current mode: a new mode that starts empty
              // has no rules and silently behaves unlike every other one.
              root.commandArgs(["omavoi", "mode", "new", name, root.current])
              root.selected = name
              newName.text = ""
            }
            onClicked: click()
          }
        }
      }
    }

    Rectangle {
      Layout.preferredWidth: 1
      Layout.fillHeight: true
      color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.18)
    }

    // ===================== detail =====================
    //
    // Four sizes, one job each: the mode's name, a section's title, a row's
    // label, and everything a row holds or says about itself. Every one of
    // those was `caption` before, the name aside — which is why a section's
    // title and the note beside it read as one string — and the section
    // numbers were three colours, left over from a design that drew each
    // step as a card and coloured the two that run a model.
    Flickable {
      id: pane
      Layout.fillWidth: true
      Layout.fillHeight: true
      clip: true
      contentHeight: detail.implicitHeight + root.pad * 2
      visible: root.mode !== null

      ColumnLayout {
        id: detail
        x: root.pad
        y: root.pad
        width: Math.min(pane.width - root.pad * 2, root.columnWidth)
        spacing: Style.space(20)

        // -- header --
        RowLayout {
          Layout.fillWidth: true
          spacing: Style.space(10)
          OmText {
            text: root.current
            size: "heading"
            color: Color.foreground
          }
          OmText {
            visible: root.mode && root.mode.active === true
            text: root.t("modes.here")
            color: Color.accent
          }
          OmText {
            visible: root.blocked !== "" && root.blocked === root.current
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: root.t("modes.blocked")
            color: Color.urgent
          }
          Item { Layout.fillWidth: true }
          Button {
            visible: root.current !== "default"
            text: root.t("modes.delete")
            onClicked: root.commandArgs(["omavoi", "mode", "rm", root.current])
          }
        }

        // What window matching would say about the mode, once it is shown.
        // The switch itself lives above the list.
        Rectangle {
          visible: root.showWindowMatch
          Layout.fillWidth: true
          implicitHeight: pick.implicitHeight + Style.space(18)
          color: root.byWindow
                 ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.07)
                 : "transparent"
          border.width: 1
          border.color: root.byWindow
                        ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.6)
                        : Qt.rgba(Color.foreground.r, Color.foreground.g,
                                  Color.foreground.b, 0.25)
          radius: Style.cornerRadius

          ColumnLayout {
            id: pick
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.margins: Style.space(12)
            spacing: 2
            OmText {
              text: root.byWindow
                    ? root.t("modes.followwin")
                    : root.t("modes.everytake") + (root.switching.mode || "default")
              size: "body"
              color: Color.foreground
            }
            OmText {
              Layout.fillWidth: true
              wrapMode: Text.Wrap
              text: root.byWindow ? root.t("modes.longestwins")
                                  : root.t("modes.matchoff")
              color: Color.muted
            }
          }
        }

        // -- triggers --
        ColumnLayout {
          visible: root.showWindowMatch
          Layout.fillWidth: true
          spacing: Style.space(6)
          opacity: root.byWindow ? 1 : 0.5
          RowLayout {
            spacing: Style.space(8)
            OmText {
              text: root.t("modes.opens")
              font.letterSpacing: 1
              color: Color.muted
            }
            OmText {
              visible: !root.byWindow
              text: root.t("modes.notinuse")
              color: Qt.darker(Color.muted, 1.1)
            }
          }
          Flow {
            Layout.fillWidth: true
            spacing: Style.space(6)
            Repeater {
              model: (root.mode && root.mode.match) || []
              OmChip {
                readonly property string token: modelData
                label: token + "  ×"
                on: true
                onClicked: root.commandArgs(["omavoi", "mode", "unmatch", root.current, token])
              }
            }
            OmText {
              visible: !((root.mode && root.mode.match) || []).length
              text: root.t("modes.nothing")
              color: Color.muted
            }
          }
          RowLayout {
            Layout.fillWidth: true
            spacing: Style.space(7)
            TextField {
              id: newMatch
              Layout.preferredWidth: Style.space(280)
              placeholderText: root.t("modes.classph")
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              onAccepted: addMatch.click()
            }
            Button {
              id: addMatch
              text: root.t("modes.add")
              function click() {
                var t = newMatch.text.trim()
                if (!t) return
                root.commandArgs(["omavoi", "mode", "match", root.current, t])
                newMatch.text = ""
              }
              onClicked: click()
            }
            OmText {
              Layout.fillWidth: true
              wrapMode: Text.Wrap
              text: root.t("modes.matchhint")
              color: Qt.darker(Color.muted, 1.1)
            }
          }
        }

        // ---- voice ------------------------------------------------------
        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(10)
          Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            Layout.bottomMargin: Style.space(8)
            color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.12)
          }
          OmText {
            text: root.t("modes.s1")
            size: "subtitle"
            font.letterSpacing: 1
            color: Color.foreground
          }
          RowLayout {
            Layout.fillWidth: true
            spacing: Style.space(10)
            OmText {
              Layout.preferredWidth: root.labelWidth
              wrapMode: Text.Wrap
              text: root.t("modes.language")
              size: "body"
              color: Color.muted
            }
            SearchableDropdown {
              id: inputLanguagePicker
              objectName: "inputLanguagePicker"
              Layout.alignment: Qt.AlignLeft
              Layout.preferredWidth: Style.space(280)
              // Bound to the column, not a RowLayout's implicit width: this
              // also keeps the popup inside the detail pane on narrow windows.
              Layout.maximumWidth: Math.max(Style.space(120), Math.min(Style.space(280),
                                     detail.width - root.labelWidth - Style.space(10)))
              // The row has the label; the picker's own sat above it in bold
              // and title case, the one label on the page that looked like it.
              showLabel: false
              popupRowHeight: Style.space(40)
              // The shell picker writes value on selection. Binding keeps
              // external refreshes and mode switches connected afterwards.
              Binding on value { value: root.language }
              options: root.mode && root.mode.input_languages ? root.mode.input_languages : []
              enabled: options.length > 0
              placeholderText: root.t("modes.langsearch")
              triggerLabel: root.t("modes.langauto")
              emptyText: root.t("modes.langempty")
              onChanged: function(code) {
                if (root.mode && code !== root.language)
                  root.commandArgs(["omavoi", "mode", "set", root.current, "language", code])
              }
            }
            Item { Layout.fillWidth: true }
          }
          // Said only when it is true of the choice: auto needs no note, and
          // one pinned language has a cost worth knowing before a take in
          // another one comes out wrong.
          OmText {
            visible: text !== ""
            Layout.leftMargin: root.labelWidth + Style.space(10)
            Layout.fillWidth: true
            Layout.maximumWidth: root.noteWidth
            wrapMode: Text.Wrap
            text: !inputLanguagePicker.enabled ? root.t("modes.langupgrade")
                  : root.language !== "auto" ? root.t("modes.langfixed") : ""
            color: Qt.darker(Color.muted, 1.1)
          }
          RowLayout {
            objectName: "scriptRow"
            visible: root.scriptShown
            Layout.fillWidth: true
            spacing: Style.space(10)
            OmText {
              Layout.preferredWidth: root.labelWidth
              wrapMode: Text.Wrap
              text: root.t("modes.script")
              size: "body"
              color: Color.muted
            }
            Flow {
              Layout.fillWidth: true
              spacing: Style.space(6)
              Repeater {
                model: [{ v: "", k: "modes.script.none" },
                        { v: "zh-Hans", k: "modes.script.hans" },
                        { v: "zh-Hant", k: "modes.script.hant" }]
                OmChip {
                  readonly property var choice: modelData
                  objectName: "script:" + choice.v
                  label: root.t(choice.k)
                  on: ((root.mode && root.mode.script) || "") === choice.v
                  onClicked: if (!on) root.commandArgs(
                    ["omavoi", "mode", "set", root.current, "script", choice.v])
                }
              }
            }
          }
        }

        // ---- cleanup ----------------------------------------------------
        //
        // Every chip is a thing that happens when it is lit. "keep end
        // punctuation" was the one lit for not doing something, in a row
        // where the others lit for doing it.
        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(10)
          Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            Layout.bottomMargin: Style.space(8)
            color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.12)
          }
          ColumnLayout {
            spacing: Style.space(3)
            OmText {
              text: root.t("modes.s2")
              size: "subtitle"
              font.letterSpacing: 1
              color: Color.foreground
            }
            OmText {
              text: root.t("modes.rulessub")
              color: Color.muted
            }
          }
          Flow {
            Layout.fillWidth: true
            spacing: Style.space(6)
            Repeater {
              model: [
                { k: "fillers", label: root.t("modes.r.fillers") },
                { k: "cjk_spacing", label: root.t("modes.r.cjk") }
              ]
              OmChip {
                readonly property var rule: modelData
                label: rule.label
                on: root.rules[rule.k] !== false
                onClicked: root.commandArgs(
                  ["omavoi", "config", "set",
                   "modes." + root.current + ".rules." + rule.k,
                   on ? "false" : "true"])
              }
            }
            OmChip {
              label: root.t("modes.droppunct")
              on: root.rules.punctuation === "strip"
              onClicked: root.commandArgs(
                ["omavoi", "config", "set",
                 "modes." + root.current + ".rules.punctuation",
                 on ? "keep" : "strip"])
            }
          }
        }

        // ---- ai rewrite -------------------------------------------------
        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(10)
          Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            Layout.bottomMargin: Style.space(8)
            color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.12)
          }
          ColumnLayout {
            spacing: Style.space(3)
            OmText {
              text: root.t("modes.s3")
              size: "subtitle"
              font.letterSpacing: 1
              color: Color.foreground
            }
            OmText {
              Layout.fillWidth: true
              Layout.maximumWidth: root.noteWidth
              wrapMode: Text.Wrap
              text: root.t("modes.llmsub")
              color: Color.muted
            }
          }

          Repeater {
            model: (root.mode && root.mode.steps) || []
            Rectangle {
              readonly property var step: modelData
              readonly property int idx: index
              Layout.fillWidth: true
              implicitHeight: stepBody.implicitHeight + Style.space(18)
              color: "transparent"
              border.width: 1
              border.color: Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.55)
              radius: Style.cornerRadius

              ColumnLayout {
                id: stepBody
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Style.space(10)
                spacing: Style.space(6)

                RowLayout {
                  Layout.fillWidth: true
                  spacing: Style.space(7)
                  OmText {
                    text: root.t("modes.step") + (idx + 1)
                          + root.t("modes.stepsuffix")
                    color: Color.muted
                  }
                  Repeater {
                    model: root.llms
                    OmChip {
                      readonly property string llmName: modelData
                      label: root.llmLabel(llmName, !root.isLocalLlm(llmName))
                      on: llmName === step.llm
                      onClicked: if (!on) root.commandArgs(
                        ["omavoi", "mode", "step", root.current, "llm",
                         String(idx), llmName])
                    }
                  }
                  Item { Layout.fillWidth: true }
                  Button {
                    text: root.t("modes.remove")
                    onClicked: root.commandArgs(
                      ["omavoi", "mode", "step", root.current, "rm", String(idx)])
                  }
                }

                // Which weights this step runs. Downloading a model made it
                // appear in the Models tab and nowhere else: a step named a
                // configuration and inherited whatever that configuration
                // pointed at, so a second local model had no way of being
                // reached from a mode at all. It stays in the card rather
                // than under Advanced: it is only here for a local step, and
                // it is a question about this step.
                RowLayout {
                  visible: root.isLocalLlm(step.llm)
                           && root.weightChoices.length > 0
                  Layout.fillWidth: true
                  spacing: Style.space(7)
                  OmText {
                    text: root.t("modes.weights")
                    color: Color.muted
                  }
                  // Inherit is the absence of an override, and it says what
                  // it will follow rather than only that it follows.
                  OmChip {
                    label: root.tf("modes.inherit",
                                   root.plain(root.llmModelOf(step.llm)))
                    on: String(step.model || "") === ""
                    onClicked: if (!on) root.commandArgs(
                      ["omavoi", "mode", "step", root.current, "model",
                       String(idx), ""])
                  }
                  Repeater {
                    model: root.weightChoices
                    OmChip {
                      readonly property string wkey: modelData.key
                      label: root.plain(wkey)
                      on: String(step.model || "") === wkey
                      onClicked: if (!on) root.commandArgs(
                        ["omavoi", "mode", "step", root.current, "model",
                         String(idx), wkey])
                    }
                  }
                  Item { Layout.fillWidth: true }
                }

                OmTextArea {
                  Layout.fillWidth: true
                  strings: root.strings
                  minLines: 3
                  key: root.current + "#" + idx
                  text: step.prompt || ""
                  placeholder: root.t("modes.stepph")
                  onCommitted: function (v) {
                    root.commandArgs(["omavoi", "mode", "step", root.current,
                                      "prompt", String(idx), v])
                  }
                }
              }
            }
          }

          // An action, and drawn as one. It was a row of chips under a row of
          // chips: the same three names, the same shape, a hundred pixels
          // below the ones that choose a step's LLM — and a click on the
          // wrong row added a step, prompt and all.
          RowLayout {
            visible: root.llms.length > 0
            Layout.fillWidth: true
            spacing: Style.space(8)
            Button {
              objectName: "addStep"
              visible: !root.adding
              text: root.t("modes.addstep")
              bordered: true
              fontSize: Style.font.caption
              onClicked: root.adding = true
            }
            OmText {
              visible: root.adding
              text: root.t("modes.addwhich")
              color: Color.muted
            }
            Repeater {
              model: root.adding ? root.llms : []
              Button {
                readonly property string llmName: modelData
                objectName: "addStep:" + llmName
                text: root.llmLabel(llmName)
                bordered: true
                fontSize: Style.font.caption
                // No prompt here: the command fills its default, so the text
                // lives in one place instead of drifting between the two.
                // Closing the question comes last: it empties this Repeater,
                // and this button with it, handler and all.
                onClicked: {
                  root.commandArgs(["omavoi", "mode", "step", root.current, "add", llmName])
                  root.adding = false
                }
              }
            }
            Button {
              visible: root.adding
              text: root.t("word.cancel")
              fontSize: Style.font.caption
              onClicked: root.adding = false
            }
            Item { Layout.fillWidth: true }
          }
          OmText {
            visible: !root.llms.length
            text: root.t("modes.nollm")
            color: Color.muted
          }
        }

        // ---- advanced ---------------------------------------------------
        ColumnLayout {
          Layout.fillWidth: true
          spacing: Style.space(12)
          Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            Layout.bottomMargin: Style.space(6)
            color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.12)
          }
          Item {
            id: advHead
            Layout.fillWidth: true
            implicitHeight: advTitle.implicitHeight
            readonly property var changes: root.advancedChanges()
            RowLayout {
              id: advTitle
              width: parent.width
              spacing: Style.space(12)
              // The shell's own chevrons, the ones its dropdowns draw.
              OmText {
                text: root.advancedOpen ? "󰅀" : "󰅂"
                size: "subtitle"
                color: Color.muted
              }
              OmText {
                text: root.t("modes.adv")
                size: "subtitle"
                font.letterSpacing: 1
                color: Color.foreground
              }
              OmText {
                objectName: "advancedSummary"
                visible: !root.advancedOpen && advHead.changes.length > 0
                Layout.fillWidth: true
                elide: Text.ElideRight
                text: root.tf("modes.adv.changed", advHead.changes.join(root.t("modes.adv.sep")))
                color: Color.accent
              }
              Item { Layout.fillWidth: true }
            }
            MouseArea {
              anchors.fill: parent
              cursorShape: Qt.PointingHandCursor
              onClicked: root.advancedOpen = !root.advancedOpen
            }
          }

          ColumnLayout {
            objectName: "advancedBody"
            visible: root.advancedOpen
            Layout.fillWidth: true
            spacing: Style.space(12)

            // A mode names its own weights, or takes whatever is loaded. The
            // switch costs one reload — measured at 3.7 s for large-v3 — and
            // it is paid when the mode changes, not when you dictate.
            ColumnLayout {
              Layout.fillWidth: true
              spacing: Style.space(6)
              RowLayout {
                Layout.fillWidth: true
                spacing: Style.space(10)
                OmText {
                  Layout.preferredWidth: root.labelWidth
                  Layout.alignment: Qt.AlignTop
                  wrapMode: Text.Wrap
                  text: root.t("modes.speechmodel")
                  size: "body"
                  color: Color.muted
                }
                Flow {
                  Layout.fillWidth: true
                  spacing: Style.space(6)
                  // The absence of an override, saying what it will follow —
                  // the same shape as the LLM step's inherit chip, which had
                  // it first. "whatever is loaded" named no model at all.
                  OmChip {
                    label: root.defaultSpeech === ""
                           ? root.t("modes.speechglobal")
                           : root.tf("modes.speechglobalnamed", root.defaultSpeech)
                    on: !(root.mode && root.mode.speech_model)
                    onClicked: root.commandArgs(
                      ["omavoi", "mode", "set", root.current, "speech_model", ""])
                  }
                  // Not the default's own weights beside the chip that
                  // already names them — "use the default (large-v3-turbo)"
                  // next to "large-v3-turbo" read as one model twice. It
                  // stays for a mode that pinned them.
                  Repeater {
                    model: root.speechChoices
                    OmChip {
                      readonly property var entry: modelData
                      visible: on || root.plain(entry.key) !== root.defaultSpeech
                      label: root.plain(entry.key)
                      on: root.mode && String(root.mode.speech_model) === String(entry.key)
                      onClicked: root.commandArgs(
                        ["omavoi", "mode", "set", root.current, "speech_model", entry.key])
                    }
                  }
                }
              }
              // Two different facts, and `<= 1` reported the first one for
              // both: "only one set is downloaded" over a machine with none.
              // The third is what choosing one costs.
              OmText {
                visible: text !== ""
                Layout.leftMargin: root.labelWidth + Style.space(10)
                Layout.fillWidth: true
                Layout.maximumWidth: root.noteWidth
                wrapMode: Text.Wrap
                text: root.speechChoices.length === 0 ? root.t("modes.speechnone")
                      : root.mode && root.mode.speech_model
                        && root.plain(root.mode.speech_model) !== root.defaultSpeech
                        ? root.t("modes.speechreload")
                      : root.speechChoices.length === 1 ? root.t("modes.speechonly1")
                      : ""
                color: Qt.darker(Color.muted, 1.1)
              }
            }

            // The decoder prompt. A mode that states none sends default's,
            // and said so nowhere: terminal, code and prose showed an empty
            // box over a hint they were sending with every take.
            ColumnLayout {
              Layout.fillWidth: true
              spacing: Style.space(6)
              RowLayout {
                Layout.fillWidth: true
                spacing: Style.space(10)
                OmText {
                  Layout.preferredWidth: root.labelWidth
                  Layout.alignment: Qt.AlignTop
                  Layout.topMargin: Style.space(6)
                  wrapMode: Text.Wrap
                  text: root.t("modes.decoderhint")
                  size: "body"
                  color: Color.muted
                }
                OmTextArea {
                  Layout.fillWidth: true
                  strings: root.strings
                  minLines: 2
                  key: root.current
                  text: (root.mode && root.mode.prompt) || ""
                  placeholder: root.t("modes.promptph")
                  onCommitted: function (v) {
                    root.commandArgs(["omavoi", "mode", "set", root.current, "prompt", v])
                  }
                }
              }
              OmText {
                Layout.leftMargin: root.labelWidth + Style.space(10)
                Layout.fillWidth: true
                Layout.maximumWidth: root.noteWidth
                wrapMode: Text.Wrap
                text: root.mode && root.mode.prompt_inherited === true
                      ? root.t("modes.promptinherited") : root.t("modes.prompthint")
                color: Qt.darker(Color.muted, 1.1)
              }
            }

            // The rules that stay on: what they catch only ever goes wrong.
            RowLayout {
              Layout.fillWidth: true
              spacing: Style.space(10)
              OmText {
                Layout.preferredWidth: root.labelWidth
                Layout.alignment: Qt.AlignTop
                wrapMode: Text.Wrap
                text: root.t("modes.adv.cleanup")
                size: "body"
                color: Color.muted
              }
              Flow {
                Layout.fillWidth: true
                spacing: Style.space(6)
                // Named for what the flag does. It was "made-up phrases", and
                // switching it off never kept one: a segment measured as
                // silence is dropped whatever it says. What the flag decides
                // is whether "好的。好的。好的。" collapses to one.
                OmChip {
                  label: root.t("modes.r.hallucinations")
                  on: root.rules.hallucinations !== false
                  onClicked: root.commandArgs(
                    ["omavoi", "config", "set",
                     "modes." + root.current + ".rules.hallucinations",
                     on ? "false" : "true"])
                }
                OmChip {
                  visible: root.payload.vocabulary_supported === true
                  label: root.t("word.use") + (root.dictCorrections !== root.dictNames
                                               ? " · " + root.t("word.partial") : "")
                  on: root.dictOn
                  onClicked: root.commandArgs(["omavoi", "mode", "set", root.current,
                                               "rules.vocabulary", root.dictOn ? "false" : "true"])
                }
                Repeater {
                  model: root.payload.vocabulary_supported ? [] : [
                    { k: "dictionary", label: root.t("modes.r.dictionary") },
                    { k: "names", label: root.t("modes.r.names") }
                  ]
                  OmChip {
                    readonly property var rule: modelData
                    label: rule.label
                    on: root.rules[rule.k] !== false
                    onClicked: root.commandArgs(["omavoi", "config", "set", "modes." + root.current + ".rules." + rule.k, on ? "false" : "true"])
                  }
                }
              }
            }

            // How the text reaches the window. Auto is right almost
            // everywhere, so the note describes whichever route is chosen:
            // what auto does, or what forcing one gives up.
            ColumnLayout {
              Layout.fillWidth: true
              spacing: Style.space(6)
              RowLayout {
                Layout.fillWidth: true
                spacing: Style.space(10)
                OmText {
                  Layout.preferredWidth: root.labelWidth
                  wrapMode: Text.Wrap
                  text: root.t("modes.s4")
                  size: "body"
                  color: Color.muted
                }
                Repeater {
                  model: ["auto", "wtype", "clipboard"]
                  OmChip {
                    readonly property string how: modelData
                    // The value written to the config is still `wtype`; the
                    // chip says what it does. A program name is the right
                    // word in a terminal and in the note below, and the wrong
                    // one on a choice between three things — nobody picks
                    // "wtype" over "clipboard" by knowing what wtype is.
                    label: root.injectLabel(how)
                    on: root.inject === how
                    onClicked: if (!on) root.commandArgs(
                      ["omavoi", "mode", "set", root.current, "inject", how])
                  }
                }
                Item { Layout.fillWidth: true }
              }
              OmText {
                visible: text !== ""
                Layout.leftMargin: root.labelWidth + Style.space(10)
                Layout.fillWidth: true
                Layout.maximumWidth: root.noteWidth
                wrapMode: Text.Wrap
                text: root.inject === "auto" ? root.t("modes.inject.hint.auto")
                      : root.inject === "wtype" ? root.t("modes.inject.hint.type")
                      : root.inject === "clipboard" ? root.t("modes.inject.hint.paste")
                      : ""
                color: Qt.darker(Color.muted, 1.1)
              }
            }
          }
        }
      }
    }
  }
}
