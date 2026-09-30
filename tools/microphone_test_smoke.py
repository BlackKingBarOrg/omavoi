#!/usr/bin/env python3
"""Check the microphone test with fake PipeWire processes; never record audio."""
import contextlib
import io
import json
import signal
import subprocess
import sys
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import microphone_test


class MicrophoneTest(unittest.TestCase):
    def exercise(self, *, fail_playback=False, interrupt_recording=False):
        recorded = []
        target = 'microphone $(not-a-command)'

        def run(argv, **kwargs):
            if argv[0] == 'pw-record':
                self.assertEqual(argv[argv.index('--target') + 1], target)
                path = Path(argv[-1])
                recorded.append(path)
                with wave.open(str(path), 'wb') as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(16000)
                    wav.writeframes(b'\x00\x00' * 48000)
                if interrupt_recording:
                    signal.raise_signal(signal.SIGTERM)
            elif argv[0] == 'pw-play':
                self.assertTrue(recorded[0].is_file())
                if fail_playback:
                    raise subprocess.CalledProcessError(1, argv)
            else:
                self.fail('Unexpected process: ' + argv[0])
            return subprocess.CompletedProcess(argv, 0)

        out = io.StringIO()
        with patch.object(sys, 'argv', ['microphone_test.py', '--target', target]), \
             patch.object(subprocess, 'run', run), contextlib.redirect_stdout(out):
            code = microphone_test.main()
        self.assertFalse(recorded[0].exists(), 'Temporary recording leaked')
        self.assertFalse(recorded[0].parent.exists(), 'Temporary directory leaked')
        return code, json.loads(out.getvalue())

    def test_quiet_recording_and_cleanup(self):
        code, result = self.exercise()
        self.assertEqual(code, 0)
        self.assertTrue(result['quiet'])

    def test_playback_failure_still_cleans_up(self):
        code, result = self.exercise(fail_playback=True)
        self.assertEqual(code, 1)
        self.assertFalse(result['ok'])

    def test_closed_view_still_cleans_up(self):
        code, result = self.exercise(interrupt_recording=True)
        self.assertEqual(code, 1)
        self.assertFalse(result['ok'])


if __name__ == '__main__':
    unittest.main()
