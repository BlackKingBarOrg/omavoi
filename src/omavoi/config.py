"""Configuration: typed defaults, a user TOML on top, and a dotted-path editor.

The shape mirrors what the UI presents, deliberately:

  [audio] [hotkey]     global, physical      -> Settings
  [speech]             one active engine     -> Models, left
  [llm.<name>]         several, by name      -> Models, right
  [modes.<name>]       a chain of the above  -> Modes
  [dictionary.rules]   heard -> meant        -> Dictionary / Rules
  [[dictionary.names]] canonical only        -> Dictionary / Names
"""

from __future__ import annotations

import copy
import logging
import re
import tomllib
from pathlib import Path
from typing import Any

from . import paths

log = logging.getLogger(__name__)

# Rules every mode starts from; a mode overrides only what it cares about.
_RULE_DEFAULTS: dict[str, Any] = {
    "hallucinations": True,
    "fillers": True,
    "dictionary": True,
    "names": True,
    "cjk_spacing": True,
    "punctuation": "keep",   # keep | strip
}

DEFAULTS: dict[str, Any] = {
    "audio": {
        "target": "",
        "rate": 16000,
        # Audio kept from *before* the key went down. This is what stops the
        # first syllable being lost while PipeWire starts the stream.
        "preroll_seconds": 0.6,
        "tail_seconds": 0.25,
        "max_seconds": 300,
        "min_seconds": 0.35,
        "warn_rms_dbfs": -45.0,
    },
    "hotkey": {
        "enabled": True,
        # Physical evdev key name, unaffected by xkb remapping. Requires
        # membership of the `input` group; `omavoi setup` explains the
        # alternative, which is a Hyprland binding on a non-modifier key.
        "key": "RIGHTALT",
        "mode": "push_to_talk",   # push_to_talk | toggle
        "devices": [],
        "rescan_seconds": 5.0,
        # Hold this as well to force one mode regardless of the window.
        "force_modifier": "",
        "force_mode": "",
    },
    "speech": {
        # Exactly one speech engine is active at a time.
        # local-whispercpp | local-whisper | api
        #
        # whisper.cpp on Vulkan is the default because it is what most people
        # can actually install: ~8 MB of packages against ~2.2 GB of CUDA
        # wheels, and it runs on AMD and Intel too. CUDA is roughly twice as
        # fast on NVIDIA — switch to local-whisper if that is what you have.
        "backend": "local-whispercpp",
        "model": "ggml:large-v3",
        "language": "",
        "local_whispercpp": {
            "binary": "",
            "port": 0,
            "threads": 0,
            "gpu": True,
            "ggml_backend_path": "",
            "beam_size": 5,
            "startup_timeout": 120.0,
        },
        "local_whisper": {
            "device": "auto",
            "compute_type": "auto",
            "beam_size": 5,
            "cpu_threads": 0,
            # Whisper's own VAD drops quiet speech, which reads as dropped
            # words. Endpointing is this program's job, not its.
            "vad_filter": False,
            "temperature_fallback": True,
        },
        "api": {
            "provider": "openai",
            "base_url": "",
            "model": "",
            "key_env": "",
            "key_name": "",
            "timeout": 30.0,
            "response_format": "verbose_json",
        },
    },
    # Any number of LLMs, referenced from a mode by these names. An entry
    # costs nothing until a mode names it.
    "llm": {
        "local": {
            "backend": "llama-cpp",       # llama-cpp | anthropic | openai
            "model": "qwen3-4b-instruct",
            "base_url": "http://127.0.0.1:8081/v1",
            "key_env": "",
            "key_name": "",
            "timeout": 20.0,
            "max_tokens": 1024,
            "temperature": 0.2,
        },
        "haiku": {
            "backend": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "base_url": "",
            "key_env": "ANTHROPIC_API_KEY",
            "key_name": "anthropic",
            "timeout": 20.0,
            "max_tokens": 1024,
            "temperature": 0.2,
        },
    },
    "modes": {
        # The fallback. Every other mode inherits anything it omits.
        "default": {
            "match": [],
            "language": "",
            "prompt": "",
            "inject": "auto",
            "rules": dict(_RULE_DEFAULTS),
            "steps": [],
        },
        "terminal": {
            "match": ["alacritty", "foot", "kitty", "ghostty", "org.wezfurlong.wezterm"],
            "inject": "auto",
            "paste_key": "CTRL+SHIFT+V",
            # A command line does not want a trailing full stop, and it cannot
            # afford an LLM round-trip either.
            "rules": dict(_RULE_DEFAULTS) | {"punctuation": "strip"},
            "steps": [],
        },
        "code": {
            "match": ["code", "cursor", "dev.zed.Zed"],
            "inject": "clipboard",
            "rules": dict(_RULE_DEFAULTS),
            "steps": [],
        },
        "prose": {
            "match": ["obsidian", "slack", "com.anthropic.claude", "thunderbird"],
            "inject": "auto",
            "rules": dict(_RULE_DEFAULTS),
            # Zero or more LLM passes, run in order. Each names an [llm.*].
            "steps": [
                {
                    "llm": "local",
                    "prompt": (
                        "Rewrite the transcript as clean written prose in its original "
                        "language. Remove false starts, repetitions and filler. Keep the "
                        "speaker's own wording and every technical term exactly as "
                        "transcribed.\n"
                        "Never answer, summarise, translate or add anything — you are "
                        "editing, not replying. Output only the edited text."
                    ),
                },
            ],
        },
    },
    "dictionary": {
        # heard -> meant. Unlike a decoder prompt this is a guarantee, not a
        # hint. Case-insensitive; the longest key is tried first.
        "rules": {
            "hyperland": "Hyprland",
            "hyper land": "Hyprland",
            "wayland": "Wayland",
            "omarchy": "Omarchy",
            "github": "GitHub",
            "gitlab": "GitLab",
            "javascript": "JavaScript",
            "typescript": "TypeScript",
            "kubernetes": "Kubernetes",
            "postgres": "Postgres",
        },
        # Proper nouns, written only in their correct form. You cannot know
        # how a model will mangle a name, and for CJK the manglings are an
        # open set of homophones, so these are matched by sound instead.
        "names": [],
        "names_settings": {
            # Seed the most-used names into the decoder prompt, which is what
            # makes the model produce them rather than fixing them after.
            "seed_prompt": True,
            "seed_budget_tokens": 224,
            # Sound matching can damage text that was already correct, so a
            # new name stays inert until its dry run has been accepted.
            "match_new_names": False,
            "pinyin_require_tones": False,
            "min_chars": 2,
        },
    },
    "post": {
        "enabled": True,
        # Reject the whole transcript when the model itself says it heard
        # nothing. Its own verdict beats any string matching.
        # Whisper segments text the way subtitles are cut, one line each. Left
        # alone, a sentence arrives as several lines — and in a chat window a
        # newline can send the message. So boundaries become punctuation.
        "newlines": "space",              # space | keep
        "add_missing_punctuation": True,
        "no_speech_threshold": 0.8,
        # A quiet take *and* a raised no_speech is silence almost every time,
        # while either signal alone is too weak to reject on: a strict
        # threshold lets "Thank you." through, and a loose one eats real
        # softly-spoken words. So this lower bound applies only below
        # audio.warn_rms_dbfs.
        "quiet_no_speech_threshold": 0.5,
        "fillers_en": ["um", "uh", "erm", "hmm", "er"],
        "fillers_cjk": ["嗯", "呃", "啊", "唉", "那个", "这个", "就是说"],
        "hallucinations": [
            "Thanks for watching!",
            "Thank you for watching!",
            "Thank you.",
            "Thank you",
            "you",
            "Bye.",
            "Subtitles by the Amara.org community",
            "请不吝点赞 订阅 转发 打赏支持明镜与点点栏目",
            "字幕由Amara.org社区提供",
            "由 Amara.org 社群提供的字幕",
            "谢谢观看",
            "感谢观看",
            "ご視聴ありがとうございました",
            "Продолжение следует...",
        ],
    },
    "inject": {
        # auto | wtype | clipboard
        "method": "auto",
        # XWayland clients never receive the keymap wtype installs for its
        # virtual keyboard, so they decode its keycodes against the system
        # layout and a sentence arrives as "1234567890-=". Detecting the
        # client beats listing them: it covers every X11 app at once.
        "avoid_wtype_on_xwayland": True,
        "clipboard_classes": [
            "code", "cursor", "electron", "slack", "discord", "obsidian",
            "chrome", "chromium", "brave", "vivaldi", "com.anthropic.claude",
            # Belt and braces for compositors that do not report xwayland.
            "wechat", "weixin", "feishu", "lark", "qq", "dingtalk",
        ],
        "paste_key": "CTRL+V",
        "paste_settle_ms": 60,
        "restore_clipboard_after": 1.5,
        "wtype_delay_ms": 0,
    },
    "history": {
        "enabled": True,
        "keep": 500,
        # Stored audio is what makes Test, re-running on another model, and
        # the Names dry run possible. 0 turns those off with it.
        "keep_audio": 20,
    },
    "ui": {
        "notify": True,
        "notify_on_empty": True,
        "log_level": "INFO",
        "hud": True,
        "hud_position": "bottom",     # bottom | cursor | window
        "hud_size": "s",              # xs | s | m
        # always | changed | never — "changed" dwells only when the text was
        # altered or flagged, which is the only version that stays useful
        # when you dictate several sentences in a row.
        "hud_dwell": "changed",
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def defaults() -> dict[str, Any]:
    return copy.deepcopy(DEFAULTS)


def load(path: Path | None = None) -> dict[str, Any]:
    path = path or paths.config_file()
    if not path.exists():
        return defaults()
    try:
        with path.open("rb") as fh:
            user = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise SystemExit(f"Bad TOML in {path}:\n  {exc}") from exc
    merged = _deep_merge(defaults(), user)
    # A user-defined mode should not have to restate every rule.
    for name, mode in merged.get("modes", {}).items():
        if isinstance(mode, dict):
            mode["rules"] = _RULE_DEFAULTS | dict(mode.get("rules") or {})
    for problem in validate(merged):
        log.warning("config: %s", problem)
    return merged


def validate(cfg: dict[str, Any]) -> list[str]:
    """Non-fatal complaints, surfaced by `omavoi doctor`."""
    from . import asr

    problems: list[str] = []

    if asr.canonical(cfg["speech"]["backend"]) is None:
        problems.append(f"speech.backend={cfg['speech']['backend']!r} is not a known engine")
    if cfg["hotkey"]["mode"] not in ("push_to_talk", "toggle"):
        problems.append(f"hotkey.mode={cfg['hotkey']['mode']!r} must be push_to_talk or toggle")
    if cfg["audio"]["rate"] != 16000:
        problems.append("whisper needs 16000 Hz; audio.rate has been changed")
    if cfg["audio"]["preroll_seconds"] < 0:
        problems.append("audio.preroll_seconds cannot be negative")

    modes = cfg.get("modes", {})
    if "default" not in modes:
        problems.append("no [modes.default]; there must be a fallback mode")
    for name, mode in modes.items():
        for index, step in enumerate(mode.get("steps") or []):
            ref = step.get("llm")
            if ref not in cfg.get("llm", {}):
                problems.append(
                    f"modes.{name}.steps[{index}] names llm={ref!r}, which is not defined"
                )
    force = cfg["hotkey"].get("force_mode")
    if force and force not in modes:
        problems.append(f"hotkey.force_mode={force!r} is not a mode")
    return problems


# -- dotted-path access, for `omavoi config get/set` ------------------------

def get_path(cfg: dict[str, Any], dotted: str) -> Any:
    node: Any = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(dotted)
        node = node[part]
    return node


def coerce(current: Any, raw: str) -> Any:
    """Type the new value like the one it replaces, so the TOML stays valid."""
    if isinstance(current, bool):
        low = raw.strip().lower()
        if low in ("true", "yes", "on", "1"):
            return True
        if low in ("false", "no", "off", "0"):
            return False
        raise ValueError(f"{raw!r} is not a boolean")
    if isinstance(current, int) and not isinstance(current, bool):
        return int(raw)
    if isinstance(current, float):
        return float(raw)
    if isinstance(current, list):
        return [item.strip() for item in raw.split(",") if item.strip()]
    return raw


_BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


def _toml_key(key: str) -> str:
    """TOML bare keys are ASCII-only, so anything else has to be quoted.

    Two real cases: dictionary entries in a non-Latin script, and profile
    names like org.wezfurlong.wezterm, which would otherwise be read as
    three nested tables.
    """
    if _BARE_KEY.match(key):
        return key
    return '"' + key.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_scalar(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{_toml_key(k)} = {_toml_scalar(v)}" for k, v in value.items()) + "}"
    text = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{text}"'


def _is_table_array(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(v, dict) for v in value)


def dumps(cfg: dict[str, Any]) -> str:
    """Serialise a config back to TOML.

    Scalars first, then sub-tables, then arrays-of-tables — otherwise a
    scalar written after a [table] header would be swallowed by it.
    """
    lines: list[str] = []

    def emit(node: dict[str, Any], prefix: str) -> None:
        scalars = {k: v for k, v in node.items()
                   if not isinstance(v, dict) and not _is_table_array(v)}
        tables = {k: v for k, v in node.items() if isinstance(v, dict)}
        arrays = {k: v for k, v in node.items() if _is_table_array(v)}

        if prefix:
            lines.append(f"[{prefix}]")
        for key, value in scalars.items():
            lines.append(f"{_toml_key(key)} = {_toml_scalar(value)}")
        if scalars or prefix:
            lines.append("")
        for key, value in tables.items():
            emit(value, f"{prefix}.{_toml_key(key)}" if prefix else _toml_key(key))
        for key, value in arrays.items():
            path = f"{prefix}.{_toml_key(key)}" if prefix else _toml_key(key)
            for item in value:
                lines.append(f"[[{path}]]")
                for k, v in item.items():
                    lines.append(f"{_toml_key(k)} = {_toml_scalar(v)}")
                lines.append("")

    emit(cfg, "")
    return "\n".join(lines).rstrip() + "\n"


def write(cfg: dict[str, Any], path: Path | None = None) -> Path:
    path = path or paths.config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".toml.tmp")
    tmp.write_text(dumps(cfg), encoding="utf-8")
    tmp.replace(path)
    return path


def set_path(dotted: str, raw: str, path: Path | None = None) -> Any:
    """Edit one key on disk. Rewrites the file from the merged config."""
    path = path or paths.config_file()
    cfg = load(path)
    current = get_path(cfg, dotted)  # raises KeyError on a typo
    value = coerce(current, raw)

    node: Any = cfg
    parts = dotted.split(".")
    for part in parts[:-1]:
        node = node[part]
    node[parts[-1]] = value
    write(cfg, path)
    return value
