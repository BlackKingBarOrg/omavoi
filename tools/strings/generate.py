# -*- coding: utf-8 -*-
import io, os, re, sys, textwrap

HEADER = '''import QtQuick

// The UI's text, in one place.
//
// Not Qt's own translation machinery: that wants .ts files compiled to .qm at
// build time, and this plugin is loaded from a directory of QML with nothing
// to build it. A plain table is also inspectable — a missing key shows up as
// the key itself rather than as blank space.
//
// Instantiated per root component (console, HUD, bar module) and handed down
// to child views as a property, because a plugin folder has no import path of
// its own to hang a singleton on.
//
// Product nouns stay untranslated on purpose: wtype, XWayland, PipeWire, ggml,
// VRAM, evdev. Translating a thing you have to type into a terminal or search
// for makes it unfindable.
Item {
  id: root

  // "" follows the environment; anything else wins.
  property string lang: ""

  // English first because it is the default; the rest by their own names,
  // Latin-script ones alphabetically and then the others.
  readonly property var languages: [
    { code: "en", name: "English" },
    { code: "de", name: "Deutsch" },
    { code: "es", name: "Espa\u00f1ol" },
    { code: "fr", name: "Fran\u00e7ais" },
    { code: "vi", name: "Ti\u1ebfng Vi\u1ec7t" },
    { code: "zh", name: "\u7b80\u4f53\u4e2d\u6587" },
    { code: "ja", name: "\u65e5\u672c\u8a9e" },
    { code: "th", name: "\u0e44\u0e17\u0e22" }
  ]

  readonly property string active: {
    if (lang && _table[lang] !== undefined) return lang
    // Qt.locale().name is like "de_DE"; the two-letter prefix is enough, and
    // a locale with no pack falls through to English rather than to nothing.
    var env = (Qt.locale().name || "en").toLowerCase().substring(0, 2)
    return _table[env] !== undefined ? env : "en"
  }

  function t(key) {
    var pack = _table[root.active] || {}
    if (pack[key] !== undefined) return pack[key]
    var base = _table.en || {}
    // The key itself, so an untranslated string is visible rather than blank.
    return base[key] !== undefined ? base[key] : key
  }

  // Same, with one substitution. Kept separate so the common case stays a
  // plain lookup.
  function tf(key, a) {
    return String(t(key)).replace("%1", a === undefined ? "" : String(a))
  }

'''

# key: (en, zh, th)
T = {}
def g(comment, **_): pass

SECTIONS = []
def section(name, entries):
    SECTIONS.append((name, entries))

section("firstrun", {
 "first.title":     ("Set up Omavoi", "设置 Omavoi", "ตั้งค่า Omavoi"),
 "first.blurb":     ("Two questions, then one button. Nothing runs until you press it, and "
                     "every command is shown first.",
                     "两个问题,然后一个按钮。你按下之前什么都不会执行,而且每条命令都会先显示出来。",
                     "สองคำถาม แล้วปุ่มเดียว ไม่มีอะไรทำงานจนกว่าคุณจะกด และทุกคำสั่งจะแสดงให้ดูก่อน"),
 "first.pick.language": ("Interface language", "界面语言", "ภาษาของหน้าจอ"),
 "first.pick.model":    ("Speech model", "语音模型", "โมเดลเสียงพูด"),
 "first.reuse":     ("weights another tool already put on this machine — used where they "
                     "lie, nothing to download",
                     "这台机器上已有的权重(别的工具下载的)—— 就地使用,无需下载",
                     "น้ำหนักที่เครื่องนี้มีอยู่แล้วจากเครื่องมืออื่น — ใช้ตามที่อยู่เดิม ไม่ต้องดาวน์โหลด"),
 "first.reuse.label": ("use what is here", "用已有的", "ใช้ของที่มีอยู่"),
 # Not "the only one": there are non-turbo models this screen does not
 # offer, and a claim that is only true of the three listed here is the
 # kind that survives into somewhere it is false.
 "first.m.large":   ("the turbo models cannot tell silence from speech; this one can",
                     "turbo 系列分不清静音和说话，这一个可以",
                     "รุ่น turbo แยกความเงียบจากเสียงพูดไม่ได้ ตัวนี้ได้"),
 "first.m.light":   ("the lightest thing still worth using",
                     "还值得一用的最轻的一个",
                     "ตัวที่เบาที่สุดที่ยังคุ้มจะใช้"),
 "first.m.turbo":   ("the default; half the download, and faster",
                     "默认选择；下载量减半，速度也更快",
                     "ค่าเริ่มต้น ดาวน์โหลดครึ่งเดียวและเร็วกว่า"),
 "first.willrun":   ("WHAT WILL RUN", "将要执行的操作", "สิ่งที่จะทำงาน"),
 "first.needspassword": ("asks for your password", "会要求输入密码", "จะขอรหัสผ่านของคุณ"),
 "first.install":   ("Install", "开始安装", "ติดตั้ง"),
 "first.retry":     ("Try again", "重试", "ลองอีกครั้ง"),
 "first.working":   ("%1 …", "%1 …", "%1 …"),
 "first.failed":    ("%1 failed — see below", "%1 失败 —— 见下方说明",
                     "%1 ล้มเหลว — ดูด้านล่าง"),
 "first.cancelled": ("the password prompt was cancelled, so nothing was installed",
                     "密码框被取消了,所以什么都没有安装",
                     "กล่องรหัสผ่านถูกยกเลิก จึงไม่มีอะไรถูกติดตั้ง"),
 "first.done":      ("Ready — hold your key and talk", "完成 —— 按住热键说话",
                     "พร้อมแล้ว — กดปุ่มค้างไว้แล้วพูด"),
 "first.dbstale":   ("Your package database is %1 days old. Installing anything now fails "
                    "with 404: the versions it lists are no longer on the mirrors. Arch "
                    "needs a system update before new packages either way.",
                    "你的软件包数据库是 %1 天前的。现在装任何东西都会 404 失败 —— 它记录的版本"
                    "在镜像上已经不存在了。Arch 在装新包之前本来就需要先更新系统。",
                    "ฐานข้อมูลแพ็กเกจของคุณเก่า %1 วัน การติดตั้งตอนนี้จะล้มเหลวด้วย 404 "
                    "เพราะเวอร์ชันที่ระบุไว้ไม่มีบนมิเรอร์แล้ว Arch ต้องอัปเดตระบบก่อนติดตั้งแพ็กเกจใหม่อยู่ดี"),
 "first.updatebtn": ("Update system packages", "更新系统软件包", "อัปเดตแพ็กเกจของระบบ"),
 "first.pacman404": ("The package database is out of date, so the mirrors no longer have the "
                     "versions it lists. Update the system above, then try again.",
                     "软件包数据库过期了,镜像上已经没有它记录的那些版本。先用上面那个按钮更新系统,"
                     "再重试。",
                     "ฐานข้อมูลแพ็กเกจล้าสมัย มิเรอร์จึงไม่มีเวอร์ชันที่ระบุไว้อีกแล้ว "
                     "อัปเดตระบบด้านบนแล้วลองอีกครั้ง"),
 "first.pick.hotkey": ("Push-to-talk key", "按住说话的键", "ปุ่มกดค้างเพื่อพูด"),
 "first.hotkey.other": ("another key, e.g. F9", "其他键,例如 F9", "ปุ่มอื่น เช่น F9"),
 # "these four normally do nothing on their own" was written on a US
 # layout, where Right Alt is exactly that. On German, French, Spanish,
 # Polish, Nordic and many other layouts it is AltGr and types characters
 # — @ is AltGr+Q on a German keyboard — so holding it to dictate means
 # you cannot type those characters without starting a take. The key is
 # read below the layout and never grabbed, which is what makes that true
 # rather than a conflict the program could resolve.
 "first.hotkey.note": ("Read below your keyboard layout and never taken over, so the key "
                       "keeps doing whatever it normally does. Right Alt is AltGr on many "
                       "non-US layouts and types characters there — pick Right Ctrl or "
                       "Scroll Lock if yours is one of those.",
                       "在键盘布局之下读取，而且从不接管，所以这个键仍然保留它原本的功能。"
                       "在很多非美式布局上右 Alt 就是 AltGr，按住它能打出字符 —— "
                       "如果你用的是那种布局，请选右 Ctrl 或 Scroll Lock。",
                       "อ่านต่ำกว่าเลย์เอาต์คีย์บอร์ดและไม่ยึดปุ่มไป ปุ่มจึงยังทำงานเดิมของมันต่อไป "
                       "บนเลย์เอาต์ที่ไม่ใช่ของสหรัฐหลายแบบ Alt ขวาคือ AltGr และใช้พิมพ์อักขระได้ — "
                       "ถ้าของคุณเป็นแบบนั้น ให้เลือก Ctrl ขวา หรือ Scroll Lock"),
 # No longer "takes effect at your next login": install.sh starts the daemon
 # through newgrp when the login predates the group, so the key works the
 # moment setup finishes. That sentence used to be the first thing a new
 # user read after being told setup was complete.
 "first.group.needed": ("You are not in the input group yet, so no key can be read. Adding "
                        "you is part of the step below, and the daemon is started in a way "
                        "that picks the group up at once — there is nothing to log out of.",
                        "你还不在 input 组里,所以任何键都读不到。下面那一步会把你加进去,"
                        "而且 daemon 会以当场就能拿到组权限的方式启动 —— 不需要重新登录。",
                        "คุณยังไม่อยู่ในกลุ่ม input จึงอ่านปุ่มใดไม่ได้ ขั้นด้านล่างจะเพิ่มคุณเข้าไป "
                        "และเดมอนจะเริ่มในแบบที่รับสิทธิ์กลุ่มได้ทันที — ไม่ต้องออกจากระบบ"),
 "first.step.hotkey": ("hotkey", "快捷键", "ปุ่มลัด"),
 "first.step.packages": ("system packages", "系统软件包", "แพ็กเกจของระบบ"),
 "first.step.daemon":   ("the daemon", "守护进程", "เดมอน"),
 "first.step.language": ("language", "语言", "ภาษา"),
 "first.step.weights":  ("model weights", "模型权重", "น้ำหนักโมเดล"),
 "first.step.use":      ("select the model", "选用模型", "เลือกโมเดล"),
 "first.step.mode":     ("default mode", "默认模式", "โหมดเริ่มต้น"),
 "first.step.service":  ("unit, keybinding and menu entry", "服务、快捷键与菜单项",
                        "ยูนิต ปุ่มลัด และรายการในเมนู"),
})

