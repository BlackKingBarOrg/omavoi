#!/usr/bin/env python3
"""The daemon pin in DaemonSource.qml: exactly one, a full commit, and current.

`check_pin.py` fails unless the pinned value is a 40-hex commit. With a sibling
checkout of the daemon at ../Omavoi it also fails when that checkout's HEAD is
a different commit that is already on its origin/master -- i.e. when the daemon
moved and the plugin did not. `--sync` rewrites the pin to that HEAD.

Why a pin at all: the marketplace's security baseline blocks unpinned remote
Git sources that get built and run, and a listing is itself a pinned commit.
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
QML = os.path.join(HERE, "..", "DaemonSource.qml")
DAEMON = os.path.join(HERE, "..", "..", "Omavoi")
PIN = re.compile(r'readonly property string sha: "([0-9a-f]*)"')

def current():
    s = open(QML, encoding="utf-8").read()
    m = PIN.findall(s)
    if len(m) != 1:
        sys.exit(f"DaemonSource.qml: expected exactly one sha, found {len(m)}")
    return s, m[0]

def daemon_head():
    if not os.path.isdir(os.path.join(DAEMON, ".git")):
        return None
    run = lambda *a: subprocess.run(["git", "-C", DAEMON, *a], capture_output=True, text=True)
    head = run("rev-parse", "HEAD").stdout.strip()
    # Only a HEAD that is already published counts: a pin nobody can fetch is worse than a stale one.
    published = run("merge-base", "--is-ancestor", head, "origin/master").returncode == 0
    return head if published else None

s, sha = current()
problems = []
if not re.fullmatch(r"[0-9a-f]{40}", sha):
    problems.append(f"pin is not a 40-hex commit: {sha!r}")
head = daemon_head()
if "--sync" in sys.argv:
    if head is None:
        sys.exit("--sync: no sibling daemon checkout at ../Omavoi with a published HEAD")
    if head != sha:
        open(QML, "w", encoding="utf-8").write(s.replace(sha, head))
        print(f"pin: {sha[:7]} -> {head[:7]}")
    else:
        print(f"pin already at {head[:7]}")
    sys.exit(0)
if head and head != sha:
    problems.append(f"daemon HEAD {head[:7]} is published but the pin is {sha[:7]}; run: python3 tools/check_pin.py --sync")
for p in problems:
    print("  " + p)
if problems:
    sys.exit(1)
print(f"pin ok: {sha[:7]}" + (" (matches daemon HEAD)" if head else ""))
