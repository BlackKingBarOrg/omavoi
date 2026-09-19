#!/usr/bin/env python3
"""The daemon pin in DaemonSource.qml: exactly one, a full commit, and current.

`check_pin.py` fails unless the pinned value is a 40-hex commit. Given a checkout
of the daemon it also fails when that checkout's HEAD is a different commit that
is already on its origin/master -- i.e. when the daemon moved and the plugin did
not. `--sync` rewrites the pin to that HEAD.

The checkout is looked for in three places, in order: a path argument,
$OMAVOI_DAEMON, then a sibling directory named omavoi-daemon. The sibling
default holds for a plugin checkout kept next to the daemon's, which is where
this file was written. It does not hold for the copy that is also the *installed*
plugin: that one lives in ~/.config/omarchy/plugins, and the only way to give it
a sibling there is to put a symlink into Omarchy's trusted plugins directory --
which is the exact thing `omarchy plugin validate`'s no-symlink rule exists to
prevent. Anyone who both uses and edits this plugin has one checkout doing both
jobs, so the sibling cannot be assumed; hence the two overrides above it.

Without any of the three the pin is still checked for shape, and only the "has
the daemon moved" half is skipped. An override that names a directory which is
not a git checkout is an error rather than a silent fall-through: it was asked
for explicitly.

Why a pin at all: the marketplace's security baseline blocks unpinned remote
Git sources that get built and run, and a listing is itself a pinned commit.
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
QML = os.path.join(HERE, "..", "DaemonSource.qml")
PIN = re.compile(r'readonly property string sha: "([0-9a-f]*)"')

def current():
    s = open(QML, encoding="utf-8").read()
    m = PIN.findall(s)
    if len(m) != 1:
        sys.exit(f"DaemonSource.qml: expected exactly one sha, found {len(m)}")
    return s, m[0]

def daemon_dir():
    """(path, where) for the daemon checkout; path is None when there is none."""
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    for path, where in ((args[0] if args else None, "argument"),
                        (os.environ.get("OMAVOI_DAEMON"), "$OMAVOI_DAEMON")):
        if path:
            if not os.path.exists(os.path.join(path, ".git")):
                sys.exit(f"{where}: not a git checkout: {path}")
            return path, f"{where} {path}"
    # Only the daemon's own name. A bare "omavoi" was in this list until the
    # repositories were renamed, and it now names *this* checkout -- which is a
    # git repository, so it would be accepted and the pin synced to a plugin
    # commit.
    for name in ("omavoi-daemon", "Omavoi-daemon"):
        path = os.path.join(HERE, "..", "..", name)
        if os.path.exists(os.path.join(path, ".git")):
            return path, f"sibling ../../{name}"
    return None, "no argument, no $OMAVOI_DAEMON, no sibling omavoi-daemon checkout"

def daemon_head():
    """(sha, where) for a HEAD that can actually be fetched; sha is None otherwise."""
    path, where = daemon_dir()
    if path is None:
        return None, where
    run = lambda *a: subprocess.run(["git", "-C", path, *a], capture_output=True, text=True)
    head = run("rev-parse", "HEAD").stdout.strip()
    # Only a HEAD that is already published counts: a pin nobody can fetch is worse than a stale one.
    if run("merge-base", "--is-ancestor", head, "origin/master").returncode != 0:
        return None, f"{where}: HEAD {head[:7] or '?'} is not on origin/master yet"
    return head, where

s, sha = current()
problems = []
if not re.fullmatch(r"[0-9a-f]{40}", sha):
    problems.append(f"pin is not a 40-hex commit: {sha!r}")
head, where = daemon_head()
if "--sync" in sys.argv:
    if head is None:
        sys.exit(f"--sync: no daemon checkout to read a published HEAD from -- {where}")
    if head != sha:
        open(QML, "w", encoding="utf-8").write(s.replace(sha, head))
        print(f"pin: {sha[:7]} -> {head[:7]}  (from {where})")
    else:
        print(f"pin already at {head[:7]}  (from {where})")
    sys.exit(0)
if head and head != sha:
    problems.append(f"daemon HEAD {head[:7]} is published but the pin is {sha[:7]}; run: python3 tools/check_pin.py --sync")
for p in problems:
    print("  " + p)
if problems:
    sys.exit(1)
print(f"pin ok: {sha[:7]}" + (f" (matches daemon HEAD, from {where})" if head else f" (daemon HEAD not checked: {where})"))