section("update", {
 "up.title":     ("UPDATE", "更新", "อัปเดต"),
 "up.behind":    ("%1 new commits on the plugin's branch",
                  "插件所在分支上有 %1 个新提交",
                  "มี %1 คอมมิตใหม่บนสาขาของปลั๊กอิน"),
 "up.current":   ("Up to date", "已是最新", "เป็นรุ่นล่าสุดแล้ว"),
 "up.daemon.blind": ("The daemon is installed separately and does not record which "
                     "commit it came from, so this screen cannot tell you whether it "
                     "is current. Running the update reinstalls it either way.",
                     "守护进程是单独安装的，而且不记录自己来自哪个提交，"
                     "所以这个页面无法告诉你它是不是最新的。无论如何，执行更新都会重装它。",
                     "เดมอนถูกติดตั้งแยกและไม่บันทึกว่ามาจากคอมมิตใด "
                     "หน้านี้จึงบอกไม่ได้ว่าเป็นเวอร์ชันล่าสุดหรือไม่ การอัปเดตจะติดตั้งใหม่อยู่ดี"),
 "up.unknown":   ("Cannot tell — the plugin was not installed from git",
                  "无法判断 —— 这个插件不是从 git 安装的",
                  "บอกไม่ได้ — ปลั๊กอินนี้ไม่ได้ติดตั้งจาก git"),
 # Said "not installed from git" for a failed fetch, which is the same
 # message for an offline laptop as for a hand-copied directory — and it
 # sends the first one to reinstall something that is perfectly fine.
 "up.nofetch":   ("Could not reach the remote, so this may not be the latest: %1",
                  "无法连接远端，所以这可能不是最新版本：%1",
                  "ติดต่อรีโมตไม่ได้ จึงอาจไม่ใช่รุ่นล่าสุด: %1"),
 "up.noupstream":("The plugin's branch has no upstream, so there is nothing to compare against",
                  "插件所在分支没有设置 upstream，没有可比较的对象",
                  "เบรนช์ของปลั๊กอินไม่มี upstream จึงไม่มีอะไรให้เทียบ"),
 "up.dirty":     ("The installed plugin has local changes, so it cannot fast-forward. "
                  "Reinstall it: omarchy plugin remove ai.bkblab.omavoi --yes && "
                  "omarchy plugin add %1 --enable --yes",
                  "已安装的插件里有本地改动,所以无法 fast-forward。重新安装它:"
                  "omarchy plugin remove ai.bkblab.omavoi --yes && "
                  "omarchy plugin add %1 --enable --yes",
                  "ปลั๊กอินที่ติดตั้งมีการเปลี่ยนแปลงในเครื่อง จึง fast-forward ไม่ได้ ติดตั้งใหม่: "
                  "omarchy plugin remove ai.bkblab.omavoi --yes && "
                  "omarchy plugin add %1 --enable --yes"),
 "up.run":       ("Update", "开始更新", "อัปเดต"),
 "up.again":     ("Check again", "再检查一次", "ตรวจอีกครั้ง"),
 "up.done":      ("Updated", "已更新", "อัปเดตแล้ว"),
 "up.step.plugin":  ("the plugin", "插件", "ปลั๊กอิน"),
 "up.step.daemon":  ("the daemon", "守护进程", "เดมอน"),
 "up.step.shortcuts": ("unit, keybinding and menu entry", "服务、快捷键与菜单项",
                       "ยูนิต ปุ่มลัด และรายการในเมนู"),
 "up.step.restart": ("restart", "重启服务", "รีสตาร์ต"),
})

section("shared-and-setup", {
 "nav.setup": ("Setup", "安装", "ตั้งค่า"),
 "setup.rootblurb": ("The steps above that need root can be done here, in one password prompt — polkit treats pacman as auth_admin, so asking in two calls means being asked twice. The daemon is restarted afterwards: it remembers a missing engine for the life of the process, so installing the binary alone would leave it still saying the engine is not there.", "上面需要 root 的步骤可以在这里一次做完，只弹一次密码框 —— polkit 把 pacman 当作 auth_admin，分两次调用就会问两次密码。装完会重启守护进程：它对「引擎未安装」的判断在进程存活期间是缓存的，只装二进制的话它仍会说引擎不在。", "ขั้นตอนด้านบนที่ต้องใช้ root ทำได้จากที่นี่ในการถามรหัสผ่านครั้งเดียว — polkit ถือว่า pacman เป็น auth_admin ถ้าเรียกสองครั้งก็จะถูกถามสองครั้ง หลังจากนั้นจะรีสตาร์ตเดมอน เพราะมันจำว่าเอนจินไม่มีอยู่ไปตลอดอายุโปรเซส การติดตั้งไบนารีอย่างเดียวจึงยังทำให้มันบอกว่าไม่มีเอนจิน"),
 "setup.rootrun": ("Install these", "一次装好", "ติดตั้งทั้งหมดนี้"),
})

section("nav", {
 "nav.history":     ("History", "历史", "ประวัติ"),
 "nav.modes":       ("Modes", "模式", "โหมด"),
 "nav.models":      ("Models", "模型", "โมเดล"),
 "nav.dictionary":  ("Dictionary", "词典", "พจนานุกรม"),
 "nav.settings":    ("Settings", "设置", "ตั้งค่า"),
})

