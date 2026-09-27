#!/usr/bin/env python3
"""Photograph every console view offscreen, against an isolated configuration.

The console itself is a layer-shell PanelWindow, and the offscreen platform has
no backend for one, so each view is instantiated here the way Console.qml does
it — same properties, same `omavoi` commands behind them — inside a plain
window the size of the console's card. The header is not drawn.

Nothing of the user's is read or written except the speech models, which are
linked in read-only so the Models tab has a real catalogue. The History tab
gets a handful of made-up takes covering the shapes a take can have.

  --views history,modes,models,dictionary,settings,setup,firstrun
           and states: history:dropped, history:quiet, modes:advanced,
           dictionary:edit, dictionary:editmore
  --language zh      any of the eight
  --width/--height   the card is 1440 x 900; the views get 856 of that
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import time

VIEWS = ["history", "modes", "models", "dictionary", "settings", "setup", "firstrun"]
# A view with something done to it first: <view>:<state>.
STATES = ["history:dropped", "history:quiet", "modes:advanced", "dictionary:edit", "dictionary:editmore",
          "settings:advanced", "models:api", "models:advanced", "history:ai", "history:details"]

QML = r'''import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Io
import qs.Commons
import "Plugin"
Window {
  id: window
  width: __WIDTH__; height: __HEIGHT__; visible: true; color: Color.popups.background
  property var views: __VIEWS__
  property int at: -1
  property string current: ""
  property int ticks: 0
  property var cfg: ({})
  property var modesData: ({ modes: [], llm: [] })
  property var modelsData: ({ models: [] })
  property var setupData: ({ ready: false, done: 0, total: 5, steps: [] })
  property var takes: []
  property int waiting: 0
  // Not `strings`: inside an inline Component, `strings: strings` finds the
  // view's own property before this id, and binds it to itself.
  Strings { id: tr; lang: __LANG__ }

  function load(name, proc) { window.waiting++; proc.running = true }
  Process { id: cfgProc; command: [__CLI__, "config", "show", "--json"]
    stdout: StdioCollector { onStreamFinished: { try { window.cfg = JSON.parse(text) } catch (e) {} window.waiting-- } } }
  Process { id: modesProc; command: [__CLI__, "mode", "list", "--json"]
    stdout: StdioCollector { onStreamFinished: { try { window.modesData = JSON.parse(text) } catch (e) {} window.waiting-- } } }
  Process { id: modelsProc; command: [__CLI__, "model", "list", "--json"]
    stdout: StdioCollector { onStreamFinished: { try { window.modelsData = JSON.parse(text) } catch (e) {} window.waiting-- } } }
  Process { id: setupProc; command: [__CLI__, "setup", "--json"]
    stdout: StdioCollector { onStreamFinished: { try { window.setupData = JSON.parse(text) } catch (e) {} window.waiting-- } } }
  Process { id: histProc; command: [__CLI__, "history", "-n", "40", "--json"]
    stdout: StdioCollector { onStreamFinished: { try { window.takes = JSON.parse(text).reverse() } catch (e) {} window.waiting-- } } }
  Component.onCompleted: {
    load("cfg", cfgProc); load("modes", modesProc); load("models", modelsProc)
    load("setup", setupProc); load("history", histProc)
  }

  // A made-up setup report with something missing, so the checklist has rows.
  readonly property var fakeSetup: ({
    ready: false, done: 3, total: 6, steps: [
      { key: "tools", title: "Typing and audio tools", done: true,
        detail: "pw-record, wtype, wl-clipboard, hyprctl, xdotool", command: "", needs_root: false, optional: false, note: "" },
      { key: "engine", title: "Speech engine (Vulkan)", done: true,
        detail: "/usr/bin/whisper-server, backends: cpu, vulkan", command: "sudo pacman -S --needed whisper-cpp ggml ggml-vulkan", needs_root: true, optional: false, note: "" },
      { key: "model", title: "Model weights (ggml:large-v3-turbo)", done: true,
        detail: "/home/you/.local/share/omavoi/models/ggml/ggml-large-v3-turbo.bin", command: "omavoi model pull ggml:large-v3-turbo", needs_root: false, optional: false, note: "" },
      { key: "llm-engine", title: "LLM engine (llama.cpp)", done: false,
        detail: "llama-server is not installed, needed by local", command: "sudo pacman -S --needed llama-cpp", needs_root: true, optional: true,
        note: "About 7 MB. Without it a mode's LLM step falls through and the take arrives as plain dictation with nothing on screen to say why — the reason is in the History tab." },
      { key: "hotkey", title: "Hotkey (RIGHTALT via evdev)", done: false,
        detail: "not in the input group", command: "sudo usermod -aG input $USER", needs_root: true, optional: true,
        note: "A group is granted at login." },
      { key: "service", title: "Start at login", done: false,
        detail: "not enabled", command: "systemctl --user enable --now omavoid.service", needs_root: false, optional: true, note: "" }
    ] })

  Rectangle { anchors.fill: parent; color: Color.popups.background }
  Loader {
    id: stage
    anchors.fill: parent
    readonly property string view: window.current.split(":")[0]
    sourceComponent: view === "history" ? historyC
                   : view === "modes" ? modesC
                   : view === "models" ? modelsC
                   : view === "dictionary" ? dictC
                   : view === "settings" ? settingsC
                   : view === "setup" ? setupC
                   : view === "firstrun" ? firstC : null
  }
  property int historyPick: 0
  Component { id: historyC
    HistoryView { strings: tr; takes: window.takes; selected: window.historyPick; hotkey: "RIGHTALT" } }
  Component { id: modesC
    ModesView { strings: tr; payload: window.modesData; catalogue: window.modelsData } }
  Component { id: modelsC
    ModelsView { strings: tr; payload: window.modelsData; pulling: ({}) } }
  Component { id: dictC
    DictionaryView { strings: tr; cli: [__CLI__] } }
  Component { id: settingsC
    SettingsView { strings: tr; cfg: window.cfg; setupReport: window.setupData } }
  Component { id: setupC
    SetupView { strings: tr; setupReport: window.fakeSetup; daemonPresent: true
                rootPlan: [{ key: "packages", root: true, label: tr.t("first.step.packages"),
                             argv: ["pkexec", "/usr/bin/pacman", "-S", "--needed", "--noconfirm", "llama-cpp"] },
                           { key: "restart", label: tr.t("up.step.restart"),
                             argv: ["systemctl", "--user", "restart", "omavoid"] }] } }
  Component { id: firstC
    FirstRun { strings: tr; daemonPresent: false; foundWeights: "" } }

  property bool grabbing: false
  // What a <view>:<state> name does to the view once it has loaded.
  function prepare(name) {
    var item = stage.item
    if (!item) return
    if (name === "history:dropped") window.historyPick = window.takes.length - 1
    else if (name === "history:quiet") window.historyPick = 4
    else if (name === "history:ai") window.historyPick = 0
    else if (name === "history:details") { window.historyPick = 0; item.detailsOpen = true }
    else if (name === "modes:advanced" || name === "settings:advanced" || name === "models:advanced") item.advancedOpen = true
    else if (name === "models:api") item.apiOpen = true
    else if (name === "dictionary:edit" || name === "dictionary:editmore") {
      var e = (item.payload.entries || [])
      var pick = null
      for (var i = 0; i < e.length; i++) if (e[i].aliases && e[i].aliases.length) { pick = e[i]; break }
      item.openEditor(pick || e[0] || null)
      if (name === "dictionary:editmore") { item.more = true; item.corrections = true }
    }
  }
  function next() {
    window.at++
    if (window.at >= window.views.length) { window.current = ""; ticker.running = false; doneTimer.start(); return }
    window.current = window.views[window.at]
    window.historyPick = 0
    // Views that read on their own (dictionary, settings, update) need a
    // moment for their processes to answer.
    var v = window.current.split(":")[0]
    ticker.settle = v === "settings" || v === "dictionary" ? 14 : 6
    ticker.prepared = false
  }
  Timer {
    id: ticker
    interval: 250; repeat: true; running: true
    property int settle: 0
    property bool prepared: true
    onTriggered: {
      if (++window.ticks > 600) { console.error("UI_SHOTS_TIMEOUT"); Qt.quit() }
      if (window.waiting > 0 || window.grabbing) return
      if (settle > 0) { settle--; return }
      if (!prepared) { prepared = true; window.prepare(window.current); settle = 4; return }
      if (window.current === "") { window.next(); return }
      var name = window.current
      window.grabbing = true
      window.contentItem.grabToImage(function(r) {
        r.saveToFile(__OUT__ + "/" + name.replace(":", "-") + ".png")
        window.grabbing = false
        window.next()
      })
    }
  }
  Timer { id: doneTimer; interval: 800; onTriggered: { console.log("UI_SHOTS_OK"); Qt.quit() } }
}
'''


def takes() -> list[dict]:
    """Takes in the shapes the History tab has to draw."""
    now = time.time()

    def take(i, text, *, raw=None, mode="default", secs=3.2, rms=-24.0, lang="chinese",
             changes=(), warnings=(), steps=(), rejected="", inject="wtype", segs=None):
        raw = raw if raw is not None else text
        segs = segs or [{"start": 0.0, "end": secs, "text": raw, "avg_logprob": -0.21,
                         "no_speech_prob": 0.02, "compression_ratio": 1.1, "temperature": 0.0}]
        return {
            "ts": now - i * 437, "id": f"{int((now - i * 437) * 1000):x}",
            "audio": {"seconds": secs, "peak_dbfs": rms + 14, "rms_dbfs": rms, "head_dbfs": rms - 20,
                      "preroll": 0.6, "tail": 0.25, "truncated": False},
            "raw_text": raw, "text": "" if rejected else text, "warnings": list(warnings),
            "rejected": rejected, "window": {"class": "com.mitchellh.ghostty", "title": "", "xwayland": False},
            "mode": {"name": mode, "language": "", "inject": "auto", "steps": []},
            "asr": {"text": raw, "language": lang, "language_probability": 0.0, "audio_seconds": secs,
                    "decode_seconds": 0.31, "rtf": 0.31 / max(secs, 0.1), "model": "ggml:large-v3-turbo",
                    "device": "whisper.cpp/gpu", "segments": segs if not rejected else []},
            "post": {"changes": list(changes), "rejected": "", "changed": bool(changes)},
            "rules_text": text, "steps": list(steps),
            "inject": {"ok": True, "method": inject, "seconds": 0.04, "error": "", "fell_back": False,
                       "paste_via": "", "chars": len(text)} if not rejected else {},
            "total_seconds": 0.52,
        }

    return [
        take(6, "", rejected="only 0.20s, below audio.min_seconds=0.35", secs=0.2),
        take(5, "Let's ship the Hyprland config tonight.", raw="lets ship the hyperland config tonight",
             lang="english", changes=["dictionary: hyperland→Hyprland", "fillers"]),
        take(4, "我觉得这个 API 的设计还可以再简单一点。", raw="嗯，我觉得这个API的设计还可以再简单一点",
             changes=["fillers", "cjk spacing"], mode="default"),
        take(3, "把会议改到周四下午三点。\nMove the meeting to Thursday at 3 pm.", mode="to Thai",
             raw="把会议改到周四下午三点",
             steps=[{"llm": "agent", "index": 0, "ok": True, "seconds": 2.41, "model": "",
                     "text": "…", "before": "把会议改到周四下午三点"}]),
        take(2, "检查一下 omavoi 的日志", raw="检查一下omavoi的日志", rms=-51.2,
             warnings=["input is quiet: rms -51.2 dBFS, below -45.0 — the usual cause of dropped words"],
             changes=["cjk spacing"]),
        take(1, "This is the prose version of what I said.", mode="prose", lang="english",
             raw="so this is uh the prose version of what i said",
             steps=[{"llm": "local", "index": 0, "error": "llama-server is not installed", "kept": True}],
             warnings=["step 1 (local) fell through: llama-server is not installed"],
             segs=[{"start": 0.0, "end": 1.4, "text": "so this is uh", "avg_logprob": -0.35,
                    "no_speech_prob": 0.01}, {"start": 1.4, "end": 3.0, "text": " the prose version of what i said",
                                              "avg_logprob": -1.24, "no_speech_prob": 0.05}]),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--daemon', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--language', default='zh')
    parser.add_argument('--views', default=",".join(VIEWS))
    parser.add_argument('--width', type=int, default=1440)
    parser.add_argument('--height', type=int, default=856)
    parser.add_argument('--output', type=Path, default=Path('/tmp/omavoi-ui-shots'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='omavoi-ui-') as temp:
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
        views = [v for v in args.views.split(",") if v in VIEWS or v in STATES]
        qml = QML
        for key, value in {'__CLI__': str(wrapper), '__LANG__': args.language, '__WIDTH__': args.width,
                           '__HEIGHT__': args.height, '__OUT__': str(args.output), '__VIEWS__': views}.items():
            qml = qml.replace(key, json.dumps(value))
        (work/'shell.qml').write_text(qml)
        # The views run `omavoi` by name, as the console does; this one is it.
        run = subprocess.run(['qs', '-p', str(work/'shell.qml'), '--no-color'],
                             env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen',
                                  'PATH': f"{bindir}:{os.environ.get('PATH', '')}"},
                             capture_output=True, text=True, timeout=240)
        output = run.stdout + run.stderr
        noise = ('WAYLAND_DISPLAY', '--- WARNING', 'If you are actually', 'Launching config',
                 'Shell ID', 'Saving logs', 'Configuration Loaded')
        lines = [l for l in output.splitlines() if l.strip() and not any(n in l for n in noise)]
        print("\n".join(lines[-60:]))
        print(f"Screenshots: {args.output}")
        return 0 if 'UI_SHOTS_OK' in output else 1


if __name__ == '__main__':
    raise SystemExit(main())
