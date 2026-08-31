"""Translations for text the daemon produces and the UI only displays.

The console has its own table for its own labels (plugin/Strings.qml). This one
covers the strings that come *from here* — model catalogue notes, mostly — so a
Chinese console does not show a Chinese page with English model descriptions.

Keyed by the English text rather than by an id, so adding a model needs no
second edit and an untranslated note falls through to English instead of to a
blank or a key. `lang` follows `ui.language`; "" means English.
"""

from __future__ import annotations

_ZH = "zh"
_TH = "th"

# en -> {lang: text}
_TABLE: dict[str, dict[str, str]] = {
    "Proves the pipeline runs. Not usable for real dictation.": {
        _ZH: "只用来验证流程能跑通，不能真的用来听写。",
        _TH: "ใช้พิสูจน์ว่าไปป์ไลน์ทำงาน ไม่เหมาะกับการพิมพ์ด้วยเสียงจริง",
    },
    "Better than tiny, still not worth using daily.": {
        _ZH: "比 tiny 好，但还不值得日常使用。",
        _TH: "ดีกว่า tiny แต่ยังไม่คุ้มที่จะใช้ทุกวัน",
    },
    "Passable in English, struggles elsewhere.": {
        _ZH: "英文勉强够用，其他语言就吃力了。",
        _TH: "พอใช้ได้กับภาษาอังกฤษ ภาษาอื่นยังยาก",
    },
    "The floor of usable. A fallback when VRAM is tight.": {
        _ZH: "可用的下限。显存紧张时的退路。",
        _TH: "ขั้นต่ำที่ใช้งานได้ เป็นตัวสำรองเมื่อ VRAM ไม่พอ",
    },
    "The previous large. Steadier on some accents.": {
        _ZH: "上一代 large。对某些口音更稳。",
        _TH: "large รุ่นก่อน นิ่งกว่ากับบางสำเนียง",
    },
    "Best all-round. no_speech_prob is trustworthy, so silence is caught.": {
        _ZH: "综合最好。no_speech_prob 可信，所以能识别出静音。",
        _TH: "ดีที่สุดโดยรวม no_speech_prob เชื่อถือได้ จึงจับความเงียบได้",
    },
    "2x faster, but no_speech_prob is always 0 — it cannot detect silence.": {
        _ZH: "快两倍，但 no_speech_prob 恒为 0 —— 它识别不出静音。",
        _TH: "เร็วขึ้น 2 เท่า แต่ no_speech_prob เป็น 0 เสมอ — ตรวจความเงียบไม่ได้",
    },
    "English-only distillation. Unusable for other languages.": {
        _ZH: "只蒸馏了英文。其他语言无法使用。",
        _TH: "กลั่นมาเฉพาะภาษาอังกฤษ ใช้กับภาษาอื่นไม่ได้",
    },
    "Proves the pipeline runs.": {
        _ZH: "只用来验证流程能跑通。",
        _TH: "ใช้พิสูจน์ว่าไปป์ไลน์ทำงาน",
    },
    "Passable in English.": {
        _ZH: "英文勉强够用。",
        _TH: "พอใช้ได้กับภาษาอังกฤษ",
    },
    "The floor of usable.": {
        _ZH: "可用的下限。",
        _TH: "ขั้นต่ำที่ใช้งานได้",
    },
    "The default. Runs on any GPU through Vulkan.": {
        _ZH: "默认选择。通过 Vulkan 可以跑在任何 GPU 上。",
        _TH: "ค่าเริ่มต้น ทำงานบน GPU ใดก็ได้ผ่าน Vulkan",
    },
    "Faster, but poor at telling silence apart.": {
        _ZH: "更快，但分辨静音的能力差。",
        _TH: "เร็วกว่า แต่แยกความเงียบได้แย่",
    },
    "Quantised large-v3: a third of the VRAM, slightly less accurate.": {
        _ZH: "量化版 large-v3：显存只要三分之一，准确率略降。",
        _TH: "large-v3 แบบควอนไทซ์: ใช้ VRAM หนึ่งในสาม แม่นยำลดลงเล็กน้อย",
    },
    "The lightest thing still worth using.": {
        _ZH: "还值得一用的最轻的一个。",
        _TH: "ตัวที่เบาที่สุดที่ยังคุ้มจะใช้",
    },
    "Fast, and the best Chinese at this size. Other languages are along for the ride.": {
        _ZH: "快，而且是这个体积里中文最好的。其他语言只是顺带支持。",
        _TH: "เร็ว และภาษาจีนดีที่สุดในขนาดนี้ ภาษาอื่นเป็นของแถม",
    },
    "The same strengths with more room. A good default when the source language "
    "is Chinese.": {
        _ZH: "同样的长处，但余量更大。源语言是中文时的好默认选择。",
        _TH: "จุดแข็งเดิมแต่มีที่เหลือมากกว่า เป็นค่าเริ่มต้นที่ดีเมื่อภาษาต้นทางเป็นจีน",
    },
    "Broader language coverage than Qwen at this size, which shows on translation "
    "into anything but English.": {
        _ZH: "在这个体积上语言覆盖比 Qwen 更广，翻译成英文以外的语言时差别明显。",
        _TH: "ครอบคลุมภาษากว้างกว่า Qwen ในขนาดนี้ เห็นผลชัดเมื่อแปลเป็นภาษาอื่นที่ไม่ใช่อังกฤษ",
    },
    "The best translation here, and the heaviest. Leaves little room beside a "
    "large speech model.": {
        _ZH: "这里翻译最好的，也是最重的。和一个 large 语音模型并存时余量很小。",
        _TH: "แปลได้ดีที่สุดในนี้ และหนักที่สุด เหลือที่ไม่มากเมื่ออยู่ข้างโมเดลเสียงขนาดใหญ่",
    },
}


def t(text: str, lang: str) -> str:
    """The translation of `text`, or `text` itself."""
    if not lang or lang.startswith("en"):
        return text
    entry = _TABLE.get(text)
    if not entry:
        return text
    return entry.get(lang[:2], text)


def ui_lang(cfg: dict) -> str:
    """The configured UI language; "" when it follows the environment."""
    return str((cfg.get("ui") or {}).get("language", "") or "")