section("state", {
 "state.idle":         ("idle", "空闲", "ว่าง"),
 "state.recording":    ("recording", "录音中", "กำลังอัดเสียง"),
 "state.transcribing": ("transcribing", "转写中", "กำลังถอดเสียง"),
 "state.stopped":      ("daemon stopped", "守护进程已停止", "เดมอนหยุดทำงาน"),
})

# The overlay's own four words. It had none: the only text it ever showed
# besides your own sentence was "no speech", in English, on every language.
section("hud", {
 # Which part of a take is running. The daemon holds one `transcribing` state
 # from the speech pass through to the injection — deliberately, three states
 # are what the bar module and the state file switch on — so these name the
 # phase inside it. Short: the strip grows to fit them and sits over whatever
 # you are typing into.
 "hud.stage.decoding":  ("transcribing", "转写中", "กำลังถอดเสียง"),
 "hud.stage.llm":       ("rewriting", "改写中", "กำลังเรียบเรียง"),
 "hud.stage.injecting": ("typing", "输入中", "กำลังพิมพ์"),
 "hud.nospeech":        ("no speech", "没有语音", "ไม่มีเสียงพูด"),
})

section("setup", {
 "setup.prefix":   ("setup ", "安装 ", "ติดตั้ง "),
 "setup.title":  ("Still to install: %1", "还有 %1 个组件要装",
                  "ยังต้องติดตั้ง: %1"),
 "setup.titledone": ("Everything is in place", "全部都装好了",
                     "ติดตั้งครบแล้ว"),
 "setup.blurb":    ("Nothing here runs until you press it, and every step shows the exact "
                    "command first. Omarchy deliberately runs nothing from inside a plugin "
                    "folder, so this screen asks instead.",
                    "这里的每一步都要你按下才会执行，并且会先把完整命令显示出来。Omarchy 有意不执行插件目录里的任何东西，"
                    "所以这个页面只能来问你。",
                    "ไม่มีอะไรทำงานจนกว่าคุณจะกด และทุกขั้นจะแสดงคำสั่งจริงให้ดูก่อน Omarchy ตั้งใจไม่รันสิ่งใด "
                    "จากในโฟลเดอร์ปลั๊กอิน หน้านี้จึงต้องถามคุณแทน"),
 "setup.copy":     ("Copy", "复制", "คัดลอก"),
 "setup.run":      ("Run", "运行", "รัน"),
 "setup.recheck":  ("Re-check", "重新检查", "ตรวจอีกครั้ง"),
 "setup.hint":     ("or run  omavoi setup  in a terminal — same steps, same order",
                    "或者在终端里运行  omavoi setup  —— 步骤和顺序完全一样",
                    "หรือรัน  omavoi setup  ในเทอร์มินัล — ขั้นตอนและลำดับเดียวกัน"),
})

section("history", {
 "hist.problems":   ("WHAT WENT WRONG", "出了什么问题", "เกิดอะไรผิดพลาด"),
 "hist.steps":      ("LLM STEPS", "LLM 步骤", "ขั้น LLM"),
 "hist.fellthrough": ("fell through, kept the previous text", "已回落,保留了上一步的文本",
                      "ล้มเหลว จึงคงข้อความก่อนหน้าไว้"),
 "hist.none":      ("no takes yet — hold %1 and talk", "还没有记录 —— 按住 %1 说话",
                    "ยังไม่มีรายการ — กด %1 ค้างไว้แล้วพูด"),
 "hist.yourkey":   ("your key", "你的按键", "ปุ่มของคุณ"),
 "hist.dropped":   ("dropped — ", "已丢弃 —— ", "ถูกทิ้ง — "),
 "hist.audio":     ("audio", "音频", "เสียง"),
 "hist.level":     ("level", "电平", "ระดับ"),
 "hist.decode":    ("decode", "解码", "ถอดรหัส"),
 "hist.model":     ("model", "模型", "โมเดล"),
 "hist.language":  ("language", "语言", "ภาษา"),
 "hist.mode":      ("mode", "模式", "โหมด"),
 "hist.injected":  ("injected", "注入方式", "วิธีป้อน"),
 "hist.said":      ("model said:  ", "模型原文：  ", "โมเดลได้ยินว่า:  "),
 "hist.post":      ("POST-PROCESSING", "后处理", "การประมวลผลภายหลัง"),
 "hist.segments":  ("SEGMENT CONFIDENCE", "分段置信度", "ความมั่นใจต่อช่วง"),
 "hist.copy":      ("Copy", "复制", "คัดลอก"),
 "hist.play":      ("Play", "播放", "เล่น"),
})

