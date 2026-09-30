#!/usr/bin/env python3
"""Exercise Models, History, Setup and First run against an isolated configuration.

Models: the engine cards and the Use buttons write through the CLI and the
view follows; the remote endpoint appears only with the remote engine; a
download, a removal or a restart is refused here and only recorded. History:
the right-click menu copies the take it was opened on and deletes by id, and
the details fold opens. Setup: no string key reaches the screen, and the daemon's detail lines are
put in the reader's language. First run:
the three answers make a plan that uses the chosen model's catalogue key.
Bar: the tooltips say how to press the key, not which engine is running.

The speech models already downloaded on this machine are linked in
read-only; nothing that could remove or fetch one is ever run.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ui_shots import takes  # noqa: E402  -- the same made-up takes the photographs use

QML = r'''import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Io
import qs.Commons
import "Plugin"
Window {
  id: window
  width: 1400; height: 1400; visible: true; color: Color.popups.background
  property int step: 0
  property int ticks: 0
  property bool busy: false
  property var queued: []
  property string failure: ""
  property var refused: []
  property var ran: []
  property var removed: []
  property var models: ({ models: [] })
  property var hist: []
  property bool ready: false
  Strings { id: tr; lang: __LANG__ }

  function run(argv) {
    var text = argv.join(" ")
    // Only what writes the isolated config; nothing that fetches, deletes or
    // restarts anything real.
    if (!/omavoi (config set|model use) /.test(text) || /model (pull|rm)|systemctl/.test(text)) {
      window.refused.push(text); return
    }
    window.busy = true
    writer.command = argv
    writer.running = true
  }
  Process {
    id: writer
    stderr: StdioCollector { id: writeErr }
    onExited: function(code, status) {
      if (code) window.failure = "write failed: " + JSON.stringify(writer.command) + " " + writeErr.text
      if (window.queued.length) { var next = window.queued[0]; window.queued = window.queued.slice(1); writer.command = next; nextWrite.restart() }
      else modelsProc.running = true
    }
  }
  Timer { id: nextWrite; interval: 0; onTriggered: writer.running = true }
  Process {
    id: modelsProc; command: [__CLI__, "model", "list", "--json"]; running: true
    stdout: StdioCollector { onStreamFinished: { window.models = JSON.parse(text); window.busy = false; window.ready = true } }
  }
  Process {
    id: histProc; command: [__CLI__, "history", "-n", "40", "--json"]; running: true
    stdout: StdioCollector { onStreamFinished: window.hist = JSON.parse(text).reverse() }
  }

  ModelsView {
    id: modelsView; visible: window.step < 20; width: 1400; height: 1400
    strings: tr; payload: window.models; pulling: ({})
    onCommand: function(cmd) { window.run(["sh", "-c", cmd]) }
    onCommandArgs: function(argv) { window.run(argv) }
    onCommandBatch: function(commands) { window.queued = commands.slice(1); window.run(commands[0]) }
  }
  HistoryView {
    id: historyView; visible: false; width: 1400; height: 900
    strings: tr; takes: window.hist; selected: 0
    onRunArgs: function(argv) { window.ran.push(argv) }
    onRemove: function(id) { window.removed.push(id) }
  }
  SetupView {
    id: setupView; visible: false; width: 1400; height: 1200; strings: tr
    setupReport: ({ ready: false, done: 1, total: 3, steps: [
      { key: "model", title: "Model weights (ggml:large-v3-turbo)", done: true, detail: "/x", command: "", needs_root: false, optional: false, note: "" },
      { key: "llm-engine", title: "LLM engine (llama.cpp)", done: false, detail: "llama-server is not installed, needed by local", command: "sudo pacman -S --needed llama-cpp", needs_root: true, optional: true, note: "About 7 MB." },
      { key: "hotkey", title: "Hotkey (RIGHTCTRL via evdev)", done: false, detail: "not in the input group", command: "sudo usermod -aG input $USER", needs_root: true, optional: true, note: "" } ] })
    rootPlan: [{ key: "packages", root: true, label: tr.t("first.step.packages"), argv: ["pkexec", "/usr/bin/pacman", "-S", "llama-cpp"] }]
  }
  FirstRun { id: firstRun; visible: false; width: 1400; height: 1200; strings: tr; daemonPresent: false; foundWeights: "" }
  BarWidget { id: barWidget; visible: false; width: 120; height: 30 }
  // The widget's own IpcLink, found by what only it has; its fields are set
  // by hand below, and the socket it looks for is in a runtime dir of ours.
  function barLink() { for (var i = 0; i < barWidget.data.length; i++) if (barWidget.data[i].socketPath !== undefined) return barWidget.data[i]; return null }
  // The glyph-only button is a BarIconButton, which alone has an icon slot.
  function barTip(type) { var b = all(barWidget, function(i) { return i.tooltipText !== undefined && (i.slotSize !== undefined) === (type === "icon") }); return b.length ? b[0].tooltipText : "" }

  function all(item, test, out, seen) {
    out = out || []; seen = seen || []
    if (!item || seen.indexOf(item) >= 0) return out
    seen.push(item)
    if (test(item)) { out.push(item); return out }
    var nodes = []
    if (item.children) for (var i = 0; i < item.children.length; i++) nodes.push(item.children[i])
    if (item.contentItem) nodes.push(item.contentItem)
    for (var k = 0; k < nodes.length; k++) all(nodes[k], test, out, seen)
    return out
  }
  function texts(root) { return all(root, function(i) { return typeof i.text === "string" && i.font !== undefined && i.visible }).map(function(i) { return i.text }) }
  function cards(root) { return all(root, function(i) { return typeof i.chosen === "function" && i.selectable !== undefined }) }
  function buttonsLabelled(root, label) { return all(root, function(i) { return i.text === label && typeof i.clicked === "function" && i.bordered !== undefined && i.visible }) }
  function check(v, m) { if (!v) throw new Error(m) }
  function speech(key) { var m = window.models.models || []; for (var i = 0; i < m.length; i++) if (m[i].key === key) return m[i]; return null }

  Timer {
    interval: 200; repeat: true; running: true
    onTriggered: {
      try {
        if (++window.ticks > 400) throw new Error("Timed out at step " + window.step)
        if (!window.ready || window.busy) return
        check(!window.failure, window.failure)
        switch (window.step) {
          case 0:
            check(window.models.backend === "local-whispercpp", "starts on the local engine")
            check(texts(modelsView).indexOf(tr.t("models.speechapi")) < 0, "the remote endpoint shows with the local engine selected")
            cards(modelsView)[1].chosen()                       // the remote engine card
            break
          case 1:
            check(window.models.backend === "local-whispercpp", "opening the form changed the active engine")
            check(texts(modelsView).indexOf(tr.t("models.speechapi")) >= 0, "the remote endpoint is missing with the remote engine selected")
            var endpoint = all(modelsView, function(i) { return i.objectName === "speechEndpoint" })[0]
            check(endpoint && endpoint.activateOnSave, "missing staged endpoint form")
            endpoint.draftUrl = "invalid address"
            endpoint.save()
            check(endpoint.checkNote === tr.t("api.invalid") && !window.busy, "invalid endpoint was saved")
            endpoint.draftUrl = "https://example.invalid/v1"
            endpoint.draftModel = "test-model"
            check(window.models.backend === "local-whispercpp" && !window.busy, "editing the form saved it")
            endpoint.save()
            break
          case 2:
            check(window.models.backend === "api", "save and enable did not activate the endpoint")
            cards(modelsView)[0].chosen()
            break
          case 3:
            check(window.models.backend === "local-whispercpp", "the local card did not switch back")
            // A downloaded voice model that is not in use: Use must reach the config.
            var spare = (window.models.models || []).filter(function(m) { return m.kind === "speech" && m.downloaded && !m.active })[0]
            if (!spare) { window.step = 5; return }
            window.spareKey = spare.key
            buttonsLabelled(modelsView, tr.t("models.use"))[0].clicked()
            break
          case 4:
            check(speech(window.spareKey).active === true, "Use did not make " + window.spareKey + " the voice model")
            break
          case 5:
            var before = window.refused.length
            var downloads = buttonsLabelled(modelsView, tr.t("models.download"))
            if (downloads.length) downloads[0].clicked()
            modelsView.command("systemctl --user restart omavoid")
            check(window.refused.length === before + (downloads.length ? 2 : 1), "a download or a restart was not refused")
            window.step = 19
            return
          case 19:
            if (window.hist.length === 0) return
            historyView.visible = true
            window.step = 20
            return
          case 20:
            var t = window.hist[1]
            historyView.openMenu(t, 1, { x: 30, y: 30 })
            check(historyView.menuActions.map(function(a) { return a.key }).indexOf("copy") >= 0, "no Copy for a take with text")
            historyView.fire("copy")
            check(window.ran.length === 1 && window.ran[0][0] === "wl-copy" && window.ran[0][2] === t.text, "Copy did not copy the take it was opened on")
            historyView.openMenu(t, 1, { x: 30, y: 30 })
            historyView.fire("delete")
            check(window.removed.length === 1 && window.removed[0] === t.id, "Delete did not name the take by id")
            check(!historyView.menuOpen, "the menu stayed open")
            historyView.detailsOpen = true
            break
          case 21:
            var dropped = window.hist[window.hist.length - 1]
            check(historyView.dropped(dropped.rejected) === tr.tf("hist.drop.short", "0.2"), "the drop reason was not put in words: " + historyView.dropped(dropped.rejected))
            check(historyView.warning("input is quiet: rms -51.2 dBFS, below -45.0 — the usual cause of dropped words") === tr.tf("hist.w.quiet", "-51.2"), "the quiet warning was not put in words")
            check(historyView.change("dictionary: hyperland→Hyprland×1") === tr.tf("hist.c.dictionary", "hyperland→Hyprland"), "a dictionary change was not put in words")
            historyView.visible = false
            setupView.visible = true
            break
          case 22:
            var st = texts(setupView)
            for (var i = 0; i < st.length; i++)
              check(!/^(first|setup|models|modes|hist|set)\.[a-z.]+$/.test(st[i]), "a string key reached the setup screen: " + st[i])
            check(st.indexOf(tr.t("first.willrun")) >= 0, "the runner's heading is missing")
            // The model is in place and both open steps are optional.
            check(st.indexOf(tr.tf("setup.titleoptional", 2)) >= 0, "the heading counts optional steps as still to do: " + st.slice(0, 3).join(" / "))
            check(st.indexOf(tr.tf("setup.s.model", "large-v3-turbo")) >= 0, "the model step title was not translated")
            check(st.indexOf(tr.tf("setup.x.notinstalled", "llama-server")) >= 0, "the missing engine was not put in words")
            check(st.indexOf(tr.t("setup.x.notingroup")) >= 0, "the input group line was not put in words")
            if (tr.active !== "en")
              check(st.indexOf("not in the input group") < 0, "the daemon's English detail is still on the page")
            setupView.visible = false
            firstRun.visible = true
            break
          case 23:
            check(firstRun.model === "ggml:large-v3-turbo" && firstRun.hotkey === "RIGHTCTRL", "first run has no recommended defaults")
            check(firstRun.lang === tr.active, "first-run language was not preselected")
            firstRun.lang = "zh"; firstRun.model = "ggml:large-v3-turbo-q5_0"; firstRun.hotkey = "RIGHTCTRL"
            var plan = firstRun.steps.map(function(s) { return s.argv.join(" ") })
            check(plan.some(function(p) { return p === "omavoi model pull ggml:large-v3-turbo-q5_0" }), "the plan does not fetch the chosen model")
            check(plan.some(function(p) { return p === "omavoi config set hotkey.key RIGHTCTRL" }), "the plan does not set the chosen key")
            check(texts(firstRun).indexOf("large-v3-turbo-q5_0") >= 0, "the model chip still shows its file format")
            firstRun.visible = false
            var link = barLink()
            check(link !== null, "the bar widget has no link")
            link.uiLang = tr.active
            link.hotkey = "RIGHTCTRL"; link.hotkeyMode = "toggle"; link.hotkeyOn = true
            link.backend = "whisper.cpp ggml:large-v3-turbo [vulkan] http://127.0.0.1:8178 (running)"
            link.state = "idle"
            break
          case 24:
            var idle = barTip("icon")
            check(idle.indexOf(tr.tf("bar.tip.toggle", "RIGHTCTRL")) >= 0, "the idle tooltip does not say how to press the key: " + idle)
            check(idle.indexOf("whisper.cpp") < 0, "the idle tooltip still shows the engine string: " + idle)
            barLink().hotkeyMode = "push_to_talk"
            barLink().state = "recording"
            break
          case 25:
            var rec = barTip("reading")
            check(rec.indexOf(tr.tf("bar.tip.release", "RIGHTCTRL")) >= 0, "the recording tooltip does not say how to finish: " + rec)
            barLink().hotkeyOn = false
            check(barTip("reading") === tr.t("bar.tip.recording"), "a key with no listener is still offered: " + barTip("reading"))
            console.log("VIEWS_SMOKE_OK used=" + (window.spareKey || "none") + " refused=" + JSON.stringify(window.refused))
            Qt.quit()
        }
        window.step++
      } catch (e) { console.error("VIEWS_SMOKE_FAILED", e); Qt.quit() }
    }
  }
  property string spareKey: ""
}
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--daemon', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--language', default='zh')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='omavoi-views-') as temp:
        work = Path(temp)
        for name in ('Commons', 'Ui'):
            (work/name).symlink_to(Path('/usr/share/omarchy/shell')/name)
        (work/'Plugin').symlink_to(Path(__file__).resolve().parent.parent)
        env = {
            'PYTHONPATH': (args.daemon/'src').resolve(),
            'XDG_CONFIG_HOME': work/'config', 'XDG_STATE_HOME': work/'state',
            'XDG_CACHE_HOME': work/'cache', 'XDG_DATA_HOME': work/'data',
            'XDG_RUNTIME_DIR': work/'run',
        }
        (work/'run').mkdir(mode=0o700)
        models = Path.home()/'.local/share/omavoi/models'
        if models.is_dir():
            (work/'data'/'omavoi').mkdir(parents=True)
            (work/'data'/'omavoi'/'models').symlink_to(models)
        (work/'state'/'omavoi').mkdir(parents=True)
        with open(work/'state'/'omavoi'/'history.jsonl', 'w', encoding='utf-8') as fh:
            for entry in takes():
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        bindir = work/'bin'
        bindir.mkdir()
        wrapper = bindir/'omavoi'
        wrapper.write_text('#!/bin/sh\n' + '\n'.join(
            f'export {key}={shlex.quote(str(value))}' for key, value in env.items()
        ) + '\nexec ' + shlex.quote(str(args.python.absolute())) + ' -m omavoi.cli "$@"\n')
        wrapper.chmod(0o700)
        subprocess.run([str(wrapper), 'config', 'set', 'ui.language', args.language], check=True, capture_output=True)
        qml = QML
        for key, value in {'__CLI__': str(wrapper), '__LANG__': args.language}.items():
            qml = qml.replace(key, json.dumps(value))
        (work/'shell.qml').write_text(qml)
        run = subprocess.run(['qs', '-p', str(work/'shell.qml'), '--no-color'],
                             env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen',
                                  # The bar widget's IpcLink looks for the daemon's socket here.
                                  'XDG_RUNTIME_DIR': str(work/'run'),
                                  'PATH': f"{bindir}:{os.environ.get('PATH', '')}"},
                             capture_output=True, text=True, timeout=180)
        output = run.stdout + run.stderr
        bad = ('FAILED', 'ReferenceError', 'TypeError', 'Unable to assign', 'Binding loop', 'binding loop')
        if 'VIEWS_SMOKE_OK' not in output or any(s in output for s in bad):
            print(output)
            return 1
        line = next(l for l in output.splitlines() if 'VIEWS_SMOKE_OK' in l)
        print('Views passed: Models engine and Use, refusals; History menu and words; '
              'Setup without keys; First run plan; bar tooltips.')
        print('  ' + line[line.index('VIEWS_SMOKE_OK') + len('VIEWS_SMOKE_OK '):])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
