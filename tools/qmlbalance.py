#!/usr/bin/env python3
"""Are the brackets balanced in every .qml file?

Not a substitute for qmllint, which is not installed here. It answers one
question, and it is the question that has actually gone wrong: an edit that
rewrites one line of a multi-line expression leaves the continuation lines
orphaned, and QML then fails to load with an error naming a line some
distance from the damage. That has happened twice, both times from a
mechanical edit of mine.

A naive version of this check reported two false positives, because
stripping `//` comments first also eats the inside of

    u.replace(/^[a-z]+:\\/\\//, "")

and with it the closing paren. So this tokenises in one pass instead:
strings, template literals, regex literals and comments are all recognised
where they start, not by pattern order. A regex literal is distinguished
from division by what precedes it — division follows a value, a regex
follows an operator or an opening bracket.

Usage: tools/qmlbalance.py [files...]   (default: every *.qml beside it)
Exit 1 if anything is unbalanced, so it can gate a commit.
"""

from __future__ import annotations

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


def main(argv: list[str]) -> int:
    here = Path(__file__).resolve().parent.parent
    files = [Path(a) for a in argv] or sorted(here.glob("*.qml"))
    bad = 0
    for f in files:
        for problem in imbalances(f.read_text()):
            print(f"{f.name}: {problem}")
            bad += 1
    if bad:
        print(f"\n{bad} problem(s) in {len(files)} file(s)")
        return 1
    print(f"brackets balanced in {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