section("modes", {
 "modes.wontfit":    ("needs %1 free", "需要 %1 空闲显存", "ต้องมี %1 ว่าง"),
 "modes.blocked":    ("not switched — this mode's model will not fit in VRAM right now",
                      "未切换 —— 这个模式的模型现在装不进显存",
                      "ไม่ได้สลับ — โมเดลของโหมดนี้ใส่ใน VRAM ตอนนี้ไม่พอ"),
 "modes.speechmodel": ("weights", "权重", "น้ำหนัก"),
 "modes.speechglobal": ("whatever is loaded", "沿用已加载的", "ใช้ตัวที่โหลดอยู่"),
 "modes.speechonly1": ("Only one set of weights is downloaded for this engine. The Models "
                       "tab has the rest — a smaller one is worth having for modes where "
                       "speed matters more than accuracy.",
                       "这个引擎目前只下载了一套权重。其余的在「模型」页 —— "
                       "对速度比准确率更重要的模式,值得备一个小的。",
                       "เอนจินนี้ดาวน์โหลดน้ำหนักไว้ชุดเดียว ที่เหลืออยู่ในแท็บโมเดล — "
                       "ตัวเล็กกว่าคุ้มที่จะมีไว้สำหรับโหมดที่เน้นความเร็วมากกว่าความแม่น"),
 "modes.newname":    ("new mode name", "新模式名称", "ชื่อโหมดใหม่"),
 "modes.here":       ("here", "当前", "ที่นี่"),
 "modes.fallback":   ("fallback", "兜底", "สำรอง"),
 "modes.followwin":  ("The mode follows the focused window", "模式跟随当前焦点窗口",
                      "โหมดจะตามหน้าต่างที่โฟกัส"),
 "modes.everytake":  ("Every take uses ", "每次录音都使用 ", "ทุกครั้งจะใช้ "),
 "modes.longestwins":("The longest match below wins; nothing matching falls back to default.",
                      "下面匹配最长的规则胜出；都不匹配时回落到 default。",
                      "กฎที่ตรงยาวที่สุดด้านล่างชนะ ถ้าไม่ตรงเลยจะกลับไปใช้ default"),
 "modes.matchoff":   ("Window matching is off, so the lists below are configured but inert. "
                      "It needs tuning per application before it earns its keep.",
                      "窗口匹配已关闭，下面的列表虽已配置但不会生效。它需要为每个应用逐个调过才值得开启。",
                      "การจับคู่หน้าต่างปิดอยู่ รายการด้านล่างจึงถูกตั้งไว้แต่ไม่ทำงาน "
                      "ต้องปรับทีละแอปก่อนจะคุ้มค่าที่จะเปิด"),
 "modes.hiddenauto": ("Window matching is switched on but its controls are hidden, so "
                     "clicking a mode below will not change which one a take uses. "
                     "Turn it off with `omavoi mode auto off`.",
                     "窗口匹配是开着的，但它的控件已被隐藏，所以点击下面的模式不会改变"
                     "录音实际使用的模式。用 `omavoi mode auto off` 关掉它。",
                     "การจับคู่หน้าต่างเปิดอยู่แต่ตัวควบคุมถูกซ่อน การคลิกโหมดด้านล่างจึงไม่เปลี่ยน"
                     "โหมดที่ใช้จริง ปิดด้วย `omavoi mode auto off`"),
 "modes.following":  ("following the window", "跟随窗口", "ตามหน้าต่าง"),
 "modes.fixed":      ("fixed", "固定", "คงที่"),
 "modes.activehere": ("active in this window", "在当前窗口生效", "ทำงานในหน้าต่างนี้"),
 "modes.delete":     ("Delete mode", "删除模式", "ลบโหมด"),
 "modes.opens":      ("OPENS ON", "触发窗口", "เปิดเมื่อ"),
 "modes.notinuse":   ("not in use while the mode is fixed", "模式固定时这里不生效",
                      "ไม่ถูกใช้ขณะโหมดถูกตั้งคงที่"),
 "modes.nothing":    ("nothing — this mode is only reached by name",
                      "无 —— 这个模式只能按名字调用",
                      "ไม่มี — โหมดนี้เรียกได้ด้วยชื่อเท่านั้น"),
 "modes.classph":    ("window class, e.g. thunderbird", "窗口 class，例如 thunderbird",
                      "คลาสหน้าต่าง เช่น thunderbird"),
 "modes.add":        ("Add", "添加", "เพิ่ม"),
 "modes.matchhint":  ("Matched against the Hyprland class and title. The longest match wins.",
                      "与 Hyprland 的 class 和 title 做匹配，最长的匹配胜出。",
                      "เทียบกับ class และ title ของ Hyprland กฎที่ตรงยาวที่สุดชนะ"),
 "modes.s1":         ("1  SPEECH", "1  语音", "1  เสียงพูด"),
 "modes.speechsub":  ("what the model is told before it decodes", "解码之前告诉模型的内容",
                      "สิ่งที่บอกโมเดลก่อนเริ่มถอดเสียง"),
 "modes.language":   ("language", "语言", "ภาษา"),
 "modes.langhint":   ("empty detects it per take; a code like en or zh is faster and steadier",
                      "留空则每次自动检测；填 en、zh 这样的代码更快也更稳",
                      "ปล่อยว่างจะตรวจทุกครั้ง ใส่รหัสอย่าง en หรือ zh จะเร็วและนิ่งกว่า"),
 "modes.decoderhint":("decoder hint", "解码提示词", "คำใบ้ให้ตัวถอดเสียง"),
 "modes.promptph":   ("Seeded into the model. Good for jargon it keeps mangling — a hint, "
                      "not a guarantee; the dictionary is the guarantee.",
                      "会喂给模型。适合它总认错的专有名词 —— 这只是提示，不是保证；保证靠词典。",
                      "ถูกป้อนเข้าโมเดล เหมาะกับศัพท์เฉพาะที่มันเพี้ยนบ่อย — เป็นคำใบ้ ไม่ใช่การรับประกัน "
                      "ตัวที่รับประกันคือพจนานุกรม"),
 "modes.s2":         ("2  RULES", "2  规则", "2  กฎ"),
 "modes.rulessub":   ("deterministic · no latency", "确定性 · 零延迟", "แน่นอน · ไม่มีดีเลย์"),
 "modes.r.hallucinations": ("hallucinations", "幻觉过滤", "การหลอน"),
 "modes.r.fillers":  ("fillers", "语气词", "คำเติม"),
 "modes.r.dictionary":("dictionary", "词典", "พจนานุกรม"),
 "modes.r.names":    ("names", "名称", "ชื่อเฉพาะ"),
 "modes.r.cjk":      ("CJK spacing", "中英间距", "ระยะห่าง CJK"),
 "modes.keeppunct":  ("keep end punctuation", "保留句末标点", "คงเครื่องหมายท้ายประโยค"),
 "modes.s3":         ("3  LLM", "3  LLM", "3  LLM"),
 "modes.llmsub":     ("optional · runs in order · a failure keeps the text it was given",
                      "可选 · 按顺序执行 · 某步失败则保留上一步的文本",
                      "ไม่บังคับ · ทำตามลำดับ · ถ้าล้มเหลวจะคงข้อความเดิมไว้"),
 "modes.step":       ("step ", "第 ", "ขั้น "),
 "modes.stepsuffix": ("", " 步", ""),
 "modes.remove":     ("Remove", "移除", "เอาออก"),
 "modes.stepph":     ("Tell it to edit, not to reply.", "让它改写，不要让它回答。",
                      "สั่งให้แก้ข้อความ ไม่ใช่ให้ตอบ"),
 "modes.nostep":     ("This mode has no LLM pass, so there is no prompt to write yet. Add one "
                      "below and its prompt appears here, editable, with a usable default "
                      "already in it.",
                      "这个模式没有 LLM 步骤，所以还没有提示词可写。在下面加一个，它的提示词就会出现在这里，可编辑，"
                      "并且已经带了一份能直接用的默认内容。",
                      "โหมดนี้ไม่มีขั้น LLM จึงยังไม่มีพรอมป์ตให้เขียน เพิ่มด้านล่างแล้วพรอมป์ตจะปรากฏที่นี่ "
                      "แก้ไขได้ และมีค่าเริ่มต้นที่ใช้งานได้อยู่แล้ว"),
 "modes.addstep":    ("+ add a step", "+ 添加一步", "+ เพิ่มขั้น"),
 "modes.weights":  ("weights", "权重", "น้ำหนักโมเดล"),
 "modes.inherit":  ("follow the configuration (%1)", "跟随配置（%1）",
                    "ตามการตั้งค่า (%1)"),
 "modes.nollm":      ("no LLM is configured — see the Models tab", "还没有配置 LLM —— 去「模型」页",
                      "ยังไม่ได้ตั้งค่า LLM — ดูที่แท็บโมเดล"),
 "modes.inject.auto":      ("auto", "自动", "อัตโนมัติ"),
 "modes.inject.clipboard": ("clipboard", "剪贴板", "คลิปบอร์ด"),
 "modes.inject.xdotool": ("xdotool", "xdotool", "xdotool"),
 "modes.langauto":         ("auto", "自动", "อัตโนมัติ"),
 "modes.s4":         ("4  INJECT", "4  注入", "4  การป้อนข้อความ"),
 "modes.injecthint": ("auto types with wtype, except in XWayland clients and known Electron "
                      "apps, where it pastes instead — wtype's synthetic keycodes reach those "
                      "as digits.",
                      "auto 默认用 wtype 逐字输入；遇到 XWayland 客户端和已知的 Electron 应用则改为粘贴 —— "
                      "wtype 合成的键码传到那些程序里会变成数字。",
                      "auto จะพิมพ์ด้วย wtype ยกเว้นไคลเอนต์ XWayland และแอป Electron ที่รู้จัก "
                      "ซึ่งจะใช้การวางแทน — คีย์โค้ดสังเคราะห์ของ wtype ไปถึงแอปพวกนั้นเป็นตัวเลข"),
})

