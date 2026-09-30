#!/usr/bin/env python3
"""Record three seconds locally, play them back, then remove the recording.

Invoked only by the microphone test button. No speech engine or history is
involved. PipeWire's node name is an argv value, never a shell command.
"""
import argparse
import json
import math
import signal
import struct
import subprocess
import tempfile
import wave
from pathlib import Path


def interrupted(signum, frame):
    raise InterruptedError('Microphone test canceled')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', default='')
    args = parser.parse_args()
    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        with tempfile.TemporaryDirectory(prefix='omavoi-microphone-') as directory:
            path = Path(directory) / 'test.wav'
            command = ['pw-record', '--rate', '16000', '--channels', '1',
                       '--format', 's16', '--sample-count', '48000']
            if args.target:
                command += ['--target', args.target]
            subprocess.run(command + [str(path)], check=True, capture_output=True, timeout=8)
            with wave.open(str(path), 'rb') as recording:
                data = recording.readframes(recording.getnframes())
            samples = [v[0] for v in struct.iter_unpack('<h', data)]
            rms = math.sqrt(sum(v * v for v in samples) / max(1, len(samples))) / 32768
            subprocess.run(['pw-play', str(path)], check=True, capture_output=True, timeout=8)
            print(json.dumps({'ok': True, 'quiet': rms < 10 ** (-45 / 20)}))
    except (OSError, ValueError, wave.Error, subprocess.SubprocessError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}))
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
