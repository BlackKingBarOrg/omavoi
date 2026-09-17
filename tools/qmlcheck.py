#!/usr/bin/env python3
"""Does every .qml file still parse?

qmllint answers this properly, and it is installed — just not on PATH:
qt6-declarative puts it in /usr/lib/qt6/bin, which is why an earlier version
of this file said it was unavailable and reimplemented a fraction of it. So
this runs qmllint when it can find it and falls back to the bracket scan
below when it cannot, and says which of the two it did.

The fallback answers one question, and it is the question that has actually
gone wrong: an edit that rewrites one line of a multi-line expression leaves
the continuation lines orphaned, and QML then fails to load with an error
naming a line some distance from the damage. That has happened twice, both
times from a mechanical edit of mine.

A naive version of this check reported two false positives, because
stripping `//` comments first also eats the inside of

    u.replace(/^[a-z]+:\\/\\//, "")

and with it the closing paren. So this tokenises in one pass instead:
strings, template literals, regex literals and comments are all recognised
where they start, not by pattern order. A regex literal is distinguished
from division by what precedes it — division follows a value, a regex
follows an operator or an opening bracket.

Usage: tools/qmlcheck.py [files...]   (default: every *.qml beside it)
Exit 1 on a syntax error, so it can gate a commit. Warnings are not failures:
qmllint has a great deal to say about a Quickshell plugin's imports that is
true of every file here and actionable in none of them.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PAIRS = {"{": "}", "(": ")", "[": "]"}
CLOSERS = {v: k for k, v in PAIRS.items()}
# A `/` here starts a regex, not a division: nothing to divide.
BEFORE_REGEX = set("(,=:[!&|?{};+-*%~^<>") | {""}
KEYWORDS_BEFORE_REGEX = ("return", "typeof", "case", "in", "of", "new", "delete")


def _prev_significant(text: str, i: int) -> str:
    """The last non-space character before i, or a keyword ending there."""
    j = i - 1
    while j >= 0 and text[j] in " \t\r\n":
        j -= 1
    if j < 0:
        return ""
    for kw in KEYWORDS_BEFORE_REGEX:
        if text[: j + 1].endswith(kw):
            k = j - len(kw)
            if k < 0 or not (text[k].isalnum() or text[k] == "_"):
                return "="  # behaves like an operator
    return text[j]


def imbalances(text: str) -> list[str]:
    """Unclosed or unopened brackets, as human-readable lines."""
    stack: list[tuple[str, int]] = []
    problems: list[str] = []
    line = 1
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        two = text[i : i + 2]
        if two == "//":
            i = text.find("\n", i)
            if i < 0:
                break
            continue
        if two == "/*":
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            line += text.count("\n", i, end)
            i = end
            continue
        if c in "\"'`":
            i += 1
            while i < n and text[i] != c:
                if text[i] == "\\":
                    i += 1
                elif text[i] == "\n":
                    line += 1          # only legal inside a template literal
                i += 1
            i += 1
            continue
        if c == "/" and _prev_significant(text, i) in BEFORE_REGEX:
            i += 1
            in_class = False
            while i < n and (in_class or text[i] != "/"):
                if text[i] == "\\":
                    i += 1
                elif text[i] == "[":
                    in_class = True
                elif text[i] == "]":
                    in_class = False
                elif text[i] == "\n":
                    break              # an unterminated regex is not one
                i += 1
            i += 1
            continue
        if c in PAIRS:
            stack.append((c, line))
        elif c in CLOSERS:
            if not stack:
                problems.append(f"line {line}: a stray {c!r} closes nothing")
            elif stack[-1][0] != CLOSERS[c]:
                opener, opened = stack.pop()
                problems.append(
                    f"line {line}: {c!r} closes the {opener!r} opened on line {opened}"
                )
            else:
                stack.pop()
        i += 1
    problems += [f"line {ln}: {ch!r} is never closed" for ch, ln in stack]
    return problems


# Where qt6-declarative puts it, plus PATH in case a future version is there.
QMLLINT = ("/usr/lib/qt6/bin/qmllint", "/usr/lib64/qt6/bin/qmllint", "qmllint")


def _qmllint() -> str | None:
    for candidate in QMLLINT:
        found = candidate if os.path.isabs(candidate) else shutil.which(candidate)
        if found and os.access(found, os.X_OK):
            return found
    return None


# `command(...)` is run as `bash -lc`; `commandArgs([...])` is argv with no
# shell at all. JSON.stringify inside the first is the tell that somebody
# knew the value needed quoting and reached for the wrong kind: it escapes "
# and \ for JSON, and leaves $(…) and backticks to be run by the shell.
#
# That is how a dictionary key, a proper noun, a base_url and a model id —
# four things typed into text boxes — reached a command line. The values
# still go through, unquoted and verbatim, as argv.
_SHELL_QUOTED = re.compile(r"\bcommand\((?:[^()]|\([^()]*\))*JSON\.stringify")


def shell_quoting(text: str) -> list[str]:
    """Places that JSON-quote a value on its way into a shell string."""
    out = []
    for match in _SHELL_QUOTED.finditer(text):
        out.append(f"line {text[: match.start()].count(chr(10)) + 1}: "
                   "JSON.stringify inside command() — JSON quoting is not shell "
                   "quoting; use commandArgs([...]) and pass the value as argv")
    return out


def main(argv: list[str]) -> int:
    here = Path(__file__).resolve().parent.parent
    files = [Path(a) for a in argv] or sorted(here.glob("*.qml"))

    linter = _qmllint()
    if linter is not None:
        proc = subprocess.run([linter, *[str(f) for f in files]],
                              capture_output=True, text=True, check=False)
        # Only syntax: qmllint cannot resolve qs.Commons or Quickshell.Io from
        # outside a shell, so its import and type warnings are noise here.
        errors = [ln for ln in (proc.stdout + proc.stderr).splitlines()
                  if "[syntax]" in ln or ln.lstrip().startswith("error:")]
        for f in files:
            errors += [f"{f.name}: {p}" for p in shell_quoting(f.read_text())]
        if errors:
            print("\n".join(errors))
            print(f"\n{len(errors)} problem(s) in {len(files)} file(s)")
            return 1
        print(f"qmllint: {len(files)} file(s) parse, no shell-quoted values")
        return 0

    bad = 0
    for f in files:
        text = f.read_text()
        for problem in [*imbalances(text), *shell_quoting(text)]:
            print(f"{f.name}: {problem}")
            bad += 1
    if bad:
        print(f"\n{bad} problem(s) in {len(files)} file(s)")
        return 1
    print(f"no qmllint found; brackets balanced in {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