section("models", {
 "models.speech":    ("SPEECH", "语音", "เสียงพูด"),
 "models.speechsub": ("audio → text · one runs", "音频 → 文本 · 只跑一个",
                      "เสียง → ข้อความ · ทำงานตัวเดียว"),
 "models.e.vulkan":     ("Local · Vulkan", "本地 · Vulkan", "ในเครื่อง · Vulkan"),
 "models.e.vulkan.sub": ("whisper.cpp · ggml weights · NVIDIA, AMD and Intel alike",
                         "whisper.cpp · ggml 权重 · NVIDIA、AMD、Intel 都能跑",
                         "whisper.cpp · น้ำหนัก ggml · ใช้ได้ทั้ง NVIDIA, AMD และ Intel"),
 "models.e.vulkan.note":("~10 MB of packages", "约 10 MB 的软件包", "แพ็กเกจราว 10 MB"),
 "models.e.api":        ("Remote API", "远程 API", "API ระยะไกล"),
 "models.e.api.sub":    ("OpenAI-compatible · OpenAI, Groq, SiliconFlow, a local server",
                         "兼容 OpenAI 协议 · OpenAI、Groq、SiliconFlow，或自建服务",
                         "รองรับรูปแบบ OpenAI · OpenAI, Groq, SiliconFlow หรือเซิร์ฟเวอร์ในเครื่อง"),
 "models.e.api.note":   ("audio leaves this machine", "音频会离开本机",
                         "เสียงจะออกจากเครื่องนี้"),
 "models.llmcathint": ("named by a mode's step, not switched globally",
                      "由模式的步骤按名字引用，不是全局切换",
                      "โหมดเรียกใช้ตามชื่อในขั้นของมัน ไม่ใช่การสลับทั้งระบบ"),
 "models.now":       ("RUNNING NOW", "正在运行", "ที่กำลังทำงาน"),
 "models.running":   ("running", "运行中", "กำลังทำงาน"),
 "models.notloaded": ("not loaded", "未加载", "ยังไม่ได้โหลด"),
 "models.llmnone": ("none loaded — each starts on its first use",
                    "都未加载 —— 各自在首次用到时启动",
                    "ยังไม่โหลด — แต่ละตัวเริ่มเมื่อถูกใช้ครั้งแรก"),
 "models.coldshort":  ("cold", "未启动", "ยังไม่เริ่ม"),
 "models.ready":     ("ready", "就绪", "พร้อม"),
 "models.nodaemon":  ("daemon not reachable — what is loaded is unknown",
                      "连不上守护进程 —— 无法得知加载了什么",
                      "ติดต่อเดมอนไม่ได้ — ไม่ทราบว่าโหลดอะไรไว้"),
 "models.f.edit":      ("Edit", "编辑", "แก้ไข"),
 "models.f.close":     ("Close", "收起", "ปิด"),
 "models.f.url":       ("URL", "URL", "URL"),
 "models.f.model":     ("Model", "模型", "โมเดล"),
 "models.f.key":       ("Key", "密钥", "คีย์"),
 "models.f.key.place": ("paste it here — it goes to secrets.toml, never to the config",
                        "粘贴在这里 —— 它会写进 secrets.toml,绝不进配置文件",
                        "วางที่นี่ — จะถูกเก็บใน secrets.toml ไม่เข้าไฟล์ตั้งค่า"),
 "models.f.key.save":  ("Save", "保存", "บันทึก"),
 "models.f.key.saved": ("saved to secrets.toml, 0600", "已存入 secrets.toml,权限 0600",
                        "บันทึกใน secrets.toml สิทธิ์ 0600"),
 "models.f.key.failed":("could not be saved", "保存失败", "บันทึกไม่สำเร็จ"),
 "models.f.test":      ("Test", "测试连接", "ทดสอบ"),
 "models.f.testing":   ("asking the endpoint for its models…", "正在向端点索取模型列表…",
                        "กำลังขอรายการโมเดลจากปลายทาง…"),
 "models.f.testok":    ("answered, %1 models — pick one below",
                        "有响应,%1 个模型 —— 在下面选一个",
                        "ตอบกลับแล้ว %1 โมเดล — เลือกด้านล่าง"),
 "models.f.key.have": ("a key is stored", "已存有密钥", "มีคีย์เก็บไว้แล้ว"),
 "models.f.key.fromenv": ("in use from %1 in the environment — it wins over "
                          "the file, so a stale one beats the key you just saved",
                          "正在使用环境变量 %1 —— 它会赢过文件，"
                          "所以一个过时的环境变量会压掉你刚保存的密钥",
                          "ใช้จาก %1 ในสภาพแวดล้อม — ชนะไฟล์ "
                          "คีย์เก่าจะทับคีย์ที่เพิ่งบันทึก"),
 "models.f.key.fromfile": ("stored in secrets.toml", "已存在 secrets.toml 里",
                           "เก็บไว้ใน secrets.toml"),
 "models.f.testfail": ("it did not answer", "它没有回应", "ไม่มีการตอบกลับ"),
 "models.speechapi": ("REMOTE SPEECH ENDPOINT", "远程语音接入点", "ปลายทางเสียงระยะไกล"),
 "models.speechapi.sub": ("Audio leaves this machine. Selected above under 远程 API.",
                          "音频会离开本机。在上面的「远程 API」里选中它才会生效。",
                          "เสียงจะออกจากเครื่องนี้ เลือก \"远程 API\" ด้านบนเพื่อใช้งาน"),
 "models.speechapi.cat": ("The list below is the local engine's weights and is "
                          "not used while the remote engine is selected.",
                          "下面的列表是本地引擎的权重，选中远程引擎时不会用到。",
                          "รายการด้านล่างคือน้ำหนักของเอนจินในเครื่อง และไม่ถูกใช้เมื่อเลือกเอนจินระยะไกล"),
 "models.k.agent":     ("System agent", "系统 agent", "เอเจนต์ของระบบ"),
 # "already logged in, no key" implied a cloud without saying the text
 # reaches it. The process is local; the inference is not, which is what
 # state() has always reported and this line did not.
 "models.k.agent.sub": ("whichever coding agent Omarchy is set to — already logged "
                        "in, no key, seconds of startup per take. Your words go "
                        "wherever that agent is signed in.",
                        "Omarchy 设定的那个 coding agent —— 已经登录过，不需要密钥，"
                        "每次录音要花几秒启动。你的话会发到那个 agent 登录的服务上。",
                        "เอเจนต์ที่ Omarchy ตั้งไว้ — ล็อกอินอยู่แล้ว ไม่ต้องมีคีย์ "
                        "แต่เสียเวลาเริ่มไม่กี่วินาทีต่อครั้ง "
                        "คำของคุณจะไปถึงบริการที่เอเจนต์นั้นล็อกอินอยู่"),
 # An agent whose non-interactive mode has nowhere but argv to take a
 # prompt gets the transcript on a command line. Said here because this
 # program reads API keys from stdin for exactly that reason.
 "models.k.agent.argv": ("· the transcript goes in this agent's command line, "
                         "which /proc shows to anything running as you",
                         "· 这个 agent 的调用会把转写文本放进命令行,"
                         "同一用户下的任何进程都能从 /proc 看到",
                         "· การเรียกเอเจนต์นี้จะใส่ข้อความถอดเสียงไว้ในบรรทัดคำสั่ง "
                         "ซึ่งโปรเซสใด ๆ ของผู้ใช้คนนี้อ่านได้จาก /proc"),
 "models.k.local":     ("Local model", "本地模型", "โมเดลในเครื่อง"),
 "models.k.local.sub": ("llama.cpp, started and owned here; a step can name its own "
                        "weights from the catalogue below",
                        "llama.cpp,由本程序启动和管理;步骤可以从下面的目录里指定自己的权重",
                        "llama.cpp ที่โปรแกรมนี้เริ่มและดูแลเอง; แต่ละขั้นเลือกน้ำหนักของตัวเอง "
                        "จากรายการด้านล่างได้"),
 "models.k.api":       ("Remote API", "远程 API", "API ระยะไกล"),
 # It was "the only one that sends your words off the machine", which the
 # agent route also does — it runs a CLI that is logged into someone's
 # cloud. Two of these three send the text out; one of them said so.
 "models.k.api.sub":   ("OpenAI-compatible — set base_url and a key. Your words go "
                        "to that endpoint.",
                        "兼容 OpenAI 协议 —— 需要设 base_url 和密钥。你的话会发到那个端点。",
                        "รองรับรูปแบบ OpenAI — ต้องตั้ง base_url และคีย์ "
                        "คำของคุณจะถูกส่งไปที่ปลายทางนั้น"),
 "models.k.unset":     ("not configured", "未配置", "ยังไม่ได้ตั้งค่า"),
 "models.stale":     ("The daemon is still running what it started with",
                      "守护进程仍在跑启动时加载的那一个",
                      "เดมอนยังรันตัวที่โหลดไว้ตอนเริ่มอยู่"),
 "models.loaded":    ("loaded ", "已加载 ", "โหลดแล้ว "),
 "models.configured":("configured ", "已配置 ", "ตั้งค่าไว้ "),
 "models.restart":   ("Restart daemon", "重启守护进程", "รีสตาร์ตเดมอน"),
 "models.list":      ("MODELS · ", "模型 · ", "โมเดล · "),
 "models.formathint":("the format this engine runs", "这个引擎使用的权重格式",
                      "รูปแบบน้ำหนักที่เอนจินนี้ใช้"),
 "models.ondisk":    ("already on disk", "已在磁盘上", "มีอยู่ในดิสก์แล้ว"),
 "models.downloading":("downloading…", "下载中…", "กำลังดาวน์โหลด…"),
 "models.download":  ("Download", "下载", "ดาวน์โหลด"),
 "models.use":       ("Use", "使用", "ใช้"),
 "models.remove":    ("Remove", "删除", "ลบ"),
 "models.ourstore":  ("our store", "我们的模型目录", "คลังของเรา"),
 "models.outside":   ("Weights found outside %1 are used where they lie and never deleted.",
                      "在 %1 之外找到的权重会就地使用，永不删除。",
                      "น้ำหนักที่พบนอก %1 จะถูกใช้ตามที่อยู่เดิมและไม่ถูกลบ"),
 "models.llm":       ("LLM", "LLM", "LLM"),
 "models.llmsub":    ("text → text · any number, named by modes",
                      "文本 → 文本 · 可配多个，由模式按名字引用",
                      "ข้อความ → ข้อความ · มีได้หลายตัว โหมดเรียกตามชื่อ"),
 "models.nokey":     ("no key", "缺密钥", "ไม่มีคีย์"),
 "models.endpointnote":("Endpoints live under [llm.<name>] — omavoi config edit. A key never "
                      "goes in the config: set its environment variable, or put it in "
                      "secrets.toml.",
                      "接入点写在 [llm.<name>] 下 —— omavoi config edit。密钥绝不写进配置文件："
                      "设成环境变量，或者放进 secrets.toml。",
                      "ปลายทางอยู่ใต้ [llm.<name>] — omavoi config edit คีย์ไม่เคยอยู่ในไฟล์ตั้งค่า: "
                      "ตั้งเป็นตัวแปรสภาพแวดล้อม หรือใส่ใน secrets.toml"),
 "models.seg.speech": ("speech model", "语音模型", "โมเดลเสียงพูด"),
 "models.seg.other":  ("other programs", "其他程序", "โปรแกรมอื่น"),
 "models.vramsub":   ("in use across the whole machine", "全机范围的占用",
                      "ที่ใช้อยู่ทั้งเครื่อง"),
 "models.vramnote":  ("Keeping both resident is the point: a chain that loads weights per take "
                      "costs seconds, not milliseconds. Overcommit and the speech model is what "
                      "gets evicted — dictation goes ten times slower with nothing to say why.",
                      "让两个模型都常驻是关键：每次录音都重新加载权重要花几秒，而不是几毫秒。一旦超配，"
                      "被换出去的就是语音模型 —— 听写会慢十倍，而且不会有任何提示告诉你为什么。",
                      "การให้ทั้งสองตัวค้างในหน่วยความจำคือหัวใจ: สายที่โหลดน้ำหนักใหม่ทุกครั้งเสียเวลาเป็นวินาที "
                      "ไม่ใช่มิลลิวินาที ถ้าจัดเกินโควตา ตัวที่ถูกไล่ออกคือโมเดลเสียงพูด — "
                      "การพิมพ์ด้วยเสียงจะช้าลงสิบเท่าโดยไม่มีอะไรบอกสาเหตุ"),
 "models.vram":      ("VRAM · ", "显存 · ", "VRAM · "),
 "models.sharednote": ("This GPU has no memory of its own — the weights are ordinary system pages, and the bar above is the whole machine. Keeping both resident is still the point, but overcommit here costs swap rather than an eviction: dictation stalls instead of merely slowing down, and everything else on the machine stalls with it.", "这块 GPU 没有独立显存 —— 权重就是普通的系统内存页，上面那条是全机内存。让两个模型都常驻依然是关键，但在这里超配的代价是 swap，不是被换出：听写会直接卡住，而不只是变慢，整台机器也会跟着卡。", "GPU ตัวนี้ไม่มีหน่วยความจำของตัวเอง — น้ำหนักอยู่ในหน่วยความจำระบบธรรมดา และแถบด้านบนคือทั้งเครื่อง การให้ทั้งสองตัวค้างไว้ยังคงเป็นหัวใจ แต่การจัดเกินโควตาที่นี่ต้องจ่ายด้วย swap ไม่ใช่การถูกไล่ออก: การพิมพ์ด้วยเสียงจะค้างไปเลย ไม่ใช่แค่ช้าลง และทั้งเครื่องจะค้างตามไปด้วย"),
 "models.shared": ("Shared memory · ", "共享内存 · ", "หน่วยความจำร่วม · "),
 "models.needs":     ("needs", "需要", "ต้องใช้"),
})

