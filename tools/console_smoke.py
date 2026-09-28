#!/usr/bin/env python3
"""Drive the whole console against an isolated configuration.

What the tab tests cannot reach, because it lives in Console.qml: deleting a
take from the history menu, and landing on the take that took its place;
switching the interface language from the header, and every label following
it; clearing the history through the confirmation dialog, and the empty list
that is left. Also that the header fits: nothing in it runs past the card.

Console.qml is copied with its PanelWindow turned into a Rectangle, since the
offscreen platform has no layer shell, and its login-shell runner turned into
a plain `sh -c` -- a login shell reads the profile, which can put the real
`omavoi` ahead of the isolated one on PATH. The runtime directory is a
temporary one, so the console's IpcLink finds no daemon to talk to.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ui_shots import takes  # noqa: E402  -- the same made-up takes the photographs use

PLUGIN = Path(__file__).resolve().parent.parent

QML = r'''import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons
import "Plugin"
Window {
  id: window
  width: __W__; height: __H__; visible: true; color: "#101010"
  property int step: 0
  property int ticks: 0
  property var before: []
  Strings { id: de; lang: "de" }
  Strings { id: tr; lang: __LANG__ }
  Console { id: con; anchors.fill: parent }
  Component.onCompleted: con.open(JSON.stringify({ tab: "history" }))

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
  function one(test, what) { var r = all(window.contentItem, test); if (!r.length) throw new Error("no " + what); return r[0] }
  function history() { return one(function(i) { return i.menuActions !== undefined && typeof i.openMenu === "function" }, "history view") }
  function picker() { return one(function(i) { return i.showLabel === false && i.options !== undefined }, "language picker") }
  function dialog() { return one(function(i) { return i.confirmText !== undefined && i.opened !== undefined }, "confirmation dialog") }
  function visibleTexts() { return all(window.contentItem, function(i) { return typeof i.text === "string" && i.font !== undefined && i.visible }).map(function(i) { return i.text }) }
  function check(v, m) { if (!v) throw new Error(m) }

  Timer {
    interval: 250; repeat: true; running: true
    onTriggered: {
      try {
        if (++window.ticks > 480) throw new Error("Timed out at step " + window.step)
        switch (window.step) {
          case 0:
            if (!con.ready || con.takes.length !== __TAKES__) return
            // The header, at this size: nothing in it past the card's edge.
            // By its size: a Rectangle reads border.width 1 whether or not it
            // draws one, and the backdrop is a Rectangle the window's width.
            var card = one(function(i) { return i.border !== undefined && i.width > window.width / 2 && i.width < window.width - 10 && i.height > window.height / 2 }, "card")
            var header = all(card, function(i) { return typeof i.text === "string" && i.font !== undefined && i.visible && i.text !== "" && i.mapToItem(card, 0, 0).y < 60 })
            // The name, six tabs and the state, at least.
            check(header.length >= 8, "found " + header.length + " texts in the header, not the whole row")
            for (var h = 0; h < header.length; h++) {
              // What is painted, not the item: a layout short of room shrinks a
              // text's box and the text goes on past it.
              var right = header[h].mapToItem(card, 0, 0).x + Math.max(header[h].width, header[h].paintedWidth || 0)
              check(right <= card.width, "the header's \"" + header[h].text + "\" runs past the card: " + Math.round(right) + " > " + Math.round(card.width))
            }
            window.before = con.takes.map(function(t) { return t.id })
            var hv = history()
            hv.openMenu(con.takes[1], 1, { x: 40, y: 40 })
            check(con.selected === 1, "the menu did not select the row it was opened on")
            hv.fire("delete")
            break
          case 1:
            if (con.takes.length !== __TAKES__ - 1) return
            var ids = con.takes.map(function(t) { return t.id })
            check(ids.indexOf(window.before[1]) < 0, "the take the menu was opened on is still there")
            check(con.selected === 1 && ids[1] === window.before[2], "the selection did not land on the take that took its place")
            picker().changed("de")
            break
          case 2:
            if (con.tabs[0].label !== de.t("nav.history")) return
            var shown = visibleTexts()
            check(shown.indexOf(de.t("nav.settings")) >= 0, "the header's tabs did not follow the language")
            check(picker().value === "de", "the picker does not show the language it switched to: " + picker().value)
            picker().changed(tr.active)
            break
          case 3:
            if (con.tabs[0].label !== tr.t("nav.history")) return
            con.tab = "settings"
            break
          case 4:
            var clear = one(function(i) { return i.text === tr.t("set.clearhistory") && typeof i.clicked === "function" && i.visible }, "clear-history button")
            clear.clicked()
            check(dialog().opened === true, "clearing the history did not ask first")
            check(con.takes.length === __TAKES__ - 1, "the history went before the question was answered")
            dialog().confirmed()
            break
          case 5:
            if (con.takes.length !== 0) return
            check(dialog().opened === false, "the dialog stayed up after it was answered")
            con.tab = "history"
            break
          case 6:
            var empty = tr.tf("hist.none", tr.t("hist.yourkey"))
            if (visibleTexts().indexOf(empty) < 0) return
            console.log("CONSOLE_SMOKE_OK")
            Qt.quit()
            return
        }
        window.step++
      } catch (e) { console.error("CONSOLE_SMOKE_FAILED", e); Qt.quit() }
    }
  }
}
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--daemon', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--language', default='zh')
    # A 1366-pixel laptop screen: the console's card is 80 pixels narrower.
    parser.add_argument('--width', type=int, default=1366)
    parser.add_argument('--height', type=int, default=768)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='omavoi-console-') as temp:
        work = Path(temp)
        for name in ('Commons', 'Ui'):
            (work/name).symlink_to(Path('/usr/share/omarchy/shell')/name)
        plugin = work/'Plugin'
        plugin.mkdir()
        for f in PLUGIN.iterdir():
            if f.name not in ('Console.qml', '.git'):
                (plugin/f.name).symlink_to(f)
        src = (PLUGIN/'Console.qml').read_text(encoding='utf-8')
        for old, new in (('  PanelWindow {\n    id: panel', '  Rectangle {\n    id: panel'),
                         ('anchors { top: true; bottom: true; left: true; right: true }', 'anchors.fill: parent'),
                         ('["bash", "-lc", cmd]', '["sh", "-c", cmd]')):
            if old not in src:
                print(f'Console.qml no longer has {old!r}; this test needs updating')
                return 1
            src = src.replace(old, new)
        src = re.sub(r'^\s*WlrLayershell\.[^\n]*\n', '', src, flags=re.M)
        (plugin/'Console.qml').write_text(src, encoding='utf-8')
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
        entries = takes()
        with open(work/'state'/'omavoi'/'history.jsonl', 'w', encoding='utf-8') as fh:
            for entry in entries:
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
        for key, value in {'__LANG__': args.language, '__W__': args.width, '__H__': args.height,
                           '__TAKES__': len(entries)}.items():
            qml = qml.replace(key, json.dumps(value))
        (work/'shell.qml').write_text(qml, encoding='utf-8')
        run = subprocess.run(['qs', '-p', str(work/'shell.qml'), '--no-color'],
                             env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen',
                                  'XDG_RUNTIME_DIR': str(work/'run'),
                                  'PATH': f"{bindir}:{os.environ.get('PATH', '')}"},
                             capture_output=True, text=True, timeout=240)
        output = run.stdout + run.stderr
        bad = ('FAILED', 'ReferenceError', 'TypeError', 'Unable to assign', 'Binding loop', 'binding loop')
        if 'CONSOLE_SMOKE_OK' not in output or any(s in output for s in bad):
            print(output)
            return 1
        print(f'Console passed at {args.width}x{args.height}: header fits, delete from the menu lands on the next take, '
              'language switch from the header, clear history through the dialog.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
