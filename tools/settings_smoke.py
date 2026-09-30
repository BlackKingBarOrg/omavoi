#!/usr/bin/env python3
"""Exercise the Settings tab's controls against an isolated configuration.

Every control that writes a setting is clicked and the config is read back:
the overlay switch and the rows it hides, the dwell and size choices, the
notification switch, the recordings kept, the key typed by name, the press
style, and an audio number under Advanced, which the closed fold must then
name. Commands that act on the machine rather than on the config — restart
the service, update, open an editor — are refused here and only recorded.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

QML = r'''import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Io
import qs.Commons
import "Plugin"
Window {
  id: window
  width: 1400; height: 1700; visible: true; color: Color.popups.background
  property bool loaded: false
  property bool busy: false
  property int step: 0
  property int ticks: 0
  property string failure: ""
  property var refused: []
  Strings { id: tr; lang: __LANG__ }
  SettingsView {
    id: view; anchors.fill: parent; strings: tr
    // As the console does: a shell string, or argv.
    onCommand: function(cmd) { window.run(["sh", "-c", cmd]) }
    onCommandArgs: function(argv) { window.run(argv) }
  }
  function run(argv) {
    var text = argv.join(" ")
    if (!/^(sh -c )?omavoi config set /.test(text)) { window.refused.push(text); return }
    window.busy = true
    writer.command = argv
    writer.running = true
  }
  Process {
    id: reader; command: [__CLI__, "config", "show", "--json"]; running: true
    stdout: StdioCollector { onStreamFinished: { view.cfg = JSON.parse(text); window.loaded = true; window.busy = false } }
  }
  Process {
    id: writer
    stderr: StdioCollector { id: writeErr }
    onExited: function(code, status) {
      if (code) window.failure = "write failed: " + JSON.stringify(writer.command) + " " + writeErr.text
      reader.running = true
    }
  }
  function find(item, name) {
    if (!item) return null
    if (item.objectName === name) return item
    var nodes = []
    if (item.children) for (var i = 0; i < item.children.length; i++) nodes.push(item.children[i])
    if (item.contentItem) nodes.push(item.contentItem)
    for (var k = 0; k < nodes.length; k++) { var f = find(nodes[k], name); if (f) return f }
    return null
  }
  // Every item of a type, by a property only that type has.
  function all(item, test, out, seen) {
    out = out || []
    seen = seen || []
    // A Flickable's contentItem is among its children as well.
    if (!item || seen.indexOf(item) >= 0) return out
    seen.push(item)
    // A control's own insides can look like the control; stop at the first.
    if (test(item)) { out.push(item); return out }
    var nodes = []
    if (item.children) for (var i = 0; i < item.children.length; i++) nodes.push(item.children[i])
    if (item.contentItem) nodes.push(item.contentItem)
    for (var k = 0; k < nodes.length; k++) all(nodes[k], test, out, seen)
    return out
  }
  function chips() { return all(view, function(i) { return i.label !== undefined && i.on !== undefined && typeof i.clicked === "function" }) }
  function chipLabelled(text) { var c = chips(); for (var i = 0; i < c.length; i++) if (c[i].label === text && c[i].visible) return c[i]; return null }
  function groups() { return all(view, function(i) { return i.options !== undefined && typeof i.changed === "function" }) }
  function groupWith(value) { var g = groups(); for (var i = 0; i < g.length; i++) for (var j = 0; j < g[i].options.length; j++) if (g[i].options[j].value === value) return g[i]; return null }
  function numbers() { return all(view, function(i) { return typeof i.modified === "function" && i.stepSize !== undefined }) }
  function check(v, m) { if (!v) throw new Error(m) }
  function cfg(path) { var n = view.cfg; var p = path.split("."); for (var i = 0; i < p.length; i++) n = n ? n[p[i]] : undefined; return n }
  function shot(name) { window.contentItem.grabToImage(function(r) { r.saveToFile(__OUT__ + "/" + name) }) }
  Timer {
    interval: 200; repeat: true; running: true
    onTriggered: {
      try {
        if (++window.ticks > 300) throw new Error("Timed out at step " + window.step)
        if (!window.loaded || window.busy) return
        check(!window.failure, window.failure)
        switch (window.step) {
          case 0:
            check(cfg("ui.hud") === true, "overlay starts off")
            chipLabelled(tr.t("set.on")).clicked()          // the first on-chip is the overlay's
            break
          case 1:
            check(cfg("ui.hud") === false, "overlay switch did not write ui.hud=false")
            check(!groupWith("changed").visible, "the dwell choice stays up for an overlay that is off")
            chips().filter(function(c) { return c.visible && c.label === tr.t("set.off") })[0].clicked()
            break
          case 2:
            check(cfg("ui.hud") === true, "overlay did not come back on")
            groupWith("never").changed("never")
            break
          case 3:
            check(cfg("ui.hud_dwell") === "never", "dwell did not write never")
            groupWith("m").changed("m")
            break
          case 4:
            check(cfg("ui.hud_size") === "m", "size did not write m")
            groupWith("toggle").changed("toggle")
            break
          case 5:
            check(cfg("hotkey.mode") === "toggle", "press style did not write toggle")
            find(view, "historyAudioCount").modified(40)                                // keep recordings is the first one showing
            break
          case 6:
            check(cfg("history.keep_audio") === 40, "keep recordings did not write 40: " + cfg("history.keep_audio"))
            check(find(view, "settingsAdvancedBody").visible === false, "Advanced is open before anyone opened it")
            view.advancedOpen = true
            break
          case 7:
            var nums = numbers().filter(function(x) { return x.visible })
            check(nums.length === 6, "Expected two retention fields and four audio numbers: " + nums.length)
            var pre = find(view, "audioNumber:audio.preroll_seconds").field
            check(pre.contentItem.text === "0.6", "pre-roll display does not show seconds: " + pre.contentItem.text)
            check(pre.valueFromText("0.8", Qt.locale("en_US")) === 800, "seconds input lost precision")
            check(pre.textFromValue(600, Qt.locale("en_US")) === "0.6", "pre-roll still displays milliseconds")
            var maximum = find(view, "audioNumber:audio.max_seconds").field
            check(maximum.contentItem.text === "5", "maximum length display does not show minutes: " + maximum.contentItem.text)
            check(maximum.textFromValue(300, Qt.locale("en_US")) === "5", "maximum length does not display minutes")
            check(maximum.valueFromText("5.5", Qt.locale("en_US")) === 330, "minutes input did not convert to seconds")
            find(view, "audioNumber:audio.preroll_seconds").modified(800)                            // start early by, in ms
            break
          case 8:
            check(Math.abs(cfg("audio.preroll_seconds") - 0.8) < 1e-9, "pre-roll did not write 0.8: " + cfg("audio.preroll_seconds"))
            check(find(view, "audioNumber:audio.preroll_seconds").field.contentItem.text === "0.8", "display did not follow saved seconds")
            view.advancedOpen = false
            break
          case 9:
            var s = find(find(view, "settingsAdvanced"), "foldSummary")
            check(s && s.visible && s.text.indexOf("0.8") >= 0, "the closed fold does not name the changed pre-roll: " + (s ? s.text : "none"))
            window.shot("settings-changed.png")
            view.commandArgs(["omavoi", "config", "set", "hotkey.key", "F9"])
            break
          case 10:
            check(cfg("hotkey.key") === "F9", "typed key did not write F9")
            find(view, "hotkeyToggle").clicked()
            break
          case 11:
            check(cfg("hotkey.enabled") === false, "hotkey toggle did not disable the shortcut")
            find(view, "hotkeyToggle").clicked()
            break
          case 12:
            check(cfg("hotkey.enabled") === true, "hotkey toggle did not enable the shortcut")
            var refusedBefore = window.refused.length
            view.command("systemctl --user restart omavoid")
            check(window.refused.length === refusedBefore + 1, "a machine command was not refused")
            console.log("SETTINGS_SMOKE_OK")
            Qt.quit()
        }
        window.step++
      } catch (e) { console.error("SETTINGS_SMOKE_FAILED", e); Qt.quit() }
    }
  }
}
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--daemon', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--language', default='zh')
    parser.add_argument('--output', type=Path, default=Path('/tmp/omavoi-settings-smoke'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='omavoi-settings-') as temp:
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
        bindir = work/'bin'
        bindir.mkdir()
        wrapper = bindir/'omavoi'
        wrapper.write_text('#!/bin/sh\n' + '\n'.join(
            f'export {key}={shlex.quote(str(value))}' for key, value in env.items()
        ) + '\nexec ' + shlex.quote(str(args.python.absolute())) + ' -m omavoi.cli "$@"\n')
        wrapper.chmod(0o700)
        subprocess.run([str(wrapper), 'config', 'set', 'ui.language', args.language], check=True, capture_output=True)
        qml = QML
        for key, value in {'__CLI__': str(wrapper), '__LANG__': args.language, '__OUT__': str(args.output)}.items():
            qml = qml.replace(key, json.dumps(value))
        (work/'shell.qml').write_text(qml)
        run = subprocess.run(['qs', '-p', str(work/'shell.qml'), '--no-color'],
                             env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen',
                                  'PATH': f"{bindir}:{os.environ.get('PATH', '')}"},
                             capture_output=True, text=True, timeout=120)
        output = run.stdout + run.stderr
        bad = ('FAILED', 'ReferenceError', 'TypeError', 'Unable to assign', 'Binding loop', 'binding loop')
        if 'SETTINGS_SMOKE_OK' not in output or any(s in output for s in bad):
            print(output)
            return 1
        print('Settings UI passed: overlay switch and the rows it hides, dwell, size, press style, '
              'recordings kept, Advanced audio and its fold summary, typed key; machine commands refused.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
