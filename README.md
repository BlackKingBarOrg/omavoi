# Omavoi

Voice dictation for [Omarchy](https://omarchy.org) and Hyprland. Hold a key,
talk, and the text lands in whatever window you were already typing into.
Everything runs on your own machine.

```
                 hold RIGHTALT ─────────────────────────┐
                                                        ▼
  ring buffer ──▶ speech model ──▶ rules ──▶ LLM (opt) ──▶ your window
   (pre-roll)      whisper.cpp     dictionary,  per mode      wtype or
                   or CUDA         names, …                   paste
```

## Why three pieces

`omarchy-shell` is a single Quickshell process that also draws your bar,
notifications and lock screen. A plugin is QML running *inside* it, so a
speech model, CUDA and a microphone reader cannot live there. Omavoi is
therefore:

| | what it is | how it installs |
|---|---|---|
| `omavoid` | the daemon: model, microphone, hotkey, typing | `uv tool install omavoi` |
| model weights | 3 GB, never shipped | downloaded on first run |
| `ai.bkblab.omavoi` | the QML plugin: bar module, HUD, console | `omarchy plugin add` |

The plugin talks to the daemon over a Unix socket and never installs anything
itself — Omarchy deliberately runs nothing from inside a plugin folder. The
first-run screen asks instead, and prints every command before it runs.

## Install

```bash
# 1. the speech engine (Vulkan runs on NVIDIA, AMD and Intel alike)
sudo pacman -S --needed whisper-cpp ggml-cpu ggml-vulkan

# 2. the daemon
uv tool install omavoi
systemctl --user enable --now omavoid

# 3. weights, and whatever is still missing
omavoi setup
```

`ggml-cpu` is **not** optional. Arch ships ggml's compute backends as separate
packages, and whisper still asks for a CPU device for the tensors it does not
offload. With only the GPU plugin installed it aborts part-way through loading
the model on `GGML_ASSERT(device)`, and the backtrace says nothing useful.

For the desktop pieces:

```bash
omarchy plugin add https://github.com/BlackKingBarOrg/omavoi
omarchy plugin enable ai.bkblab.omavoi right
~/.config/omarchy/plugins/ai.bkblab.omavoi/install.sh   # unit, keybinding
```

The hotkey is read from evdev, which needs membership of the `input` group and
a fresh login. Until then `omavoi setup` will offer a Hyprland binding on a
non-modifier key instead — a modifier cannot be bound that way, because
pressing one changes the modmask, which fires the release binding immediately
and records a 0.0 s take.

## What it does that a transcribe-and-paste script does not

**Pre-roll.** PipeWire needs a few hundred milliseconds to open a stream, and
people start talking the instant they press the key. So the microphone runs
continuously into a small ring buffer and a take is sliced out of it starting
*before* the keypress. Start-on-press throws that speech away; it is the single
biggest cause of dropped leading words.

**Modes are chains of models.** A mode is picked by the focused window and
decides what the speech model is told, which rules run, which LLM passes
follow, and how the text is injected. A terminal strips the trailing full stop
and cannot afford an LLM round-trip; prose can. An LLM step that fails or times
out falls through to the text it was given — a slow model degrades your
dictation, it never swallows it.

**Two kinds of correction.** A dictionary rule (`heard -> meant`) needs you to
know what the model got wrong. For a proper noun you never will, and for
Chinese the manglings are an open set of homophones — 李文渊 comes back as
李文远, 李闻渊, 里闻鸢. So names are written once, correctly, seeded into the
decoder prompt, and matched afterwards by sound: pinyin for CJK, a consonant
skeleton for Latin. Sound matching is the one feature here that can damage text
that was already right, so it stays inert until its dry run has been reviewed.

**Injection knows about XWayland.** `wtype` installs a keymap for its virtual
keyboard that X11 clients never receive, so they decode its keycodes against
the system layout and a sentence arrives as `1234567890-=`. Omavoi detects the
client and pastes instead.

**Every take is inspectable.** History keeps what the model actually said, what
each rule changed, per-segment confidences, input level and where the text
went. "It dropped a word again" becomes "segment 3 came back at avg_logprob
−1.4".

## Commands

```
omavoi daemon                 run it (normally systemd does)
omavoi setup                  what is missing, with the command for each
omavoi doctor                 check the whole install
omavoi status [--json]        state, for a bar module
omavoi record start|stop|toggle|cancel

omavoi history -n 10 -v       recent takes with diagnostics
omavoi last [--raw|--json]    everything about the last one
omavoi stats                  empty rate, RTF, input level

omavoi mode list|show|new|rm|set|match|unmatch|step
omavoi model list|pull|rm|use
omavoi dict add|rm|list       heard -> meant
omavoi names add|rm|dryrun|enable
omavoi config get|set|edit|show
omavoi transcribe FILE [--mode M]
```

## Engines

| | install size | notes |
|---|---|---|
| whisper.cpp on Vulkan | ~10 MB | default; NVIDIA, AMD, Intel |
| faster-whisper on CUDA | ~2.2 GB of wheels | NVIDIA only |
| any OpenAI-compatible API | — | audio leaves the machine |

On short push-to-talk takes the two local engines are close: measured on one
RTX 5070 Ti, Vulkan decoded a 3 s clip in 0.25 s against CUDA's 0.39 s, because
fixed overhead dominates at that length. Vulkan is the default for the install
size and the breadth of hardware, not because it is slower.

An LLM step is separate and optional, configured per mode: a local llama.cpp
server, the Claude API, or any OpenAI-compatible endpoint.

## Interface language

The console is in English by default and also speaks German, Spanish, French,
Vietnamese, Chinese, Japanese and Thai. Pick one from the dropdown in the top
nav, or set it from a terminal:

```bash
omavoi config set ui.language ja
```

An empty value follows the environment locale. This is the interface language
only — what you dictate in, and what an LLM step translates to, are per-mode
settings on the Modes tab.

## Status

Working: the daemon, all five console tabs, the HUD, the bar module, modes and
models editable from the UI, the dictionary and names.

Not yet: the dictionary's history-mined suggestions and its try-it box, sliders
in settings rather than read-only values, and a real byte-level progress bar
for model downloads.

MIT.
