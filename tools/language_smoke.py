#!/usr/bin/env python3
"""Exercise the actual language popup and CLI with an isolated configuration.

Uses the real Quickshell popup, filtering and CLI with the installed Omarchy UI kit.
No microphone, user settings or target-app input is used.
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
  width: __WIDTH__; height: 820; visible: true; color: Color.popups.background
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
    id: reader; command: [__CLI__, "mode", "list", "--json"]; running: true
    stderr: StdioCollector { onStreamFinished: if (text) console.log("reader stderr", text) }
    stdout: StdioCollector { onStreamFinished: { modes.payload = JSON.parse(text); window.loaded = true; window.busy = false } }
  }
  Process {
    id: writer
    onExited: function(code, status) {
      if (code) window.failure = "CLI write failed: " + code
      reader.running = true
    }
  }
  function field(item, name) {
    if (item.objectName === name) return item
    var children = item.children || []
    for (var i = 0; i < children.length; i++) { var found = field(children[i], name); if (found) return found }
    return null
  }
  function check(value, message) { if (!value) throw new Error(message) }
  function optionList(item, visited) {
    if (!item || visited.indexOf(item) >= 0) return null
    visited.push(item)
    if (typeof item.selectCurrent === "function") return item
    var nodes = []
    if (item.children) for (var i = 0; i < item.children.length; i++) nodes.push(item.children[i])
    if (item.resources) for (var j = 0; j < item.resources.length; j++) nodes.push(item.resources[j])
    if (item.contentItem) nodes.push(item.contentItem)
    for (var k = 0; k < nodes.length; k++) { var found = optionList(nodes[k], visited); if (found) return found }
    return null
  }
  function select(picker, code) {
    if (!picker.popupOpen) picker.open()
    var list = optionList(picker, [])
    check(!!list, "Missing popup option list")
    var idx = picker.filtered.findIndex(function(row) { return row.value === code })
    check(idx >= 0, "Missing filtered choice " + code)
    list.currentIndex = idx
    list.selectCurrent()
  }
  Timer {
    interval: 150; repeat: true; running: true
    onTriggered: {
      try {
        if (++window.ticks > 150) throw new Error("Timed out at step " + window.step)
        if (!window.loaded || window.busy) return
        check(!window.failure, window.failure)
        var picker = window.field(modes, "inputLanguagePicker")
        check(!!picker, "Missing language picker")
        switch(window.step) {
          case 0:
            check(picker.value === "auto", "Initial choice is not auto")
            check(picker.options.length === 102, "Wrong language count")
            check(picker.mapToItem(window.contentItem, 0, 0).x + picker.width <= window.width, "Popup exceeds window width")
            picker.open()
            break
          case 1:
            check(picker.popupOpen, "Popup did not open")
            window.contentItem.grabToImage(function(result) { result.saveToFile(__IMAGE__); window.activeFocusItem.text = "简体中文" })
            break
          case 2:
            check(picker.filtered.length === 1 && picker.filtered[0].value === "zh-Hans", "Chinese search failed")
            select(picker, "zh-Hans")
            break
          case 3:
            check(modes.mode.language === "zh-Hans", "Simplified preference was not saved")
            modes.selected = "prose"
            break
          case 4:
            check(picker.value === "auto", "Binding did not follow mode switch")
            picker.open()
            break
          case 5:
            window.activeFocusItem.text = "Traditional Chinese"
            break
          case 6:
            check(picker.filtered.length === 1 && picker.filtered[0].value === "zh-Hant", "English search failed")
            select(picker, "zh-Hant")
            break
          case 7:
            check(modes.mode.language === "zh-Hant", "Traditional preference was not saved")
            modes.selected = "default"
            break
          case 8:
            check(picker.value === "zh-Hans", "First mode lost its saved choice")
            select(picker, "auto")
            break
          case 9:
            check(modes.mode.language === "auto", "Auto reset was not saved")
            modes.selected = "prose"
            break
          case 10:
            check(picker.value === "zh-Hant", "Auto reset changed another mode")
            picker.open()
            break
          case 11:
            window.activeFocusItem.text = "zzzz-no-such-language"
            break
          case 12:
            check(picker.filtered.length === 0, "No-match search failed")
            picker.close()
            check(picker.value === "zh-Hant", "Searching changed the saved preference")
            modes.selected = "default"
            break
          case 13:
            check(picker.value === "auto", "Picker did not restore auto")
            console.log("LANGUAGE_SMOKE_OK")
            Qt.quit()
        }
        window.step++
      } catch(e) { console.error("LANGUAGE_SMOKE_FAILED", e); Qt.quit() }
    }
  }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--daemon', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--language', default='zh')
    parser.add_argument('--width', type=int, default=980)
    parser.add_argument('--output', type=Path, default=Path('/tmp/omavoi-language-smoke'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='omavoi-language-') as temp:
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
        wrapper = work/'omavoi'
        wrapper.write_text('#!/bin/sh\n' + '\n'.join(
            f'export {key}={shlex.quote(str(value))}' for key, value in env.items()
        ) + '\nexec ' + shlex.quote(str(args.python.absolute())) + ' -m omavoi.cli "$@"\n')
        wrapper.chmod(0o700)
        # Keep the selected UI locale and the daemon's option labels aligned.
        subprocess.run([str(wrapper), 'config', 'set', 'ui.language', args.language], check=True, capture_output=True)
        subprocess.run([str(wrapper), 'mode', 'set', 'prose', 'language', 'auto'], check=True, capture_output=True)
        qml = QML
        for key, value in {'__CLI__': str(wrapper), '__LANG__': args.language,
                           '__WIDTH__': args.width, '__IMAGE__': str(args.output/'menu.png')}.items():
            qml = qml.replace(key, json.dumps(value))
        (work/'shell.qml').write_text(qml)
        run = subprocess.run(['qs', '-p', str(work/'shell.qml'), '--no-color'],
                             env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'},
                             capture_output=True, text=True, timeout=30)
        output = run.stdout + run.stderr
        if 'LANGUAGE_SMOKE_OK' not in output or any(s in output for s in ('FAIL!', 'ReferenceError', 'TypeError', 'Unable to assign', 'recursive rearrange')):
            print(output)
            return 1
        print('Language UI passed: search, selection, persistence, mode switching, auto reset, no matches.')
        print(f'Menu image: {args.output / "menu.png"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
