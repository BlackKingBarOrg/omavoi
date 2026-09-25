#!/usr/bin/env python3
"""Exercise the Modes page's basic and advanced halves with an isolated configuration.

Uses the real ModesView, the installed Omarchy UI kit and the daemon's own CLI,
against a configuration in a temporary directory. The speech models already
downloaded on this machine are linked in read-only, so the voice-model row has
something to show; nothing else of the user's is read or written.

Saves a screenshot of each state, so the layout can be looked at as well as
asserted on:

  basic.png      the page as it opens, advanced folded
  folded.png     the closed fold naming a changed setting
  advanced.png   the fold open
  inherited.png  code, sending the hint it inherits from default
  adding.png     "+ add a rewrite step" asking which LLM
  following.png  the list while the focused window picks the mode

--preview CONFIG copies a config.toml in instead and only takes pictures of
its default, code and "to Thai" modes; the original file is only read.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

QML = '''import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Io
import qs.Commons
import "Plugin"
Window {
  id: window
  width: __WIDTH__; height: __HEIGHT__; visible: true; color: Color.popups.background
  property bool loaded: false
  property bool busy: false
  property int step: 0
  property int ticks: 0
  property string failure: ""
  Strings { id: strings; lang: __LANG__ }
  ModesView {
    id: modes; anchors.fill: parent; strings: strings
    onCommandArgs: function(argv) {
      window.busy = true
      writer.command = [__CLI__].concat(argv.slice(1))
      writer.running = true
    }
  }
  Process {
    id: catalogue; command: [__CLI__, "model", "list", "--json"]; running: true
    stdout: StdioCollector { onStreamFinished: modes.catalogue = JSON.parse(text) }
  }
  Process {
    id: reader; command: [__CLI__, "mode", "list", "--json"]; running: true
    stderr: StdioCollector { onStreamFinished: if (text) console.log("reader stderr", text) }
    stdout: StdioCollector { onStreamFinished: { modes.payload = JSON.parse(text); window.loaded = true; window.busy = false } }
  }
  Process {
    id: writer
    onExited: function(code, status) {
      if (code) window.failure = "CLI write failed: " + code + " " + JSON.stringify(writer.command)
      reader.running = true
    }
  }
  function find(item, name) {
    if (!item) return null
    if (item.objectName === name) return item
    var nodes = []
    if (item.children) for (var i = 0; i < item.children.length; i++) nodes.push(item.children[i])
    if (item.contentItem) nodes.push(item.contentItem)
    for (var k = 0; k < nodes.length; k++) { var found = find(nodes[k], name); if (found) return found }
    return null
  }
  function check(value, message) { if (!value) throw new Error(message) }
  function shot(name) { window.contentItem.grabToImage(function(result) { result.saveToFile(__OUT__ + "/" + name) }) }
  function showing(name) { var item = find(modes, name); return !!item && item.visible }
  function summary() { var s = find(modes, "advancedSummary"); return s && s.visible ? s.text : "" }
  Timer {
    interval: 200; repeat: true; running: true
    onTriggered: {
      try {
        if (++window.ticks > 200) throw new Error("Timed out at step " + window.step)
        if (!window.loaded || window.busy) return
        check(!window.failure, window.failure)
        if (__PREVIEW__) {
          // Someone's own modes, copied in: pictures only, nothing written.
          switch(window.step) {
            case 0: window.shot("preview-default.png"); break
            case 1: modes.advancedOpen = true; break
            case 2: window.shot("preview-default-advanced.png"); break
            case 3: modes.selected = "code"; break
            case 4: window.shot("preview-code-advanced.png"); break
            case 5: modes.advancedOpen = false; modes.selected = "to Thai"; break
            case 6: window.shot("preview-to-thai.png"); break
            case 7: console.log("MODES_SMOKE_OK"); Qt.quit()
          }
          window.step++
          return
        }
        if (__LEGACY__) {
          // A daemon from before the script setting: the row it cannot
          // honour is not shown, and nothing else on the page breaks.
          switch(window.step) {
            case 0:
              check(modes.payload.script_supported !== true, "This daemon has the script setting")
              check(!showing("scriptRow"), "Chinese characters shown to a daemon that cannot use it")
              check(showing("addStep"), "No add-step action")
              modes.advancedOpen = true
              break
            case 1:
              check(showing("advancedBody"), "Advanced did not open")
              window.shot("legacy.png")
              break
            case 2:
              console.log("MODES_SMOKE_OK")
              Qt.quit()
          }
          window.step++
          return
        }
        switch(window.step) {
          case 0:
            check(modes.current === "default", "Did not open on default")
            check(modes.payload.script_supported === true, "The daemon does not report the script setting")
            check(showing("scriptRow"), "Chinese characters row hidden on auto")
            check(!showing("advancedBody"), "Advanced is open before anyone opened it")
            check(summary() === "", "A fresh default reports changed settings: " + summary())
            check(showing("addStep"), "No add-step action")
            window.shot("basic.png")
            break
          case 1:
            find(modes, "script:zh-Hans").clicked()
            break
          case 2:
            check(modes.mode.script === "zh-Hans", "Simplified was not saved")
            check(modes.language === "auto", "Choosing a script pinned the language")
            modes.commandArgs(["omavoi", "mode", "set", "default", "prompt", __PROMPT__])
            break
          case 3:
            check(summary().indexOf(strings.t("modes.decoderhint")) >= 0,
                  "A recognition hint is set and the fold does not say so: " + summary())
            window.shot("folded.png")
            break
          case 4:
            modes.advancedOpen = true
            break
          case 5:
            check(showing("advancedBody"), "Advanced did not open")
            check(summary() === "", "The open fold still shows its summary")
            window.shot("advanced.png")
            break
          case 6:
            modes.selected = "code"
            break
          case 7:
            check(modes.current === "code", "Did not open code")
            check(modes.mode.prompt === __PROMPT__ && modes.mode.prompt_inherited === true,
                  "code does not show the hint it inherits from default")
            check(modes.mode.script === "zh-Hans", "code does not inherit default's script")
            window.shot("inherited.png")
            break
          case 8:
            modes.advancedOpen = false
            break
          case 9:
            check(summary().indexOf(strings.t("modes.inject.clipboard")) >= 0,
                  "code pastes and the fold does not say so: " + summary())
            modes.selected = "default"
            modes.adding = true
            break
          case 10:
            check(!showing("addStep") && showing("addStep:agent"), "Add did not ask which LLM")
            window.shot("adding.png")
            break
          case 11:
            find(modes, "addStep:agent").clicked()
            break
          case 12:
            check(!modes.adding, "Picking an LLM left the question open")
            check((modes.mode.steps || []).length === 1 && modes.mode.steps[0].llm === "agent",
                  "The step was not added")
            modes.commandArgs(["omavoi", "mode", "set", "default", "language", "th"])
            break
          case 13:
            check(!showing("scriptRow"), "Chinese characters shown for a mode pinned to Thai")
            find(modes, "switching").changed("window")
            break
          case 14:
            check(modes.byWindow, "Following the window was not saved")
            window.shot("following.png")
            break
          case 15:
            find(modes, "switching").changed("fixed")
            break
          case 16:
            check(!modes.byWindow, "Picking here was not saved")
            console.log("MODES_SMOKE_OK")
            Qt.quit()
        }
        window.step++
      } catch(e) { console.error("MODES_SMOKE_FAILED", e); Qt.quit() }
    }
  }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--daemon', type=Path, required=True, help='a daemon checkout with the script setting')
    parser.add_argument('--python', type=Path, required=True, help="a python with the daemon's dependencies")
    parser.add_argument('--language', default='zh')
    parser.add_argument('--width', type=int, default=1400)
    parser.add_argument('--height', type=int, default=900)
    parser.add_argument('--output', type=Path, default=Path('/tmp/omavoi-modes-smoke'))
    parser.add_argument('--preview', type=Path, metavar='CONFIG',
                        help='copy this config.toml in and only take pictures of its modes')
    parser.add_argument('--legacy', action='store_true',
                        help='the daemon predates the script setting; check the page degrades')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='omavoi-modes-') as temp:
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
        wrapper = work/'omavoi'
        wrapper.write_text('#!/bin/sh\n' + '\n'.join(
            f'export {key}={shlex.quote(str(value))}' for key, value in env.items()
        ) + '\nexec ' + shlex.quote(str(args.python.absolute())) + ' -m omavoi.cli "$@"\n')
        wrapper.chmod(0o700)
        if args.preview:
            (work/'config'/'omavoi').mkdir(parents=True)
            (work/'config'/'omavoi'/'config.toml').write_bytes(args.preview.read_bytes())
        subprocess.run([str(wrapper), 'config', 'set', 'ui.language', args.language], check=True, capture_output=True)
        qml = QML
        for key, value in {'__CLI__': str(wrapper), '__LANG__': args.language,
                           '__WIDTH__': args.width, '__HEIGHT__': args.height,
                           '__PROMPT__': '如果是中文请只输出简体中文', '__OUT__': str(args.output),
                           '__LEGACY__': args.legacy, '__PREVIEW__': bool(args.preview)}.items():
            qml = qml.replace(key, json.dumps(value))
        (work/'shell.qml').write_text(qml)
        run = subprocess.run(['qs', '-p', str(work/'shell.qml'), '--no-color'],
                             env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'},
                             capture_output=True, text=True, timeout=90)
        output = run.stdout + run.stderr
        if 'MODES_SMOKE_OK' not in output or any(s in output for s in (
                'FAIL', 'ReferenceError', 'TypeError', 'Unable to assign', 'recursive rearrange',
                'Binding loop', 'binding loop')):
            print(output)
            return 1
        print('Pictures taken of the copied modes.' if args.preview else
              'Modes UI passed against an older daemon: no script row, nothing broken.' if args.legacy else
              'Modes UI passed: basic and advanced halves, fold summary, script, inherited hint, '
              'add-step question, switching.')
        print(f'Screenshots: {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