section("dictionary", {
 "dict.rules":     ("rules", "规则", "กฎ"),
 "dict.names":     ("names", "名称", "ชื่อเฉพาะ"),
 "dict.blurb":     ("heard → meant. A decoder prompt is a hint the model may ignore; this is "
                    "the guarantee. The longest key is tried first, so a shorter one it "
                    "contains can never fire.",
                    "听到的 → 想要的。解码提示词只是模型可以无视的建议，这里才是保证。匹配时先试最长的键，"
                    "所以被它包含的更短的键永远不会触发。",
                    "ที่ได้ยิน → ที่ต้องการ พรอมป์ตของตัวถอดเสียงเป็นเพียงคำใบ้ที่โมเดลอาจเมิน "
                    "ส่วนนี้คือตัวรับประกัน คีย์ที่ยาวที่สุดถูกลองก่อน คีย์สั้นที่อยู่ข้างในจึงไม่มีวันทำงาน"),
 "dict.shadowed":  ("never fires — shadowed by ", "永不触发 —— 被遮蔽于 ",
                    "ไม่เคยทำงาน — ถูกกลบโดย "),
 "dict.remove":    ("Remove", "移除", "เอาออก"),
 "dict.heard":   ("heard as", "听成了", "ได้ยินเป็น"),
 "dict.meant":   ("should be", "应该是", "ควรเป็น"),
 "dict.add":     ("Add", "添加", "เพิ่ม"),
 "dict.heardph": ("hyper land", "hyper land", "hyper land"),
 "dict.meantph": ("Hyprland", "Hyprland", "Hyprland"),
 "dict.nameph":  ("Hyprland  Postgres  Wayland — several at once is fine",
                  "Hyprland  Postgres  Wayland —— 可以一次加好几个",
                  "Hyprland  Postgres  Wayland — ใส่หลายคำพร้อมกันได้"),
 "dict.namesblurb":("Write only the correct form. Names are seeded into the decoder prompt so "
                    "the model produces them, and matched by sound afterwards so homophones "
                    "collapse back. Matching stays off until a dry run has been looked at — it "
                    "is the one thing here that can damage text that was already right.",
                    "只写正确的写法。名称会被喂进解码提示词，让模型倾向于产出它们，之后再按读音匹配，"
                    "把同音的写法收回来。匹配默认关闭，直到你看过一次试运行 —— "
                    "这是这里唯一可能把原本正确的文字改坏的功能。",
                    "เขียนเฉพาะรูปที่ถูกต้อง ชื่อจะถูกป้อนเข้าพรอมป์ตของตัวถอดเสียงเพื่อให้โมเดลสร้างมันออกมา "
                    "แล้วจับคู่ด้วยเสียงภายหลังเพื่อรวมคำพ้องเสียงกลับ การจับคู่จะปิดไว้จนคุณได้ดูผลทดลองก่อน — "
                    "นี่เป็นสิ่งเดียวในหน้านี้ที่ทำให้ข้อความที่ถูกอยู่แล้วเสียได้"),
 "dict.matching":  ("matching", "匹配中", "จับคู่อยู่"),
 "dict.seedonly":  ("seed only", "仅提示", "ป้อนพรอมป์ตเท่านั้น"),
 "dict.dryrun":    ("Dry run", "试运行", "ทดลองรัน"),
 "dict.enable":    ("Enable matching", "开启匹配", "เปิดการจับคู่"),
 "dict.prompt":    ("prompt: ", "提示词： ", "พรอมป์ต: "),
 "dict.none":      ("(none)", "（无）", "(ไม่มี)"),
 "dict.overbudget":("%1 more did not fit the prompt budget",
                    "另有 %1 个超出提示词预算，未被加入",
                    "อีก %1 รายการไม่พอโควตาพรอมป์ต"),
 "set.ptt":        ("push to talk", "按住说话", "กดค้างเพื่อพูด"),
 "set.toggle":     ("toggle", "按一下切换", "สลับเปิด/ปิด"),
 "set.dwell.always":  ("always", "总是", "เสมอ"),
 "set.dwell.changed": ("changed", "有改动时", "เมื่อมีการแก้"),
 "set.dwell.never":   ("never", "从不", "ไม่เลย"),
 "set.hotkey":     ("HOTKEY", "快捷键", "ปุ่มลัด"),
 "set.key.type":    ("or type it, e.g. CTRL+SLASH",
                     "或者直接输入，例如 CTRL+SLASH",
                     "หรือพิมพ์เอง เช่น CTRL+SLASH"),
 "set.key.rebind":  ("Press a key", "按一下新键", "กดปุ่มใหม่"),
 "set.key.press":   ("waiting — press it now, or hold a combination",
                     "等待中 —— 现在按下它，或按住一个组合键",
                     "กำลังรอ — กดเลย หรือกดค้างเป็นชุดปุ่มก็ได้"),
 "set.key":        ("key", "按键", "ปุ่ม"),
 "set.behaviour":  ("behaviour", "行为", "พฤติกรรม"),
 "set.key.check":   ("Check again", "重新检查", "ตรวจอีกครั้ง"),
 "set.key.ok":      ("listening on %1", "正在监听 %1", "กำลังฟังที่ %1"),
 "set.key.testing": ("checking…", "检查中……", "กำลังตรวจ…"),
 "set.key.badname": ("%1 is not a key this machine has — press a key instead",
                     "%1 不是这台机器上的按键 —— 直接按一下你想用的键",
                     "%1 ไม่ใช่ปุ่มที่เครื่องนี้มี — กดปุ่มที่ต้องการเลย"),
 "set.key.nogroup": ("you are not in the `input` group, so not one keyboard can be opened — "
                     "the key is read straight from the device, below the desktop",
                     "你不在 `input` 组里，所以一个键盘也打不开 —— "
                     "按键是直接从设备读的，在桌面之下",
                     "คุณไม่ได้อยู่ในกลุ่ม `input` จึงเปิดคีย์บอร์ดไม่ได้เลย — "
                     "ปุ่มถูกอ่านจากอุปกรณ์โดยตรง ใต้ระดับเดสก์ท็อป"),
 # The button beside this runs install.sh, which starts the daemon through
 # newgrp; "log out and back in" was the only advice for as long as nothing
 # could do that for you.
 "set.key.relogin": ("you are in the `input` group, but this session started before that — "
                     "the daemon can be started with the group now, no logout needed",
                     "你已经在 `input` 组里了，但这次登录发生在加入之前 —— 可以让 daemon 当场带着组权限启动，不用重新登录",
                     "คุณอยู่ในกลุ่ม `input` แล้ว แต่เซสชันนี้เริ่มก่อนหน้านั้น — เริ่มเดมอนพร้อมสิทธิ์กลุ่มได้เลย ไม่ต้องออกจากระบบ"),
 "set.key.nodevice": ("no keyboard here reports %1 — press a different key",
                      "这里没有键盘会报出 %1 —— 换一个键按",
                      "ไม่มีคีย์บอร์ดที่นี่รายงาน %1 — กดปุ่มอื่น"),
 "set.key.stopped": ("the background service is not running, so nothing is listening",
                     "后台服务没有在运行，所以没有任何东西在监听",
                     "บริการเบื้องหลังไม่ได้ทำงาน จึงไม่มีอะไรกำลังฟัง"),
 "set.key.stale":   ("the service is still listening on %1 — it never picked up the change",
                     "服务还在监听 %1 —— 它没有接到这次改动",
                     "บริการยังฟังที่ %1 — มันไม่ได้รับการเปลี่ยนแปลงนี้"),
 "set.key.off":     ("the hotkey is switched off",
                     "快捷键被关掉了", "ปุ่มลัดถูกปิดอยู่"),
 "set.key.fix.restart": ("Restart it", "重启它", "รีสตาร์ต"),
 "set.key.fix.regroup": ("Start it with the group", "带上组权限启动", "เริ่มพร้อมสิทธิ์กลุ่ม"),
 "set.key.fix.group":   ("Add me to `input`", "把我加进 `input`", "เพิ่มฉันเข้า `input`"),
 "set.hotkeynote": ("Read from evdev, below xkb, so the key stays where it physically is even "
                    "if your layout remaps it. A modifier cannot be bound in Hyprland instead: "
                    "pressing one changes the modmask, which fires the release binding at once "
                    "and records a 0.0s take.",
                    "直接从 evdev 读取，位于 xkb 之下，所以即使你的键盘布局把它重映射了，这个键的物理位置也不变。"
                    "换成在 Hyprland 里绑一个修饰键是不行的：按下修饰键会改变 modmask，"
                    "松开绑定会立刻触发，录出一条 0.0 秒的记录。",
                    "อ่านจาก evdev ซึ่งอยู่ต่ำกว่า xkb ปุ่มจึงอยู่ตำแหน่งจริงเสมอแม้เลย์เอาต์จะรีแมป "
                    "จะผูกปุ่มมอดิฟายเออร์ใน Hyprland แทนไม่ได้: การกดมันเปลี่ยน modmask "
                    "ทำให้ทริกเกอร์ปล่อยปุ่มทำงานทันทีและได้รายการยาว 0.0 วินาที"),
 "set.audio":      ("AUDIO", "音频", "เสียง"),
 "set.preroll":    ("pre-roll", "前置缓冲", "บัฟเฟอร์นำหน้า"),
 "set.prerollwhy": ("Audio kept from before the key went down. Lower it and the first syllable "
                    "starts going missing while PipeWire opens the stream.",
                    "保留按键按下之前的一段音频。调小了，PipeWire 打开音频流的这段时间里第一个音节就会开始丢。",
                    "เสียงที่เก็บไว้ก่อนกดปุ่ม ถ้าลดลง พยางค์แรกจะเริ่มหายไปช่วงที่ PipeWire เปิดสตรีม"),
 "set.tail":       ("tail", "尾部延时", "ส่วนท้าย"),
 "set.warnbelow":  ("warn below", "低于则警告", "เตือนเมื่อต่ำกว่า"),
 "set.maxtake":    ("max take", "单次上限", "ความยาวสูงสุด"),
 "set.hud":        ("HUD", "HUD", "HUD"),
 "set.hud.show":   ("show the overlay", "显示浮层", "แสดงหน้าต่างซ้อน"),
 "set.hud.size":   ("size", "大小", "ขนาด"),
 "set.size.xs":    ("tiny", "极小", "จิ๋ว"),
 "set.size.s":     ("small", "小", "เล็ก"),
 "set.size.m":     ("large", "大", "ใหญ่"),
 "set.keepup":     ("keep the result up", "结果保持显示", "คงผลลัพธ์ไว้บนจอ"),
 "set.hudnote":    ("\"changed\" is the default: a dwell you always pay for turns into noise "
                    "the moment you dictate two sentences in a row, but a silent correction you "
                    "never saw is worse.",
                    "默认是 \"changed\"：每次都停留一下，等你连着说两句话就变成了干扰；"
                    "但一次你根本没看见的静默改写更糟。",
                    "ค่าเริ่มต้นคือ \"changed\": การค้างจอทุกครั้งจะกลายเป็นสิ่งรบกวนทันทีที่คุณพูดสองประโยคติดกัน "
                    "แต่การแก้ไขเงียบ ๆ ที่คุณไม่เคยเห็นแย่กว่า"),
 "set.notifications":("notifications", "通知", "การแจ้งเตือน"),
 "set.on":         ("on", "开", "เปิด"),
 "set.off":        ("off", "关", "ปิด"),
 "set.history":    ("HISTORY", "历史", "ประวัติ"),
 "set.keepaudio":  ("keep audio for", "保留音频", "เก็บเสียงไว้"),
 "set.takes":      (" takes", " 条", " รายการ"),
 "set.historynote":("Stored audio is what makes re-running a take on another model, and the "
                    "names dry run, possible. Set it to 0 and those go away with it.",
                    "存下的音频是「换个模型重跑一次」和名称试运行的前提。设成 0，这两个功能也一起没了。",
                    "เสียงที่เก็บไว้คือสิ่งที่ทำให้รันรายการเดิมด้วยโมเดลอื่น และการทดลองรันชื่อ เป็นไปได้ "
                    "ตั้งเป็น 0 แล้วสองอย่างนั้นก็หายไปด้วย"),
 "set.neverleaves":("Audio never leaves this machine", "音频永不离开本机",
                    "เสียงไม่เคยออกจากเครื่องนี้"),
 # The banner above was unconditional, and the console offers a remote
 # speech engine — so selecting it left a green "audio never leaves this
 # machine" over an engine that uploads every take. A privacy claim is the
 # worst thing in the program to be wrong about.
 "set.audioleaves":("Audio is uploaded to %1",
                    "音频会被上传到 %1",
                    "เสียงถูกอัปโหลดไปที่ %1"),
 "set.privacynote.api":("The speech engine is a remote API, so every take's audio "
                        "leaves this machine. The Models tab has the endpoint, and "
                        "the two local engines there keep audio on the GPU.",
                        "语音引擎用的是远程 API，所以每次录音的音频都会离开本机。"
                        "端点在「模型」标签页里，那里的两个本地引擎会把音频留在 GPU 上。",
                        "เครื่องยนต์เสียงเป็น API ระยะไกล ดังนั้นเสียงของทุกครั้งที่อัดจะออกจากเครื่องนี้ "
                        "ปลายทางอยู่ในแท็บโมเดล และเครื่องยนต์ในเครื่องสองตัวที่นั่นเก็บเสียงไว้บน GPU"),
 "set.privacynote":("Speech runs on the local GPU in every mode. A mode whose LLM step is a "
                    "remote model does send the transcribed text out — the Modes tab shows "
                    "which ones have a step at all.",
                    "所有模式的语音识别都跑在本地 GPU 上。但如果某个模式的 LLM 步骤用的是远程模型，"
                    "转写出来的文本确实会发出去 —— 「模式」页里可以看到哪些模式有 LLM 步骤。",
                    "การถอดเสียงทำงานบน GPU ในเครื่องทุกโหมด แต่โหมดที่ขั้น LLM ใช้โมเดลระยะไกล "
                    "จะส่งข้อความที่ถอดได้ออกไปจริง — แท็บโหมดแสดงว่าโหมดใดมีขั้นนั้นบ้าง"),
 "set.editconfig": ("Edit config", "编辑配置", "แก้ไฟล์ตั้งค่า"),
 "set.restart":    ("Restart daemon", "重启守护进程", "รีสตาร์ตเดมอน"),
 "set.configpath": ("everything here is  ~/.config/omavoi/config.toml",
                    "这里的一切都在  ~/.config/omavoi/config.toml",
                    "ทุกอย่างในหน้านี้อยู่ที่  ~/.config/omavoi/config.toml"),
})

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "packs"))
EXTRA = {}
for _code in ("de", "fr", "es", "ja", "vi"):
    EXTRA[_code] = __import__(_code).PACK


