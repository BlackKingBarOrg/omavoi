#!/usr/bin/env bash
#
# Run the clone you are editing, instead of the copy `omarchy plugin add` put in
# the plugins directory.
#
#   dev/link.sh          # development: the install path becomes a link to this clone
#   dev/link.sh --real   # installed: a real checkout, the way a user gets it
#   dev/link.sh --check  # which of the two is in place, and what it is running
#
# omarchy-shell loads plugins from ~/.config/omarchy/plugins/<id> and it follows
# a symlink there. Measured, with the shell fully restarted rather than asked:
# listPlugins reports the plugin enabled with all three of its kinds registered.
# So development needs no copy and no sync step — edit the clone,
# omarchy-restart-shell, done, and there is never a second place the code could
# be.
#
# What the link costs is `omarchy plugin validate`, which refuses a symlink
# anywhere inside a plugin folder and counts the folder itself. That is the
# marketplace gate rather than anything the shell enforces, so it matters before
# publishing and not before every edit. --real puts a genuine install back for
# it, through `omarchy plugin add` rather than a copy, because the thing worth
# reproducing is what a user actually gets.
#
# The link is also what makes the daemon repo's dev/reset.sh safe to run here:
# `omarchy plugin remove` unlinks rather than deletes when the target is a link,
# so a teardown cannot take the clone with it. A checkout that *is* the
# installed folder has no such protection.

set -uo pipefail

MODE=dev
case "${1:-}" in
  --real)  MODE=real ;;
  --check) MODE=check ;;
  "")      ;;
  *)       echo "usage: dev/link.sh [--real|--check]" >&2; exit 2 ;;
esac

CLONE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_ID="ai.bkblab.omavoi"
INSTALLED="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins/$PLUGIN_ID"

say() { printf '  %s\n' "$*"; }
step() { printf '\n%s\n' "$*"; }

[[ -f "$CLONE/manifest.json" ]] || { echo "not a plugin checkout: $CLONE" >&2; exit 1; }

# Refusing to throw away work is the whole of the safety here: everything else
# these modes touch is reproducible from git, and uncommitted changes are not.
dirty_at() { [[ -d "$1/.git" ]] && [[ -n "$(git -C "$1" status --porcelain 2>/dev/null)" ]]; }

if [[ "$MODE" == dev ]]; then
  step "1. what is at the install path now"
  if [[ -L "$INSTALLED" ]]; then
    say "a link to $(readlink "$INSTALLED") — replacing it"
    rm -f "$INSTALLED"
  elif [[ -d "$INSTALLED" ]]; then
    if dirty_at "$INSTALLED"; then
      echo "  the installed folder has uncommitted changes:" >&2
      git -C "$INSTALLED" status --short | sed 's/^/    /' >&2
      echo "  commit or move them first — this would delete them" >&2
      exit 1
    fi
    # Deleted rather than removed through omarchy: the id is replaced in the
    # same breath, so shell.json keeps pointing at something that exists, and
    # `omarchy plugin remove` would take the widget out of it for nothing.
    say "a real checkout with nothing uncommitted — removing it"
    rm -rf "$INSTALLED"
  else
    say "nothing installed"
  fi

  step "2. link it to this clone"
  mkdir -p "$(dirname "$INSTALLED")"
  ln -s "$CLONE" "$INSTALLED"
  say "$INSTALLED -> $CLONE"

  step "3. reload the shell"
  omarchy-restart-shell 2>&1 | sed 's/^/  /'

elif [[ "$MODE" == real ]]; then
  url="$(git -C "$CLONE" remote get-url origin 2>/dev/null)"
  [[ -n "$url" ]] || { echo "no origin remote on $CLONE" >&2; exit 1; }

  step "1. what this install will not have"
  if dirty_at "$CLONE"; then
    say "your clone has uncommitted changes, and a real install clones origin:"
    git -C "$CLONE" status --short | sed 's/^/    /'
  else
    unpushed="$(git -C "$CLONE" log --oneline '@{u}..HEAD' 2>/dev/null | wc -l)"
    if (( unpushed )); then
      say "$unpushed unpushed commit(s) — a real install clones origin and gets none of them"
    else
      say "nothing uncommitted, nothing unpushed"
    fi
  fi

  step "2. take the link out of the way"
  # Only ever the link: the clone lives elsewhere and is not this script's to
  # remove. A real folder already there is what --real is asking for.
  if [[ -L "$INSTALLED" ]]; then
    rm -f "$INSTALLED"
    say "removed the link"
    step "3. install it the way a user does"
    # `omarchy plugin add` refuses an id that is already installed, which is why
    # the link had to go first.
    omarchy plugin add "$url" --enable --yes 2>&1 | sed 's/^/  /'
  elif [[ -d "$INSTALLED" ]]; then
    say 'already a real checkout — move it on with: omarchy plugin update' "$PLUGIN_ID"
  else
    say "nothing there"
    step "3. install it the way a user does"
    omarchy plugin add "$url" --enable --yes 2>&1 | sed 's/^/  /'
  fi
fi

step "state"
if [[ -L "$INSTALLED" ]]; then
  target="$(readlink "$INSTALLED")"
  if [[ "$target" == "$CLONE" ]]; then
    say "development: install path -> this clone"
  else
    say "!! install path -> $target, which is not this clone"
  fi
elif [[ -d "$INSTALLED" ]]; then
  say "installed: a real checkout at the install path, not this clone"
  say "at $(git -C "$INSTALLED" rev-parse --short HEAD 2>/dev/null || echo '?')"
else
  say "!! nothing at $INSTALLED"
fi

if command -v omarchy-shell >/dev/null && [[ "$(omarchy-shell shell ping 2>/dev/null)" == ok ]]; then
  if omarchy-shell shell listPlugins 2>/dev/null | grep -q "\"$PLUGIN_ID\""; then
    say "the shell has it loaded"
  else
    say "!! the shell does not have it loaded"
  fi
else
  say "shell not answering, so nothing to say about what it loaded"
fi

branch="$(git -C "$CLONE" branch --show-current 2>/dev/null)"
say "clone on ${branch:-detached} at $(git -C "$CLONE" rev-parse --short HEAD 2>/dev/null), $(git -C "$CLONE" status --porcelain 2>/dev/null | wc -l) uncommitted change(s)"

# Named rather than run: validate fails by design while linked, and a failure
# printed on every development run is a failure nobody reads.
if [[ -L "$INSTALLED" ]]; then
  say "omarchy plugin validate will refuse the link — dev/link.sh --real before publishing"
fi
