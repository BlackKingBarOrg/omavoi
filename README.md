# Omavoi — Omarchy shell plugin

![Omavoi: hold a key, talk, and the text lands where you were typing](preview.png)

The desktop half of [Omavoi](https://github.com/BlackKingBarOrg/omavoi): voice
dictation for Omarchy and Hyprland. Hold a key, talk, and the text lands in
whatever window you were already typing into. Speech runs on your own GPU
through whisper.cpp; audio never leaves the machine.

This repository is the recording HUD, the bar module, and the five-tab console.
It is what you install.

## Install

```sh
omarchy plugin add https://github.com/BlackKingBarOrg/omavoi-shell-plugin --enable --yes
```

Then open the console — click the Omavoi module in the bar; `SUPER + ALT + V`
is bound by setup's last step, so it works from then on — and the
first-run screen takes it from there: it asks which language you want the
interface in and which speech model to use, then does the rest itself. Its
last step adds the three things a plugin cannot add for itself — the systemd
unit, the keybinding, and an Omavoi row in the Omarchy menu under
`SUPER + SPACE`.

## What it looks like

The strip that appears while you hold the key — pre-roll bars on the left,
the live meter, the clock — and the bar module beside your tray:

<p>
  <img src="docs/img/hud-recording.png" alt="The recording HUD: a small strip with a level meter and a timer" height="96">
  &nbsp;&nbsp;
  <img src="docs/img/bar-recording.png" alt="The bar module while recording, showing the elapsed time" height="88">
  &nbsp;&nbsp;
  <img src="docs/img/menu.png" alt="Omavoi in the Omarchy application menu" height="150">
</p>

The console — `SUPER + ALT + V`, the bar module, or the Omarchy menu — is
where everything is configured. Every step of a mode is on one screen: what
the speech model is told, the deterministic rules, the optional LLM steps, and
how the text is typed.

The history tab keeps every take with the numbers behind it. Right-click one
to copy its text, play the recording back, or delete it — the recording goes
with the take — and Settings has the button that clears the lot.

| Modes | Models |
|---|---|
| ![Modes: speech settings, rules, LLM steps and injection for one mode](docs/img/console-modes.webp) | ![Models: speech engines and weights, LLM configurations, and the VRAM in use](docs/img/console-models.webp) |

| Settings | Dictionary |
|---|---|
| ![Settings: hotkey, audio, HUD, history, update](docs/img/console-settings.webp) | ![Dictionary: heard → meant rules and names](docs/img/console-dictionary.webp) |

The same console in 简体中文 and ไทย — one of eight languages, picked from the
dropdown in the top bar:

| 简体中文 | ไทย |
|---|---|
| ![The Modes tab in Simplified Chinese](docs/img/console-modes-zh.webp) | ![The Modes tab in Thai](docs/img/console-modes-th.webp) |

## Why this is a separate repository

`omarchy-shell` is a single Quickshell process that also draws your bar, your
notifications and your lock screen. A plugin is QML running *inside* it, and
Quickshell exposes no way to read the microphone — its Pipewire service is
volume and routing, not samples — and no way to read an input device. The
pre-roll ring buffer that keeps the first syllable, and a push-to-talk key read
below xkb so a modifier works at all, both need a process of their own.

So the model, the microphone and the hotkey live in a daemon, and this plugin
talks to it over a Unix socket. The daemon is a Python package in the
[main repository](https://github.com/BlackKingBarOrg/omavoi); the first-run
screen installs it for you.

That split has one more benefit worth naming: the daemon survives
`omarchy-restart-shell`. Change your theme and dictation keeps working, with
the weights still resident, instead of reloading three gigabytes.

## What the first-run screen does

Nothing until you press it, and it shows the exact command first. Omarchy
deliberately runs nothing from inside a plugin folder — a plugin lands in a
trusted directory and is not itself trusted — so the screen asks instead.

| | needs root |
|---|---|
| system packages: `uv`, `whisper-cpp`, `ggml`, `ggml-vulkan`, `llama-cpp`, `xdotool`, and adding you to the `input` group | yes — one `pkexec` prompt, drawn by Omarchy's own polkit agent |
| the daemon — `uv tool install` of the main repository, pinned to one commit | no |
| the speech model, if you do not already have usable weights on disk | no |
| the systemd user unit, the `SUPER + ALT + V` keybinding, the Omarchy menu entry | no |

Existing `ggml` weights are found and reused rather than downloaded again, so
if another tool already put a 3 GB model on this machine, that step is free.

The daemon is installed at the exact commit named in `DaemonSource.qml`, so
what a given plugin commit installs is itself fixed. Bumping it is
`python3 tools/check_pin.py --sync` against a checkout of the main repository.

### The `input` group

Reading a key below the keyboard layout means reading `/dev/input/event*`,
which is `crw-rw---- root input`. A group is granted at login, and the login
that runs the first-run screen predates its own `usermod -aG input` by one
step — so the last step starts the daemon through `newgrp`, which is setuid
root and re-reads `/etc/group`, and the key works the moment setup finishes.
That override is a single file under `$XDG_RUNTIME_DIR/systemd/user/`, which
logind clears when the session ends; the next login has the group itself and
needs none. Nothing on disk changes, and a login that already has the group
gets no override.

## Dependencies

Everything outside this repository, and where it comes from:

| | package / source | why |
|---|---|---|
| whisper.cpp | `whisper-cpp`, `ggml`, `ggml-vulkan` (Arch extra) | the speech model, on any GPU through Vulkan |
| llama.cpp | `llama-cpp` (Arch extra) | modes with a local LLM step; optional in practice |
| xdotool | `xdotool` (Arch extra) | typing into XWayland windows — WeChat, Feishu, Steam |
| uv | `uv` (Arch extra) | installs the daemon |
| the daemon | [BlackKingBarOrg/omavoi](https://github.com/BlackKingBarOrg/omavoi), MIT, pinned commit | the model, the microphone, the hotkey |
| model weights | downloaded on request from Hugging Face; never bundled | 0.5–3 GB depending on the model |

The plugin itself is QML only and ships no binaries. It never runs anything
as root except the one `pkexec pacman`/`usermod` line the first-run screen
prints before asking.

## Uninstall

```sh
~/.config/omarchy/plugins/ai.bkblab.omavoi/install.sh --remove
omarchy plugin remove ai.bkblab.omavoi
```

The first line takes out the systemd unit, the keybinding, the menu entry and
its icon, and the runtime `newgrp` override if one was written; `bindings.lua`
is edited between markers, so it removes exactly what was added and leaves the
rest of the file byte for byte as it was. The daemon,
your config and any downloaded weights are left alone — see the main
repository to remove those too.

MIT.