def q(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"' if False else '"' + s.replace('"', '\\"') + '"'

def emit(lang, idx):
    out = []
    for name, entries in SECTIONS:
        out.append("      // ---- %s" % name)
        for k, v in entries.items():
            val = v[idx] if idx is not None else EXTRA[lang].get(k, v[0])
            out.append("      %s: %s," % (q(k), q(val)))
        out.append("")
    body = "\n".join(out).rstrip().rstrip(",")
    return "    %s: {\n%s\n    },\n" % (lang, body)

buf = io.StringIO()
buf.write(HEADER)
buf.write("  readonly property var _table: ({\n")
LANGS = [("en", 0), ("zh", 1), ("th", 2),
         ("de", None), ("fr", None), ("es", None), ("ja", None), ("vi", None)]
for lang, idx in LANGS:
    buf.write(emit(lang, idx))
s = buf.getvalue().rstrip().rstrip(",")
s += "\n  })\n}\n"
open(os.path.join(_HERE, "..", "..", "Strings.qml"), "w").write(s)

n = sum(len(e) for _, e in SECTIONS)
keys = {k for _, e in SECTIONS for k in e}

# Drift, reported as a failure rather than a line of output. Printing it and
# exiting 0 is how a pack loses a key and nobody notices until a user sees a
# dotted identifier where a sentence should be.
problems = []
for code, pack in EXTRA.items():
    missing = keys - set(pack)
    extra = set(pack) - keys
    if missing:
        problems.append(f"{code}: missing {sorted(missing)}")
    if extra:
        problems.append(f"{code}: has keys the canonical set does not: {sorted(extra)}")

# And the other direction: a key the interface asks for and the table has not
# got renders as the identifier itself, silently.
_ROOT = os.path.join(_HERE, "..", "..")
DYNAMIC = {f"modes.inject.{v}" for v in ("auto", "clipboard", "xdotool")} | {
    f"state.{v}" for v in ("idle", "recording", "transcribing", "stopped")} | {
    f"hud.stage.{v}" for v in ("decoding", "llm", "injecting")}
# Conservative on purpose. An earlier version of this check looked only for
# a literal immediately after `t(`, which misses
#     root.t(root.unifiedMem ? "models.shared" : "models.vram")
# — and on that evidence four live keys were deleted and the VRAM footer
# rendered its own identifiers. A key counts as used if it appears anywhere in
# any of these files, in any form.
source = ""
for name in sorted(os.listdir(_ROOT)):
    if name.endswith(".qml") and name != "Strings.qml":
        source += open(os.path.join(_ROOT, name), encoding="utf-8").read()
asked = {k for k in keys if '"%s"' % k in source}
# Only a literal immediately after t( can be checked in the other direction:
# anything else may be a key this table is not responsible for.
requested = set(re.findall(r'\bt[f]?\("([^"]+)"', source))
absent = sorted(a for a in requested if a not in keys and not a.endswith("."))
if absent:
    problems.append(f"used in QML and not in the table: {absent}")
unused = sorted(keys - asked - DYNAMIC)
if unused:
    problems.append(f"in the table and never used: {unused}")

print("keys per language:", n, "· languages:", len(LANGS),
      "· total entries:", n * len(LANGS))
for line in problems:
    print("  " + line)
if problems:
    raise SystemExit(1)
