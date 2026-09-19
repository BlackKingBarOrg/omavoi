#!/usr/bin/env python3
"""Send real Qt key events through the console, without touching user data.

Uses an offscreen Window in place of the Wayland-only PanelWindow. All views
and key handlers come from the repository; subprocesses use an inert CLI.
"""
import os
from pathlib import Path
import subprocess
import tempfile

CHECKS = '''
    TestCase { id: keyboard; when: false }
    function check(value, message) { if (!value) throw new Error(message) }
    function field(item, name) {
      if (item.objectName === name) return item
      var children = item.children || []
      for (var i = 0; i < children.length; i++) {
        var found = panel.field(children[i], name); if (found) return found
      }
      return null
    }
    function pressEscape() { keyboard.keyClick(Qt.Key_Escape); keyboard.wait(20) }
    function showTab(tab) {
      root.tab = tab; root.opened = true
      panel.requestActivate(); keyboard.wait(100)
    }
    Timer {
      interval: 300; running: true
      onTriggered: {
        try {
          root.setupReport = {ready: true, done: 5, total: 5, steps: []}
          panel.showTab("dictionary")
          panel.field(dictionaryView, "dictionarySearch").forceActiveFocus()
          panel.pressEscape()
          panel.check(!root.opened, "Escape in dictionary search did not close console")
          panel.showTab("dictionary")
          dictionaryView.openEditor(null)
          panel.pressEscape()
          panel.check(!dictionaryView.editing && root.opened, "Escape should close editor first")
          panel.pressEscape()
          panel.check(!root.opened, "Second Escape after editor did not close console")
          panel.showTab("dictionary")
          dictionaryView.openEditor(null)
          panel.field(dictionaryView, "dictionarySpelling").text = "Unsaved draft"
          panel.pressEscape()
          panel.check(dictionaryView.editing && dictionaryView.discardPrompt && root.opened,
                "Escape discarded unsaved changes")
          dictionaryView.editing = false
          dictionaryView.discardPrompt = false
          panel.showTab("history")
          historyView.menuTake = {id: "test", text: "test"}
          panel.pressEscape()
          panel.check(!historyView.menuOpen && root.opened, "Escape should dismiss history menu first")
          panel.pressEscape()
          panel.check(!root.opened, "Escape in history did not close console")
          panel.showTab("settings")
          confirmClear.opened = true
          panel.pressEscape()
          panel.check(!confirmClear.opened && root.opened, "Escape should dismiss confirmation first")
          panel.pressEscape()
          panel.check(!root.opened, "Escape in settings did not close console")
          panel.showTab("modes")
          panel.pressEscape()
          panel.check(!root.opened, "Escape after switching tabs did not close console")
          panel.showTab("models")
          panel.pressEscape()
          panel.check(!root.opened, "Escape in models did not close console")
          console.log("ESCAPE_SMOKE_OK")
        } catch(e) { console.error("ESCAPE_SMOKE_FAILED", e) }
        Qt.quit()
      }
    }
'''


def main():
    repo = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix='omavoi-escape-') as tmp:
        work = Path(tmp)
        for name in ('Commons', 'Ui'):
            (work/name).symlink_to(Path('/usr/share/omarchy/shell')/name)
        plugin = work/'Plugin'
        plugin.mkdir()
        for source in repo.glob('*.qml'):
            if source.name != 'Console.qml':
                (plugin/source.name).symlink_to(source)
        console = (repo/'Console.qml').read_text()
        console = console.replace('import QtQuick\n', 'import QtQuick\nimport QtQuick.Window as QtWindow\nimport QtTest\n', 1)
        console = console.replace('PanelWindow {', 'QtWindow.Window {', 1)
        console = console.replace('anchors { top: true; bottom: true; left: true; right: true }', 'width: 1200; height: 900', 1)
        console = '\n'.join(line for line in console.splitlines() if 'WlrLayershell.' not in line)
        console = console.replace('id: panel', 'id: panel\n' + CHECKS, 1)
        console = console.replace('DictionaryView {', 'DictionaryView {\n            id: dictionaryView', 1)
        (plugin/'Console.qml').write_text(console)
        (work/'shell.qml').write_text('import QtQuick\nimport "Plugin"\nConsole {}\n')
        cli = work/'omavoi'
        cli.write_text('#!/bin/sh\nprintf \'%s\\n\' \'{"ok":true,"entries":[],"modes":[]}\'\n')
        cli.chmod(0o700)
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                   PATH=str(work)+os.pathsep+os.environ['PATH'],
                   XDG_CONFIG_HOME=str(work/'config'), XDG_STATE_HOME=str(work/'state'),
                   XDG_DATA_HOME=str(work/'data'), XDG_RUNTIME_DIR=str(work/'runtime'))
        (work/'runtime').mkdir(mode=0o700)
        run = subprocess.run(['qs', '-p', str(work/'shell.qml'), '--no-color'],
                             env=env, text=True, capture_output=True, timeout=20)
        output = run.stdout + run.stderr
        if run.returncode or 'ESCAPE_SMOKE_OK' not in output or 'ESCAPE_SMOKE_FAILED' in output:
            print(output)
            return 1
        print('Escape passed: search, editor, unsaved draft, history menu, confirmation, tab switching, reopen.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
