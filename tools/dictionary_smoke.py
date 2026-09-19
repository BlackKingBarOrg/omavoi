#!/usr/bin/env python3
"""Exercise the real QML editor and CLI in an isolated, temporary configuration.

Requires Quickshell and the Omarchy shell UI kit. No microphone, desktop
changes, user configuration writes, or running speech service are needed.
Usage: python tools/dictionary_smoke.py --daemon ../omavoi-daemon --python ../omavoi-daemon/.venv/bin/python
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
import qs.Commons
import "Plugin"
Window {
  id: window
  width: WIDTH; height: 820; visible: true; color: Color.popups.background
  property int step: 0
  property int ticks: 0
  property string entryId: ""
  Strings { id: strings; lang: LANG }
  DictionaryView { id: dictionary; anchors.fill: parent; strings: strings; cli: [CLI] }
  function check(value, message) { if (!value) throw new Error(message) }
  function field(item, name) {
    if (item.objectName === name) return item
    var children = item.children || []
    for (var i=0; i<children.length; i++) { var found = field(children[i], name); if (found) return found }
    return null
  }
  function current() { return dictionary.payload.entries.filter(function(e) { return e.id === entryId })[0] }
  Timer {
    interval: 180; repeat: true; running: true
    onTriggered: {
      try {
        if (++window.ticks > 100) throw new Error("Timed out at step " + window.step)
        if (dictionary.busy) return
        check(!dictionary.error, dictionary.error + " " + dictionary.detail)
        switch(window.step) {
          case 0:
            if (!dictionary.loaded) return
            check(!dictionary.legacy, "Unexpected legacy fallback")
            dictionary.openEditor(null)
            field(dictionary, "dictionarySpelling").text = "星河设计"
            check(dictionary.draft().recognition_hint, "New words should help recognition")
            check(!dictionary.draft().phonetic.enabled, "Sound matching must default off")
            dictionary.save()
            break
          case 1:
            check(!dictionary.editing, "Save did not close editor")
            var e = dictionary.payload.entries.filter(function(e) { return e.text === "星河设计" })[0]
            check(!!e, "Created word missing")
            window.entryId = e.id
            e.aliases = ["星合设计", "星和设计"]
            dictionary.send("save", {entry: e})
            break
          case 2:
            check(current().aliases.length === 2, "Correction spellings not saved")
            dictionary.send("preview", {entry: current(), text: "联系星合设计", mode: "default"})
            break
          case 3:
            check(dictionary.previewText === "联系星河设计", "Wrong preview: " + dictionary.previewText)
            dictionary.toggleEntry(current())
            break
          case 4:
            check(!current().enabled, "Pause failed")
            dictionary.toggleEntry(current())
            break
          case 5:
            check(current().enabled, "Resume failed")
            dictionary.send("remove", {id: window.entryId})
            break
          case 6:
            check(!current(), "Delete failed")
            check(dictionary.undoEntry.id === window.entryId, "Missing undo snapshot")
            dictionary.send("restore", {entry: dictionary.undoEntry})
            break
          case 7:
            check(current().aliases.length === 2, "Undo lost corrections")
            dictionary.openEditor(current())
            field(dictionary, "dictionarySpelling").text = "未保存"
            dictionary.closeEditor()
            check(dictionary.discardPrompt && dictionary.editing, "Unsaved draft was discarded")
            dictionary.editing = false
            dictionary.note = ""
            break
          case 8:
            window.contentItem.grabToImage(function(result) { result.saveToFile(LIST_IMAGE) })
            break
          case 9:
            dictionary.openEditor(current())
            break
          case 10:
            window.contentItem.grabToImage(function(result) { result.saveToFile(EDITOR_IMAGE) })
            break
          case 11:
            console.log("DICTIONARY_SMOKE_OK")
            Qt.quit()
        }
        window.step++
      } catch(e) { console.error("DICTIONARY_SMOKE_FAILED", e); Qt.quit() }
    }
  }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--daemon', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--shell', type=Path, default=Path('/usr/share/omarchy/shell'))
    parser.add_argument('--output', type=Path, default=Path('/tmp/omavoi-dictionary-smoke'))
    parser.add_argument('--language', default='zh')
    parser.add_argument('--width', type=int, default=980)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='omavoi-dictionary-') as temp:
        work = Path(temp)
        for name in ('Commons', 'Ui'):
            (work/name).symlink_to((args.shell/name).resolve())
        (work/'Plugin').symlink_to(Path(__file__).resolve().parent.parent)
        wrapper = work/'omavoi'
        wrapper.write_text('#!/bin/sh\n' + '\n'.join(
            f'export {key}={shlex.quote(str(value))}' for key, value in {
                'PYTHONPATH': (args.daemon/'src').resolve(),
                'XDG_CONFIG_HOME': work/'config', 'XDG_STATE_HOME': work/'state',
                'XDG_DATA_HOME': work/'data', 'XDG_RUNTIME_DIR': work/'runtime',
            }.items()) + '\nexec ' + shlex.quote(str(args.python.resolve())) + ' -m omavoi.cli "$@"\n')
        wrapper.chmod(0o700)
        qml = QML
        for key, value in {'WIDTH': args.width, 'LANG': args.language, 'CLI': str(wrapper),
                           'LIST_IMAGE': str((args.output/'list.png').resolve()),
                           'EDITOR_IMAGE': str((args.output/'editor.png').resolve())}.items():
            qml = qml.replace(key, json.dumps(value))
        (work/'shell.qml').write_text(qml)
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software')
        run = subprocess.run(['qs', '-p', str(work/'shell.qml'), '--no-color'],
                             env=env, text=True, capture_output=True, timeout=30)
        output = run.stdout + run.stderr
        (args.output/'run.log').write_text(output)
        if run.returncode or 'DICTIONARY_SMOKE_OK' not in output or 'DICTIONARY_SMOKE_FAILED' in output:
            print(output)
            return 1
        if any(message in output for message in ('ReferenceError', 'TypeError', 'Binding loop', 'Unable to assign')):
            print(output)
            return 1
        print(f'Dictionary UI passed: add, edit corrections, preview, pause, resume, delete, undo, draft protection. Images: {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
