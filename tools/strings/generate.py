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
 # Three, not two: the push-to-talk key was added as a third question and
 # this sentence stayed behind, in all eight languages.
 "first.blurb":     ("Three questions, then one button. Nothing runs until you press it, "
                     "and every command is shown first.",
                     "三个问题，然后一个按钮。你按下之前什么都不会执行，而且每条命令都会先显示出来。",
                     "สามคำถาม แล้วปุ่มเดียว ไม่มีอะไรทำงานจนกว่าคุณจะกด และทุกคำสั่งจะแสดงให้ดูก่อน"),
 "first.pick.language": ("Interface language", "界面语言", "ภาษาของหน้าจอ"),
 "first.pick.model":    ("Speech model", "语音模型", "โมเดลเสียงพูด"),
 "first.reuse":     ("a voice model already on this machine — used where it lies, nothing to "
                     "download",
                     "这台机器上已有的语音模型 —— 就地使用，无需下载",
                     "โมเดลเสียงที่มีอยู่แล้วบนเครื่องนี้ — ใช้ตามที่อยู่เดิม ไม่ต้องดาวน์โหลด"),
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
                     "密码框被取消了，所以什么都没有安装",
                     "กล่องรหัสผ่านถูกยกเลิก จึงไม่มีอะไรถูกติดตั้ง"),
 "first.done":      ("Ready — hold your key and talk", "完成 —— 按住热键说话",
                     "พร้อมแล้ว — กดปุ่มค้างไว้แล้วพูด"),
 # Split in two so the count sits in a sentence of its own. It used to be
 # one string with "%1 days old" in it, and a database exactly one day old —
 # which is every machine that has not synced today, because the threshold is
 # a day — was told it was "1 days old".
 "first.dbstale.age": ("Your package database is %1 days old.",
                    "你的软件包数据库是 %1 天前的。",
                    "ฐานข้อมูลแพ็กเกจของคุณเก่า %1 วัน"),
 "first.dbstale.age1": ("Your package database is a day old.",
                    "你的软件包数据库是一天前的。",
                    "ฐานข้อมูลแพ็กเกจของคุณเก่าหนึ่งวัน"),
 "first.dbstale":   ("Installing anything now fails with 404: the versions it lists are no "
                    "longer on the mirrors. Arch needs a system update before new packages "
                    "either way.",
                    "现在装任何东西都会 404 失败 —— 它记录的版本在镜像上已经不存在了。"
                    "Arch 在装新包之前本来就需要先更新系统。",
                    "การติดตั้งตอนนี้จะล้มเหลวด้วย 404 เพราะเวอร์ชันที่ระบุไว้ไม่มีบนมิเรอร์แล้ว "
                    "Arch ต้องอัปเดตระบบก่อนติดตั้งแพ็กเกจใหม่อยู่ดี"),
 "first.updatebtn": ("Update system packages", "更新系统软件包", "อัปเดตแพ็กเกจของระบบ"),
 "first.pacman404": ("The package database is out of date, so the mirrors no longer have the "
                     "versions it lists. Update the system above, then try again.",
                     "软件包数据库过期了，镜像上已经没有它记录的那些版本。先用上面那个按钮更新系统，"
                     "再重试。",
                     "ฐานข้อมูลแพ็กเกจล้าสมัย มิเรอร์จึงไม่มีเวอร์ชันที่ระบุไว้อีกแล้ว "
                     "อัปเดตระบบด้านบนแล้วลองอีกครั้ง"),
 "first.pick.hotkey": ("Push-to-talk key", "按住说话的键", "ปุ่มกดค้างเพื่อพูด"),
 "first.hotkey.other": ("another key, e.g. F9", "其他键，例如 F9", "ปุ่มอื่น เช่น F9"),
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
                        "你还不在 input 组里，所以任何键都读不到。下面那一步会把你加进去，"
                        "而且 daemon 会以当场就能拿到组权限的方式启动 —— 不需要重新登录。",
                        "คุณยังไม่อยู่ในกลุ่ม input จึงอ่านปุ่มใดไม่ได้ ขั้นด้านล่างจะเพิ่มคุณเข้าไป "
                        "และเดมอนจะเริ่มในแบบที่รับสิทธิ์กลุ่มได้ทันที — ไม่ต้องออกจากระบบ"),
 "first.step.hotkey": ("hotkey", "快捷键", "ปุ่มลัด"),
 "first.step.packages": ("system packages", "系统软件包", "แพ็กเกจของระบบ"),
 "first.step.daemon":   ("the daemon", "守护进程", "เดมอน"),
 "first.step.language": ("language", "语言", "ภาษา"),
 "first.step.weights":  ("voice model", "语音模型", "โมเดลเสียง"),
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
 "up.daemon.blind": ("The background service is installed separately, so this cannot tell whether it is current; updating reinstalls it either way.",
    "后台服务是单独安装的，这里看不出它是不是最新；「开始更新」会一并重装它。",
    "บริการเบื้องหลังติดตั้งแยก จึงบอกไม่ได้ว่าเป็นรุ่นล่าสุดหรือไม่ แต่การอัปเดตจะติดตั้งใหม่ให้ด้วย"),
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
                  "已安装的插件里有本地改动，所以无法 fast-forward。重新安装它："
                  "omarchy plugin remove ai.bkblab.omavoi --yes && "
                  "omarchy plugin add %1 --enable --yes",
                  "ปลั๊กอินที่ติดตั้งมีการเปลี่ยนแปลงในเครื่อง จึง fast-forward ไม่ได้ ติดตั้งใหม่: "
                  "omarchy plugin remove ai.bkblab.omavoi --yes && "
                  "omarchy plugin add %1 --enable --yes"),
 "up.run":       ("Update", "开始更新", "อัปเดต"),
 "up.again":     ("Check again", "再检查一次", "ตรวจอีกครั้ง"),
 "up.done":      ("Updated", "已更新", "อัปเดตแล้ว"),
 "up.step.plugin":  ("the plugin", "插件", "ปลั๊กอิน"),
 "up.step.daemon": ("the background service",
    "后台服务",
    "บริการเบื้องหลัง"),
 "up.step.shortcuts": ("unit, keybinding and menu entry", "服务、快捷键与菜单项",
                       "ยูนิต ปุ่มลัด และรายการในเมนู"),
 "up.step.restart": ("restart", "重启服务", "รีสตาร์ต"),
})

section("shared-and-setup", {
 # Not "ตั้งค่า": that is nav.settings, and the two tabs sit side by side
 # while an install is unfinished.
 "nav.setup": ("Setup", "安装", "การติดตั้ง"),
 "setup.rootblurb": ("The steps above that need root can be done here, in one password prompt — polkit treats pacman as auth_admin, so asking in two calls means being asked twice. The daemon is restarted afterwards: it remembers a missing engine for the life of the process, so installing the binary alone would leave it still saying the engine is not there.", "上面需要 root 的步骤可以在这里一次做完，只弹一次密码框 —— polkit 把 pacman 当作 auth_admin，分两次调用就会问两次密码。装完会重启守护进程：它对「引擎未安装」的判断在进程存活期间是缓存的，只装二进制的话它仍会说引擎不在。", "ขั้นตอนด้านบนที่ต้องใช้ root ทำได้จากที่นี่ในการถามรหัสผ่านครั้งเดียว — polkit ถือว่า pacman เป็น auth_admin ถ้าเรียกสองครั้งก็จะถูกถามสองครั้ง หลังจากนั้นจะรีสตาร์ตเดมอน เพราะมันจำว่าเอนจินไม่มีอยู่ไปตลอดอายุโปรเซส การติดตั้งไบนารีอย่างเดียวจึงยังทำให้มันบอกว่าไม่มีเอนจิน"),
 "setup.rootrun": ("Install these", "一次装好", "ติดตั้งทั้งหมดนี้"),
 "setup.optional": ("optional", "可选", "ไม่บังคับ"),
 # OmTextArea, which is every decoder hint and every LLM prompt on the Modes
 # tab — the three words a person editing one looks at most.
 "edit.unsaved":  ("unsaved", "未保存", "ยังไม่บันทึก"),
 "edit.revert":   ("Revert", "还原", "ย้อนกลับ"),
 "edit.save":     ("Save", "保存", "บันทึก"),
})

# The bar module. Seven sentences were compiled into BarWidget.qml in
# English, on the one surface that is on screen whatever else is.
section("bar", {
 "bar.stopped":          ("stopped", "已停止", "หยุดอยู่"),
 "bar.tip.notinstalled": ("Omavoi — not installed yet. Click to set it up.",
                          "Omavoi —— 还没有安装。点击开始设置。",
                          "Omavoi — ยังไม่ได้ติดตั้ง คลิกเพื่อตั้งค่า"),
 "bar.tip.stopped":      ("Omavoi — the background service is not running. "
                          "Click to open the console.",
                          "Omavoi —— 后台服务没有在运行。点击打开控制台。",
                          "Omavoi — บริการเบื้องหลังไม่ได้ทำงาน คลิกเพื่อเปิดคอนโซล"),
 "bar.tip.recording":    ("Recording · release the key to transcribe",
                          "录音中 · 松开按键开始转写",
                          "กำลังอัด · ปล่อยปุ่มเพื่อถอดเสียง"),
 "bar.tip.transcribing": ("Transcribing…", "转写中……", "กำลังถอดเสียง…"),
 "bar.tip.unfinished":   ("Omavoi — setup unfinished (%1)",
                          "Omavoi —— 安装还没完成（%1）",
                          "Omavoi — ตั้งค่ายังไม่เสร็จ (%1)"),
 "bar.tip.ready":        ("Omavoi — ready", "Omavoi —— 就绪", "Omavoi — พร้อมแล้ว"),
 # Right-click starts and stops a take by hand, and this is the only place
 # that says so.
 "bar.tip.rightclick":   ("Right-click to start or stop a take",
                          "右键开始或停止一次录音",
                          "คลิกขวาเพื่อเริ่มหรือหยุดการอัด"),
})

section("nav", {
 "nav.history":     ("History", "历史", "ประวัติ"),
 "nav.modes":       ("Modes", "模式", "โหมด"),
 "nav.models":      ("Models", "模型", "โมเดล"),
 "nav.dictionary":  ('My dictionary', '我的词典', 'พจนานุกรมของฉัน'),
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
 "hist.problems": ("WHAT WENT WRONG",
    "出了什么问题",
    "เกิดอะไรขึ้น"),
 "hist.fellthrough": ("did not work — the text from before it was used",
    "没有成功，用的是改写前的文字",
    "ไม่สำเร็จ — จึงใช้ข้อความก่อนหน้า"),
 "hist.none":      ("no takes yet — hold %1 and talk", "还没有记录 —— 按住 %1 说话",
                    "ยังไม่มีรายการ — กด %1 ค้างไว้แล้วพูด"),
 "hist.yourkey":   ("your key", "你的按键", "ปุ่มของคุณ"),
 "hist.audio": ("length",
    "录音时长",
    "ความยาว"),
 "hist.level": ("loudness",
    "音量",
    "ความดัง"),
 "hist.decode": ("recognition took",
    "识别用时",
    "เวลารู้จำ"),
 "hist.model":     ("model", "模型", "โมเดล"),
 "hist.language":  ("language", "语言", "ภาษา"),
 "hist.injected": ("typed with",
    "输入方式",
    "ป้อนด้วย"),
 "hist.said": ("WHAT IT HEARD",
    "识别原文",
    "สิ่งที่ได้ยิน"),
 "hist.post": ("WHAT THE CLEANUP CHANGED",
    "整理改了什么",
    "การจัดข้อความแก้อะไร"),
 "hist.segments":  ("SEGMENT CONFIDENCE", "分段置信度", "ความมั่นใจต่อช่วง"),
 "hist.copy":      ("Copy", "复制", "คัดลอก"),
 "hist.play":      ("Play", "播放", "เล่น"),
 # The right-click menu on a take. The two above are in it as well, which is
 # why they are one word each rather than "Copy the text".
 "hist.delete":    ("Delete", "删除", "ลบ"),
 "hist.yesterday": ("yesterday %1",
    "昨天 %1",
    "เมื่อวาน %1"),
 "hist.droppedas": ("dropped · %1",
    "已丢弃 · %1",
    "ทิ้งแล้ว · %1"),
 "hist.drop.short": ("too short (%1 s)",
    "太短了（%1 秒）",
    "สั้นเกินไป (%1 วินาที)"),
 "hist.drop.nospeech": ("no speech heard",
    "没听到说话",
    "ไม่ได้ยินเสียงพูด"),
 "hist.drop.failed": ("recognition failed",
    "识别失败",
    "การรู้จำล้มเหลว"),
 "hist.w.quiet": ("The recording was quiet (%1 dBFS), the usual cause of missed words.",
    "录音音量偏小（%1 dBFS），容易漏字。",
    "เสียงที่อัดเบา (%1 dBFS) ทำให้คำหายได้ง่าย"),
 "hist.w.step": ("AI step %1 (%2) did not work: %3 — the text from before it was used.",
    "第 %1 步 AI 改写（%2）没有成功：%3 —— 用的是改写前的文字。",
    "AI ขั้นที่ %1 (%2) ไม่สำเร็จ: %3 — จึงใช้ข้อความก่อนหน้า"),
 "hist.w.wrapped": ("The start of this take was lost.",
    "这次录音的开头没录上。",
    "ช่วงต้นของการอัดครั้งนี้หายไป"),
 "hist.w.lowconf": ("The recognizer was unsure — some words may be wrong or missing.",
    "识别把握不大，可能有字词错误或遗漏。",
    "โมเดลไม่ค่อยมั่นใจ อาจมีคำผิดหรือหาย"),
 "hist.w.silence": ("Part of it may have been silence — check that part of the text.",
    "有一段可能是静音，请检查对应的文字。",
    "บางช่วงอาจเป็นความเงียบ ลองตรวจข้อความช่วงนั้น"),
 "hist.w.noxdotool": ("This is an X11 window and xdotool is not installed, so the text could not reach it.",
    "这是 X11 窗口，但没装 xdotool，文字进不了它。",
    "หน้าต่างนี้เป็น X11 แต่ไม่ได้ติดตั้ง xdotool ข้อความจึงเข้าไม่ถึง"),
 "hist.w.script": ("Converting the Chinese characters failed, so the text was kept as recognized.",
    "简繁转换失败，保留了识别原文。",
    "แปลงตัวอักษรจีนไม่สำเร็จ จึงเก็บข้อความเดิมไว้"),
 "hist.w.fellback": ("Typing switched to %1 for this window.",
    "这次改用 %1 输入。",
    "ครั้งนี้เปลี่ยนไปป้อนด้วย %1"),
 "hist.w.injectfailed": ("The text could not be typed into the window.",
    "文字没能输入到窗口里。",
    "ป้อนข้อความเข้าหน้าต่างไม่สำเร็จ"),
 "hist.c.fillers": ("removed filler words",
    "去掉了语气词",
    "ตัดคำเติมออก"),
 "hist.c.deduped": ("collapsed repeated sentences",
    "合并了重复的句子",
    "รวมประโยคที่ซ้ำ"),
 "hist.c.spacing": ("spaced CJK and Latin apart",
    "中西文之间加了空格",
    "เว้นวรรคระหว่าง CJK กับละติน"),
 "hist.c.lines": ("joined the lines",
    "合并了换行",
    "รวมบรรทัด"),
 "hist.c.punct": ("dropped the end punctuation",
    "去掉了句末标点",
    "ตัดเครื่องหมายท้ายประโยค"),
 "hist.c.dictionary": ("corrected from My dictionary: %1",
    "按「我的词典」纠正：%1",
    "แก้ตามพจนานุกรมของฉัน: %1"),
 "hist.c.silence": ("left out a stretch of silence",
    "去掉了一段静音",
    "ตัดช่วงเงียบออก"),
 "hist.c.hans": ("converted to Simplified Chinese",
    "转成了简体",
    "แปลงเป็นจีนตัวย่อ"),
 "hist.c.hant": ("converted to Traditional Chinese",
    "转成了繁体",
    "แปลงเป็นจีนตัวเต็ม"),
 "hist.took": ("took %1 s",
    "用时 %1 秒",
    "ใช้เวลา %1 วินาที"),
 "hist.details": ("DETAILS",
    "技术细节",
    "รายละเอียด"),
 "hist.rtfnote": ("RTF is how long recognition took against how long you spoke; under 1 is faster than real time.",
    "RTF：识别用时 ÷ 说话时长，小于 1 就比实时还快。",
    "RTF คือเวลาที่ใช้รู้จำเทียบกับความยาวเสียง ต่ำกว่า 1 คือเร็วกว่าเวลาจริง"),
 "hist.raw": ("as the background service wrote it",
    "后台服务的原始信息",
    "ข้อความดั้งเดิมจากบริการเบื้องหลัง"),
})

section("modes", {
 # -- the list ---------------------------------------------------------------
 "modes.wontfit":    ("needs %1 free", "需要 %1 空闲显存", "ต้องมี %1 ว่าง"),
 "modes.newname":    ("new mode name", "新模式名称", "ชื่อโหมดใหม่"),
 # Window matching is switched off (ModesView's showWindowMatch), so a mode
 # is global: "here" and "active in this window" were describing a scope the
 # console no longer has.
 "modes.here":       ("in use", "使用中", "ใช้อยู่"),
 # The line under each mode's name: what sets it apart, not the chain. Every
 # chain started "speech →", so the old line told code, terminal and default
 # apart by nothing at all.
 "modes.sum.ai":     ("AI: %1", "AI：%1", "AI: %1"),
 "modes.sum.plain":  ("no AI", "不经过 AI", "ไม่ผ่าน AI"),
 "modes.sum.hans":   ("Simplified Chinese", "简体", "จีนตัวย่อ"),
 "modes.sum.hant":   ("Traditional Chinese", "繁体", "จีนตัวเต็ม"),
 "modes.sum.nopunct":("no end punctuation", "不加句末标点", "ไม่มีเครื่องหมายท้ายประโยค"),
 "modes.sum.paste":  ("pastes", "粘贴", "วาง"),
 "modes.sum.type":   ("types", "逐字输入", "พิมพ์ทีละตัว"),
 # Above the list, a choice between two, where it was a chip above the
 # detail pane whose label was its own state.
 "modes.pick.title": ("switching", "模式切换", "การสลับโหมด"),
 "modes.fixed":      ("pick here", "手动选择", "เลือกเอง"),
 "modes.following":  ("follow the window", "跟随窗口", "ตามหน้าต่าง"),
 # Said beside the switch that turns it off, not instead of one. It used to end
 # "turn it off with `omavoi mode auto off`", which was the only way there was:
 # the switch itself lives inside the matching controls, and those are hidden.
 # Short, because it wraps inside the 280-pixel list.
 "modes.hiddenauto": ("The focused window picks the mode, so clicking one below only opens it.",
                      "由当前焦点窗口决定模式，点下面的模式只会打开它。",
                      "หน้าต่างที่โฟกัสเป็นตัวเลือกโหมด การคลิกโหมดด้านล่างจึงแค่เปิดดู"),
 # -- window matching, hidden with it ------------------------------------------
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
 # -- header -------------------------------------------------------------------
 "modes.blocked":    ("not switched — this mode's model will not fit in VRAM right now",
                      "未切换 —— 这个模式的模型现在装不进显存",
                      "ไม่ได้สลับ — โมเดลของโหมดนี้ใส่ใน VRAM ตอนนี้ไม่พอ"),
 "modes.delete":     ("Delete mode", "删除模式", "ลบโหมด"),
 # -- voice ----------------------------------------------------------------------
 # Section titles are capitals in English, like every other tab's, and carry
 # no number: the fold below mixes stages, so 1-2-3-4 would count wrong.
 "modes.s1":         ("VOICE", "语音识别", "เสียงพูด"),
 "modes.language":   ("spoken language", "识别语言", "ภาษาที่พูด"),
 "modes.langsearch": ("Search languages…", "搜索语言…", "ค้นหาภาษา…"),
 "modes.langempty":  ("No matching languages", "没有匹配的语言", "ไม่พบภาษาที่ตรงกัน"),
 "modes.langupgrade":("Update the speech service to choose an input language.",
                      "更新语音服务后可选择输入语言。", "อัปเดตบริการเสียงเพื่อเลือกภาษาพูด"),
 "modes.langauto":   ("auto", "自动", "อัตโนมัติ"),
 # Shown only for a pinned language. The note it replaces said auto "detects
 # speech without changing its script" and left out the cost of the other
 # choices: every one of them, Chinese included, stops the detection.
 "modes.langfixed":  ("Listens for this language only: steadier when it is what you speak, but "
                      "other languages may come out wrong.",
                      "只按这种语言识别：主要说它时更稳，说其他语言可能会识别错。",
                      "ฟังเฉพาะภาษานี้ แม่นขึ้นถ้าพูดภาษานี้เป็นหลัก แต่ภาษาอื่นอาจออกมาผิด"),
 # Its own setting now, beside the language rather than two entries in it —
 # which is how auto-detection with Simplified output became choosable.
 "modes.script":     ("Chinese characters", "中文用字", "ตัวอักษรจีน"),
 "modes.script.none":("as recognized", "不转换", "ไม่แปลง"),
 "modes.script.hans":("simplified", "简体", "ตัวย่อ"),
 "modes.script.hant":("traditional", "繁体", "ตัวเต็ม"),
 # -- cleanup --------------------------------------------------------------------
 # A chip is a thing that happens when it is lit, so each says what it does.
 # The punctuation one said "keep", the one chip in the row lit for not acting.
 "modes.s2":         ("CLEANUP", "整理", "จัดข้อความ"),
 "modes.rulessub":   ("No AI: instant, and the same every time.",
                      "不经过 AI，即时完成，每次结果都一样。",
                      "ไม่ผ่าน AI ทำทันที และได้ผลเหมือนกันทุกครั้ง"),
 "modes.r.fillers":  ("remove filler words", "去掉语气词", "ตัดคำเติม"),
 "modes.r.cjk":      ("space between CJK and Latin", "中西文之间加空格", "เว้นวรรคระหว่าง CJK กับละติน"),
 "modes.droppunct":  ("drop end punctuation", "去掉句末标点", "ตัดเครื่องหมายท้ายประโยค"),
 # -- ai rewrite -----------------------------------------------------------------
 "modes.s3":         ("AI REWRITE", "AI 改写", "AI เขียนใหม่"),
 "modes.llmsub":     ("Optional. Each step adds a few seconds; one that fails passes on the text "
                      "it was given.",
                      "可选。每一步都要多等几秒；某一步出错时，把它收到的文字原样往下传。",
                      "ไม่บังคับ แต่ละขั้นใช้เวลาเพิ่มอีกไม่กี่วินาที ถ้าขั้นไหนล้มเหลว "
                      "ข้อความที่มันได้รับจะถูกส่งต่อไปตามเดิม"),
 "modes.step":       ("step ", "第 ", "ขั้น "),
 "modes.stepsuffix": ("", " 步", ""),
 "modes.remove":     ("Remove", "移除", "เอาออก"),
 "modes.stepph":     ("Tell it to edit, not to reply.", "让它改写，不要让它回答。",
                      "สั่งให้แก้ข้อความ ไม่ใช่ให้ตอบ"),
 # An action that asks which LLM, where it was a row of chips shaped exactly
 # like the ones that choose a step's LLM.
 "modes.addstep":    ("+ add a rewrite step", "+ 添加改写步骤", "+ เพิ่มขั้นเขียนใหม่"),
 "modes.addwhich":   ("rewrite with:", "用哪个改写：", "เขียนใหม่ด้วย:"),
 "modes.weights":    ("model", "模型", "โมเดล"),
 "modes.inherit":    ("use the default (%1)", "用默认的（%1）", "ใช้ค่าเริ่มต้น (%1)"),
 "modes.nollm":      ("no LLM is configured — see the Models tab", "还没有配置 LLM —— 去「模型」页",
                      "ยังไม่ได้ตั้งค่า LLM — ดูที่แท็บโมเดล"),
 # -- advanced -------------------------------------------------------------------
 "modes.adv":        ("ADVANCED", "高级", "ขั้นสูง"),
 # On the closed fold: whatever in it is off its default, so folding a
 # setting away never hides one somebody changed.
 "modes.adv.changed":("changed: %1", "已改：%1", "เปลี่ยนแล้ว: %1"),
 "modes.adv.sep":    (", ", "、", ", "),
 "modes.adv.kv":     ("%1: %2", "%1：%2", "%1: %2"),
 "modes.speechmodel": ("voice model", "语音模型", "โมเดลเสียง"),
 "modes.speechglobal": ("use the default", "用默认的", "ใช้ค่าเริ่มต้น"),
 "modes.speechglobalnamed": ("use the default (%1)", "用默认的（%1）", "ใช้ค่าเริ่มต้น (%1)"),
 "modes.speechonly1": ("Only one voice model is downloaded. The Models tab has smaller ones, for a "
                       "mode where speed matters more than accuracy.",
                       "只下载了一个语音模型。「模型」页有更小的，适合速度比准确率更重要的模式。",
                       "ดาวน์โหลดโมเดลเสียงไว้ตัวเดียว แท็บโมเดลมีตัวที่เล็กกว่า "
                       "เหมาะกับโหมดที่เน้นความเร็วมากกว่าความแม่น"),
 "modes.speechnone": ("No voice model is downloaded yet — the Models tab has them.",
                      "还没有下载语音模型——到「模型」页下载。",
                      "ยังไม่ได้ดาวน์โหลดโมเดลเสียง — ดาวน์โหลดได้ที่แท็บโมเดล"),
 "modes.speechreload": ("Switching to this mode loads that model first, which takes a few seconds.",
                        "切换到这个模式时要先加载这个模型，需要几秒钟。",
                        "เมื่อสลับมาโหมดนี้ต้องโหลดโมเดลนี้ก่อน ใช้เวลาไม่กี่วินาที"),
 # The decoder prompt. "vocabulary" asked for a list of words, which is what
 # My dictionary now feeds the decoder on its own; what is left for this box
 # is the context a mode is spoken in.
 "modes.decoderhint": ("recognition hint", "识别提示", "คำใบ้การถอดเสียง"),
 "modes.promptph":   ("e.g. A meeting about Hyprland, Quickshell and PipeWire.",
                      "例如：关于 Hyprland、Quickshell 和 PipeWire 的技术讨论。",
                      "เช่น การประชุมเรื่อง Hyprland, Quickshell และ PipeWire"),
 "modes.prompthint": ("Read by the recognizer before it listens — a nudge, not a guarantee. Words "
                      "in My dictionary are added to it on their own.",
                      "识别模型开始听之前会先读这段话，只是提示，不保证生效。「我的词典」里的词会自动加进来。",
                      "โมเดลจะอ่านข้อความนี้ก่อนเริ่มฟัง เป็นแค่คำใบ้ ไม่รับประกันผล "
                      "คำใน พจนานุกรมของฉัน จะถูกเพิ่มเข้าไปเอง"),
 "modes.promptinherited": ("This mode has no hint of its own, so it uses default's. Saving here "
                           "gives it one.",
                           "这个模式没有自己的识别提示，用的是 default 的；在这里保存，就成了它自己的。",
                           "โหมดนี้ไม่มีคำใบ้ของตัวเอง จึงใช้ของ default บันทึกที่นี่แล้วจะเป็นของโหมดนี้เอง"),
 "modes.adv.cleanup":("cleanup", "整理", "จัดข้อความ"),
 # What the flag does: collapse "好的。好的。好的。". It was called "made-up
 # phrases", and switching it off kept none — a segment measured as silence
 # is dropped whatever it says.
 "modes.r.hallucinations": ("collapse repeated sentences", "合并重复的句子", "รวมประโยคที่ซ้ำ"),
 "modes.r.dictionary":("dictionary", "词典", "พจนานุกรม"),
 "modes.r.names":    ("names", "名称", "ชื่อเฉพาะ"),
 "modes.s4":         ("typing", "输入方式", "วิธีป้อนข้อความ"),
 "modes.inject.auto":      ("auto", "自动", "อัตโนมัติ"),
 "modes.inject.type":      ("type it", "逐字输入", "พิมพ์ทีละตัว"),
 "modes.inject.clipboard": ("paste it", "粘贴", "วาง"),
 # One per route, describing the one chosen. The note these replace said auto
 # pastes into X11 apps; it types into them, with xdotool, and pastes into
 # Electron apps and Chromium browsers — inject.clipboard_classes.
 "modes.inject.hint.auto": ("Types the text, except in Electron apps such as VS Code and Slack and "
                            "in Chromium browsers, where it pastes. X11 apps are typed with xdotool.",
                            "逐字输入；在 VS Code、Slack 这类 Electron 应用和 Chromium 系浏览器里改为粘贴。"
                            "X11 程序用 xdotool 输入。",
                            "พิมพ์ทีละตัว ยกเว้นในแอป Electron อย่าง VS Code และ Slack "
                            "และเบราว์เซอร์ตระกูล Chromium ที่จะวางแทน แอป X11 พิมพ์ด้วย xdotool"),
 "modes.inject.hint.type": ("Always types, through wtype — except X11 apps, which are typed with "
                            "xdotool.",
                            "总是用 wtype 逐字输入；X11 程序例外，改用 xdotool。",
                            "พิมพ์ทีละตัวด้วย wtype เสมอ ยกเว้นแอป X11 ที่ใช้ xdotool"),
 "modes.inject.hint.paste": ("Always pastes, then puts your clipboard back — except X11 apps, which "
                             "are typed with xdotool.",
                             "总是粘贴，粘贴后恢复你原来的剪贴板；X11 程序例外，改用 xdotool 逐字输入。",
                             "วางเสมอ แล้วคืนค่าคลิปบอร์ดเดิมให้ ยกเว้นแอป X11 ที่พิมพ์ด้วย xdotool"),
})

section("models", {
 "models.speech": ("VOICE RECOGNITION",
    "语音识别",
    "การรู้จำเสียง"),
 "models.speechsub": ("Turns what you say into text. One way at a time.",
    "把你说的话转成文字，同一时间只用一种方式。",
    "แปลงเสียงพูดเป็นข้อความ ใช้ได้ทีละแบบ"),
 "models.e.vulkan": ("On this machine",
    "本机",
    "ในเครื่องนี้"),
 "models.e.vulkan.sub": ("Runs on your graphics card, or on the processor if there is none. Nothing leaves the machine.",
    "在你的显卡上运行（没有显卡就用 CPU），什么都不会离开本机。",
    "ทำงานบนการ์ดจอ (หรือ CPU ถ้าไม่มี) ไม่มีอะไรออกจากเครื่อง"),
 "models.e.vulkan.note": ("audio stays here",
    "声音留在本机",
    "เสียงอยู่ในเครื่อง"),
 "models.e.api":        ("Remote API", "远程 API", "API ระยะไกล"),
 "models.e.api.sub": ("A speech service you point it at — OpenAI, Groq, SiliconFlow or your own server.",
    "交给你指定的在线识别服务，例如 OpenAI、Groq、SiliconFlow 或自建服务。",
    "ส่งให้บริการรู้จำเสียงที่คุณกำหนด เช่น OpenAI, Groq, SiliconFlow หรือเซิร์ฟเวอร์ของคุณเอง"),
 "models.e.api.note":   ("audio leaves this machine", "音频会离开本机",
                         "เสียงจะออกจากเครื่องนี้"),
 "models.now": ("running now",
    "正在运行",
    "กำลังทำงาน"),
 "models.running":   ("running", "运行中", "กำลังทำงาน"),
 "models.notloaded": ("not loaded", "未加载", "ยังไม่ได้โหลด"),
 "models.llmnone": ("none loaded — each starts on its first use",
                    "都未加载 —— 各自在首次用到时启动",
                    "ยังไม่โหลด — แต่ละตัวเริ่มเมื่อถูกใช้ครั้งแรก"),
 "models.coldshort":  ("cold", "未启动", "ยังไม่เริ่ม"),
 "models.ready":     ("ready", "就绪", "พร้อม"),
 "models.nodaemon": ("the background service is not answering, so what is loaded is unknown",
    "连不上后台服务，不知道现在加载了什么",
    "ติดต่อบริการเบื้องหลังไม่ได้ จึงไม่รู้ว่าโหลดอะไรอยู่"),
 "models.f.edit":      ("Edit", "编辑", "แก้ไข"),
 "models.f.close":     ("Close", "收起", "ปิด"),
 "models.f.url": ("address",
    "地址",
    "ที่อยู่"),
 "models.f.model":     ("Model", "模型", "โมเดล"),
 "models.f.key":       ("Key", "密钥", "คีย์"),
 "models.f.key.place": ("paste the key — it is kept in secrets.toml only",
    "粘贴密钥，它只存在 secrets.toml 里",
    "วางคีย์ที่นี่ — เก็บไว้ใน secrets.toml เท่านั้น"),
 "models.f.key.save":  ("Save", "保存", "บันทึก"),
 "models.f.key.saved": ("saved to secrets.toml, readable by you alone",
    "已存入 secrets.toml，只有你能读取",
    "บันทึกลง secrets.toml แล้ว อ่านได้เฉพาะคุณ"),
 "models.f.key.failed":("could not be saved", "保存失败", "บันทึกไม่สำเร็จ"),
 "models.f.test":      ("Test", "测试连接", "ทดสอบ"),
 "models.f.testing": ("connecting…",
    "正在连接…",
    "กำลังเชื่อมต่อ…"),
 "models.f.testok":    ("answered, %1 models — pick one below",
                        "有响应，%1 个模型 —— 在下面选一个",
                        "ตอบกลับแล้ว %1 โมเดล — เลือกด้านล่าง"),
 "models.f.key.have": ("a key is stored", "已存有密钥", "มีคีย์เก็บไว้แล้ว"),
 "models.f.key.fromenv": ("using the key from %1 in the environment, which wins over one saved here",
    "正在用环境变量 %1 里的密钥，它优先于这里保存的",
    "กำลังใช้คีย์จาก %1 ในสภาพแวดล้อม ซึ่งมาก่อนคีย์ที่บันทึกที่นี่"),
 "models.f.key.fromfile": ("stored in secrets.toml", "已存在 secrets.toml 里",
                           "เก็บไว้ใน secrets.toml"),
 "models.f.testfail": ("it did not answer", "它没有回应", "ไม่มีการตอบกลับ"),
 "models.speechapi": ("remote service",
    "远程服务",
    "บริการระยะไกล"),
 # Each language names the card as that language labels it. The Chinese
 # cell's "远程 API" had been pasted into the English and Thai cells, so both
 # pointed at a control neither of them shows.
 "models.speechapi.sub": ("Where the audio goes: its address, model and key.",
    "声音会发到这里：填好地址、模型和密钥。",
    "เสียงจะถูกส่งไปที่นี่: ที่อยู่ โมเดล และคีย์"),
 "models.speechapi.cat": ("These are the on-device engine's models; with the remote API selected they are not used.",
    "下面是本机引擎用的模型；现在用的是远程 API，暂时用不到。",
    "นี่คือโมเดลของเครื่องในเครื่อง ตอนนี้ใช้ API ระยะไกลอยู่จึงยังไม่ได้ใช้"),
 "models.k.agent":     ("System agent", "系统 agent", "เอเจนต์ของระบบ"),
 # "already logged in, no key" implied a cloud without saying the text
 # reaches it. The process is local; the inference is not, which is what
 # state() has always reported and this line did not.
 "models.k.agent.sub": ("The coding agent Omarchy is set to use. Already signed in, no key needed; a few seconds each time. Your words go to that agent's service.",
    "Omarchy 设定的那个 coding agent。已经登录，不用密钥；每次要几秒钟。你的话会发到它登录的服务上。",
    "coding agent ที่ Omarchy ตั้งไว้ ล็อกอินแล้ว ไม่ต้องใช้คีย์ ใช้เวลาไม่กี่วินาทีต่อครั้ง ข้อความของคุณจะไปที่บริการของ agent นั้น"),
 # An agent whose non-interactive mode has nowhere but argv to take a
 # prompt gets the transcript on a command line. Said here because this
 # program reads API keys from stdin for exactly that reason.
 "models.k.agent.argv": ("(Its command line carries your words, which other programs on this machine can see.)",
    "（它的命令行会带上你说的话，本机其他程序看得到。）",
    "(บรรทัดคำสั่งของมันมีคำพูดของคุณ โปรแกรมอื่นในเครื่องมองเห็นได้)"),
 "models.k.local":     ("Local model", "本地模型", "โมเดลในเครื่อง"),
 "models.k.local.sub": ("Runs a model from the list below on this machine. Nothing leaves it.",
    "在本机运行下面列表里的模型，文字不会离开本机。",
    "รันโมเดลจากรายการด้านล่างในเครื่องนี้ ไม่มีอะไรออกจากเครื่อง"),
 "models.k.api":       ("Remote API", "远程 API", "API ระยะไกล"),
 # It was "the only one that sends your words off the machine", which the
 # agent route also does — it runs a CLI that is logged into someone's
 # cloud. Two of these three send the text out; one of them said so.
 "models.k.api.sub": ("An online model you point it at, with its address and a key. Your words go there.",
    "你指定的在线模型，需要填地址和密钥。你的话会发到那里。",
    "โมเดลออนไลน์ที่คุณกำหนด ต้องใส่ที่อยู่และคีย์ ข้อความของคุณจะถูกส่งไปที่นั่น"),
 "models.k.unset":     ("not configured", "未配置", "ยังไม่ได้ตั้งค่า"),
 "models.stale": ("The background service is still running the model it started with",
    "后台服务还在用启动时加载的模型",
    "บริการเบื้องหลังยังใช้โมเดลที่โหลดตอนเริ่ม"),
 "models.loaded":    ("loaded ", "已加载 ", "โหลดแล้ว "),
 "models.configured":("configured ", "已配置 ", "ตั้งค่าไว้ "),
 "models.restart": ("Restart the background service",
    "重启后台服务",
    "เริ่มบริการเบื้องหลังใหม่"),
 "models.ondisk":    ("already on disk", "已在磁盘上", "มีอยู่ในดิสก์แล้ว"),
 "models.downloading":("downloading…", "下载中…", "กำลังดาวน์โหลด…"),
 "models.download":  ("Download", "下载", "ดาวน์โหลด"),
 "models.use":       ("Use", "使用", "ใช้"),
 "models.remove":    ("Remove", "删除", "ลบ"),
 "models.ourstore":  ("our store", "我们的模型目录", "คลังของเรา"),
 "models.outside": ("Models found outside %1 are used where they are and never deleted.",
    "在 %1 以外找到的模型会直接在原处使用，不会被删除。",
    "โมเดลที่พบนอก %1 จะถูกใช้ตรงที่มันอยู่ และไม่ถูกลบ"),
 "models.llm": ("AI REWRITE",
    "AI 改写",
    "AI เขียนใหม่"),
 "models.llmsub": ("What a mode's AI rewrite step can use. All three can be ready at once.",
    "模式里「AI 改写」步骤可以用的方式，三种可以同时准备好。",
    "สิ่งที่ขั้น AI เขียนใหม่ของโหมดใช้ได้ เตรียมไว้ทั้งสามแบบพร้อมกันได้"),
 "models.nokey":     ("no key", "缺密钥", "ไม่มีคีย์"),
 # For the other reasons an entry cannot run — weights never downloaded, most
 # often. "no key" stood for all of them, on a local llama.cpp that wants none.
 "models.notready":  ("not ready", "未就绪", "ยังไม่พร้อม"),
 "models.endpointnote": ("A key is never written to the config: it is kept in secrets.toml, or given by an environment variable.",
    "密钥不会写进配置文件：它存在 secrets.toml 里，也可以用环境变量提供。",
    "คีย์ไม่ถูกเขียนลงไฟล์ตั้งค่า แต่เก็บใน secrets.toml หรือให้ผ่านตัวแปรสภาพแวดล้อม"),
 "models.seg.speech": ("speech model", "语音模型", "โมเดลเสียงพูด"),
 "models.seg.other":  ("other programs", "其他程序", "โปรแกรมอื่น"),
 "models.vramnote": ("Both models stay loaded so dictation is instant. If memory runs out, the voice model is pushed out first and dictation slows down a lot.",
    "两个模型都常驻内存，听写才能即时完成。显存不够时，语音模型会先被挤出去，听写会慢很多。",
    "ทั้งสองโมเดลค้างในหน่วยความจำ การพูดพิมพ์จึงเร็วทันที ถ้าหน่วยความจำไม่พอ โมเดลเสียงจะถูกดันออกก่อนและช้าลงมาก"),
 "models.vram":      ("VRAM · ", "显存 · ", "VRAM · "),
 "models.sharednote": ("This graphics chip shares the computer's memory, so the bar is the whole machine. If it fills up, the system starts swapping and everything slows down.",
    "这块显卡和电脑共用内存，所以上面那条是整台电脑的内存。一旦用满，系统会开始用交换空间，整台电脑都会变慢。",
    "ชิปกราฟิกนี้ใช้หน่วยความจำร่วมกับเครื่อง แถบนี้จึงเป็นของทั้งเครื่อง ถ้าเต็ม ระบบจะเริ่มสลับหน่วยความจำและทุกอย่างช้าลง"),
 "models.shared": ("Shared memory · ", "共享内存 · ", "หน่วยความจำร่วม · "),
 "models.needs":     ("needs", "需要", "ต้องใช้"),
 "models.list.speech": ("voice models",
    "语音模型",
    "โมเดลเสียง"),
 "models.list.speech.sub": ("Bigger ones are more accurate, smaller ones faster. The one marked ● is in use.",
    "越大越准，越小越快。标 ● 的是正在用的。",
    "ยิ่งใหญ่ยิ่งแม่น ยิ่งเล็กยิ่งเร็ว ตัวที่มี ● คือที่ใช้อยู่"),
 "models.list.llm": ("local AI models",
    "本地 AI 模型",
    "โมเดล AI ในเครื่อง"),
 "models.list.llm.sub": ("For the “Local model” way of rewriting. Use makes one the default; a mode's step can still pick its own.",
    "给「本地模型」这种改写方式用。「使用」设为默认；模式里的步骤也可以单独选。",
    "สำหรับการเขียนใหม่แบบ “โมเดลในเครื่อง” กด “ใช้” เพื่อตั้งเป็นค่าเริ่มต้น แต่ละขั้นในโหมดยังเลือกเองได้"),
 "models.usedby": ("used by %1",
    "%1 在用",
    "ใช้โดย %1"),
 "models.seg.llm": ("AI model",
    "AI 模型",
    "โมเดล AI"),
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
 "dict.dryrun.running": ("Dry run · running…", "试运行 · 运行中……", "ทดลองรัน · กำลังรัน…"),
 "dict.dryrun.none": ("Nothing would change.", "没有任何内容会被改动。", "จะไม่มีอะไรเปลี่ยน"),
 "dict.enable":    ("Enable matching", "开启匹配", "เปิดการจับคู่"),
 "dict.prompt":    ("prompt: ", "提示词： ", "พรอมป์ต: "),
 "dict.none":      ("(none)", "（无）", "(ไม่มี)"),
 "dict.overbudget":("%1 more did not fit the prompt budget",
                    "另有 %1 个超出提示词预算，未被加入",
                    "อีก %1 รายการไม่พอโควตาพรอมป์ต"),
 "set.ptt":        ("push to talk", "按住说话", "กดค้างเพื่อพูด"),
 "set.toggle": ("press to start, press to stop",
    "按一下开始，再按一下结束",
    "กดเริ่ม กดอีกครั้งเพื่อหยุด"),
 "set.dwell.always":  ("always", "总是", "เสมอ"),
 "set.dwell.changed": ("when changed",
    "有改动时",
    "เมื่อมีการแก้"),
 "set.dwell.never":   ("never", "从不", "ไม่เลย"),
 "set.hotkey":     ("HOTKEY", "快捷键", "ปุ่มลัด"),
 "set.key.type": ("or type one, e.g. F9",
    "或直接输入，例如 F9",
    "หรือพิมพ์ชื่อปุ่ม เช่น F9"),
 "set.key.rebind":  ("Press a key", "按一下新键", "กดปุ่มใหม่"),
 "set.key.press":   ("waiting — press it now, or hold a combination",
                     "等待中 —— 现在按下它，或按住一个组合键",
                     "กำลังรอ — กดเลย หรือกดค้างเป็นชุดปุ่มก็ได้"),
 "set.key":        ("key", "按键", "ปุ่ม"),
 "set.behaviour": ("how to press",
    "按法",
    "วิธีกด"),
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
 "set.hotkeynote": ("The key is recognized by where it sits, so a layout change does not move it, and it keeps doing whatever it did before.",
    "按键按物理位置识别，换键盘布局也不受影响；它原来的功能照常保留。",
    "จดจำปุ่มตามตำแหน่งจริงบนคีย์บอร์ด เปลี่ยนเลย์เอาต์ก็ไม่กระทบ และปุ่มยังทำงานเดิมได้ตามปกติ"),
 "set.preroll": ("start early by",
    "提前开始录",
    "เริ่มอัดล่วงหน้า"),
 "set.prerollwhy": ("Keeps a moment of sound from before the key went down, so your first word is not cut off.",
    "把按下按键前的一小段声音也录进去，免得第一个字被切掉。",
    "เก็บเสียงช่วงสั้นๆ ก่อนกดปุ่มไว้ด้วย คำแรกจะได้ไม่ถูกตัด"),
 "set.tail": ("stop late by",
    "松开后多录",
    "อัดต่อหลังปล่อย"),
 "set.warnbelow": ("quiet warning at",
    "音量过低提醒",
    "เตือนเมื่อเสียงเบากว่า"),
 "set.maxtake": ("longest take",
    "单次最长",
    "นานสุดต่อครั้ง"),
 "set.hud": ("ON SCREEN",
    "屏幕提示条",
    "แถบบนหน้าจอ"),
 "set.hud.show": ("show it",
    "显示",
    "แสดง"),
 "set.hud.size":   ("size", "大小", "ขนาด"),
 "set.size.xs": ("small",
    "小",
    "เล็ก"),
 "set.size.s": ("medium",
    "中",
    "กลาง"),
 "set.size.m": ("large",
    "大",
    "ใหญ่"),
 "set.keepup": ("show what was typed",
    "显示识别结果",
    "แสดงผลลัพธ์"),
 "set.hudnote": ("Usually the result only flashes by. “When changed” keeps it up a little longer when a rule or an AI step changed what you said, or something went wrong. With “never”, what you say is not shown on screen at all.",
    "平时结果只闪一下。「有改动时」会在规则或 AI 改了你的话、或出了问题时多停留一会儿。选「从不」，你说的话就不会显示在屏幕上。",
    "ปกติผลลัพธ์จะแสดงแค่แวบเดียว “เมื่อมีการแก้” จะค้างไว้นานขึ้นเมื่อกฎหรือ AI แก้สิ่งที่คุณพูด หรือมีปัญหา ถ้าเลือก “ไม่เลย” สิ่งที่คุณพูดจะไม่แสดงบนจอ"),
 "set.notifications": ("desktop notifications",
    "系统通知",
    "การแจ้งเตือน"),
 "set.on":         ("on", "开", "เปิด"),
 "set.off":        ("off", "关", "ปิด"),
 "set.history": ("HISTORY AND PRIVACY",
    "历史与隐私",
    "ประวัติและความเป็นส่วนตัว"),
 "set.keepaudio": ("keep recordings",
    "保留录音",
    "เก็บไฟล์เสียง"),
 "set.takes":      (" takes", " 条", " รายการ"),
 "set.historynote": ("Only this many of the newest recordings are kept, for playing a take back; the text of every take stays either way. 0 keeps none.",
    "只保留最近这么多条录音，用来回放；文字记录不受影响。设为 0 就一条录音也不留。",
    "เก็บเฉพาะไฟล์เสียงล่าสุดตามจำนวนนี้ไว้ฟังย้อนหลัง ข้อความทุกครั้งยังอยู่ ตั้งเป็น 0 จะไม่เก็บเลย"),
 # The other end of the right-click delete in the history tab. Everything
 # about this one is worded to say it is not that: the button is the urgent
 # colour, the note says what goes, and it is the only thing in this console
 # that asks before it acts.
 "set.clearhistory":("Clear all history", "清空全部历史", "ล้างประวัติทั้งหมด"),
 "set.clearnote":  ("Every take, and every recording still on disk, at once. There is no "
                    "undo — one at a time is a right-click in the history tab.",
                    "所有记录，以及还留在磁盘上的录音，一次清掉。没有撤销 —— "
                    "要一条一条删，在「历史」页里右键。",
                    "ทุกรายการ และไฟล์เสียงที่ยังอยู่บนดิสก์ ทั้งหมดในครั้งเดียว ย้อนกลับไม่ได้ — "
                    "ถ้าจะลบทีละรายการ ให้คลิกขวาในแท็บประวัติ"),
 "set.clear.confirm":("Delete every take and every recording? This cannot be undone.",
                    "删除全部记录和录音？此操作无法撤销。",
                    "ลบทุกรายการและไฟล์เสียงทั้งหมดหรือไม่? การกระทำนี้ย้อนกลับไม่ได้"),
 "set.clear.cancel":("Cancel", "取消", "ยกเลิก"),
 "set.clear.go":   ("Delete everything", "全部删除", "ลบทั้งหมด"),
 "set.neverleaves":("Audio never leaves this machine", "音频永不离开本机",
                    "เสียงไม่เคยออกจากเครื่องนี้"),
 # The banner above was unconditional, and the console offers a remote
 # speech engine — so selecting it left a green "audio never leaves this
 # machine" over an engine that uploads every take. A privacy claim is the
 # worst thing in the program to be wrong about.
 "set.audioleaves":("Audio is uploaded to %1",
                    "音频会被上传到 %1",
                    "เสียงถูกอัปโหลดไปที่ %1"),
 "set.privacynote.api": ("The speech engine is a remote API, so the audio of every take leaves this machine. Switch back to the local engine in the Models tab to keep it here.",
    "语音识别用的是远程 API，所以每次录音的音频都会离开本机。在「模型」页换回本地引擎，音频就会留在本机。",
    "เครื่องรู้จำเสียงเป็น API ระยะไกล เสียงทุกครั้งจึงออกจากเครื่องนี้ เปลี่ยนกลับเป็นเครื่องในแท็บโมเดลเพื่อเก็บเสียงไว้ในเครื่อง"),
 "set.privacynote": ("Speech is recognized on this machine. Text leaves it only when a mode's AI rewrite uses the remote API or the system agent — the Modes tab shows which modes do.",
    "语音识别在本机完成。只有当某个模式的 AI 改写用了远程 API 或系统 agent 时，识别出的文字才会发出去 ——「模式」页可以看到是哪些模式。",
    "การรู้จำเสียงทำในเครื่องนี้ ข้อความจะออกไปก็ต่อเมื่อ AI เขียนใหม่ของโหมดใช้ API ระยะไกลหรือเอเจนต์ของระบบ — ดูได้ที่แท็บโหมด"),
 "set.editconfig": ("Edit it",
    "打开编辑",
    "เปิดแก้ไข"),
 "set.restart": ("Restart the background service",
    "重启后台服务",
    "เริ่มบริการเบื้องหลังใหม่"),
 "set.configpath": ("Every setting lives in ~/.config/omavoi/config.toml.",
    "所有设置都保存在 ~/.config/omavoi/config.toml。",
    "การตั้งค่าทั้งหมดอยู่ใน ~/.config/omavoi/config.toml"),
 "set.hotkey.sub": ("The key you talk with. What you say lands where your cursor is.",
    "说话用的键。你说的话会出现在光标所在的位置。",
    "ปุ่มสำหรับพูด สิ่งที่พูดจะไปอยู่ตรงเคอร์เซอร์"),
 "set.hud.sub": ("The small strip at the bottom of the screen while you talk.",
    "说话时屏幕底部出现的小提示条。",
    "แถบเล็กๆ ที่ขึ้นด้านล่างจอขณะพูด"),
 "set.notifynote": ("A notification when a take has a warning or heard nothing.",
    "录音出现警告或什么都没听到时，发一条系统通知。",
    "แจ้งเตือนเมื่อการอัดมีคำเตือน หรือไม่ได้ยินอะไรเลย"),
 "set.history.sub": ("The history is kept on this machine, and nowhere else.",
    "录音记录只保存在这台电脑上。",
    "ประวัติเก็บไว้ในเครื่องนี้เท่านั้น"),
 "set.tailwhy": ("Keeps recording a moment after you let go, so your last word is not cut off.",
    "松开按键后再多录一小会儿，免得最后一个字被切掉。",
    "อัดต่ออีกครู่หลังปล่อยปุ่ม คำสุดท้ายจะได้ไม่ถูกตัด"),
 "set.warnwhy": ("A take quieter than this is flagged in History — quiet input is the usual cause of missing words.",
    "录音音量低于这个值时，会在历史里标出来 —— 音量太小是漏字最常见的原因。",
    "ถ้าเสียงเบากว่าค่านี้ จะมีเครื่องหมายในประวัติ — เสียงเบาเป็นสาเหตุหลักที่ทำให้คำหาย"),
 "set.maxwhy": ("Recording stops on its own after this long.",
    "录到这么久会自动停止。",
    "จะหยุดอัดเองเมื่อครบเวลานี้"),
 "set.configfile": ("config file",
    "配置文件",
    "ไฟล์ตั้งค่า"),
})

section("my dictionary", {'word.add': ('Add word', '添加词语', 'เพิ่มคำ'),
 'word.edit': ('Edit word', '编辑词语', 'แก้ไขคำ'),
 'word.intro': ('Add names and specialized words to help Omavoi spell them correctly.',
                '添加人名、公司名或专业词语，帮助 Omavoi 写对它们。',
                'เพิ่มชื่อและคำเฉพาะเพื่อช่วยให้ Omavoi เขียนได้ถูกต้อง'),
 'word.spelling': ('Preferred spelling', '希望怎么写', 'ต้องการให้เขียนอย่างไร'),
 'word.examples': ('e.g. Sarah Chen, Acme, JavaScript',
                   '例如：林晓彤、星河设计、JavaScript',
                   'เช่น สมชาย, Acme, JavaScript'),
 'word.spaces': ('Enter the full name or phrase. Spaces are allowed.',
                 '填写完整名字或词语，也可以包含空格。',
                 'ใส่ชื่อหรือวลีเต็ม ใช้ช่องว่างได้'),
 'word.wrong': ('Keeps getting it wrong?', '经常写错？', 'เขียนผิดบ่อยไหม?'),
 'word.heard': ('What does Omavoi write instead?', '经常写成什么', 'Omavoi เขียนเป็นอะไร'),
 'word.another': ('Add another spelling', '再加一种写法', 'เพิ่มอีกหนึ่งรูปแบบ'),
 'word.removealias': ('Remove', '移除', 'เอาออก'),
 'word.replacehelp': ('These spellings will be changed to “%1”. Only add text you always want '
                      'corrected.',
                      '以后写出这些内容时，会改成「%1」。只填写你希望始终改掉的写法。',
                      'รูปแบบเหล่านี้จะเปลี่ยนเป็น “%1” เพิ่มเฉพาะข้อความที่ต้องการให้แก้เสมอ'),
 'word.more': ('More options', '更多选项', 'ตัวเลือกเพิ่มเติม'),
 'word.hint': ('Help recognize this word', '帮助识别这个词', 'ช่วยจดจำคำนี้'),
 'word.hinthelp': ('Provide this word to your speech service. Cloud services may receive it with your '
                   'audio.',
                   '把这个词提供给语音识别服务；使用云端服务时，它可能随音频一起发送。',
                   'ส่งคำนี้ให้บริการรู้จำเสียง บริการคลาวด์อาจได้รับพร้อมเสียง'),
 'word.case': ('Use this capitalization', '使用这里的大小写', 'ใช้ตัวพิมพ์ใหญ่เล็กตามนี้'),
 'word.sound': ('Correct similar-sounding spellings', '纠正发音相近的写法', 'แก้คำที่ออกเสียงคล้ายกัน'),
 'word.soundhelp': ('This can change words that were already correct. Preview the effect first.',
                    '也可能改动原本正确的词，建议先查看效果。',
                    'อาจเปลี่ยนคำที่ถูกอยู่แล้ว ควรดูผลก่อน'),
 'word.scope': ('Apply in', '应用于', 'ใช้ใน'),
 'word.allmodes': ('All modes', '所有模式', 'ทุกโหมด'),
 'word.previewhelp': ('Try a sentence below. This previews text corrections without recording or '
                      'calling an AI service.',
                      '粘贴一段文字查看纠正效果，不会录音、改写历史或调用 AI 服务。',
                      'วางข้อความเพื่อดูผล โดยไม่บันทึกเสียงหรือเรียกบริการ AI'),
 'word.sample': ('Paste a sentence to try…', '粘贴一段想试试的文字…', 'วางข้อความเพื่อทดลอง…'),
 'word.preview': ('Preview corrections', '查看纠正效果', 'ดูผลการแก้ไข'),
 'word.casewarning': ('This also changes %1. You can turn capitalization off under More options.',
                      '也会进行这个修改：%1。若不是你想要的结果，可在更多选项中关闭大小写统一。',
                      'ตัวเลือกนี้จะเปลี่ยน %1 ด้วย ปิดได้ในตัวเลือกเพิ่มเติม'),
 'word.save': ('Save', '保存', 'บันทึก'),
 'word.cancel': ('Cancel', '取消', 'ยกเลิก'),
 'word.discardhelp': ('Discard your unsaved changes?',
                      '要放弃尚未保存的修改吗？',
                      'ทิ้งการเปลี่ยนแปลงที่ยังไม่บันทึก?'),
 'word.keepediting': ('Keep editing', '继续编辑', 'แก้ไขต่อ'),
 'word.discard': ('Discard changes', '放弃修改', 'ทิ้งการเปลี่ยนแปลง'),
 'word.search': ('Search words or misspellings…', '搜索词语或写错的内容…', 'ค้นหาคำหรือคำที่เขียนผิด…'),
 'word.from': ('Corrects:', '纠正：', 'แก้ไข:'),
 'word.paused': ('Paused', '已暂停', 'หยุดใช้ชั่วคราว'),
 'word.pause': ('Pause word', '暂停使用', 'หยุดใช้คำนี้'),
 'word.resume': ('Use word again', '恢复使用', 'ใช้คำนี้อีกครั้ง'),
 'word.delete': ('Delete word and its corrections', '删除词语及其纠正写法', 'ลบคำและการแก้ไข'),
 'word.undo': ('Undo', '撤销', 'เลิกทำ'),
 'word.empty': ('Add a name or word that Omavoi often gets wrong.',
                '把经常写错的名字或词语加到这里。',
                'เพิ่มชื่อหรือคำที่ Omavoi เขียนผิดบ่อย'),
 'word.noresults': ('No matching words.', '没有找到相关词语。', 'ไม่พบคำที่ตรงกัน'),
 'word.loading': ('Loading your dictionary…', '正在读取词典…', 'กำลังโหลดพจนานุกรม…'),
 'word.saved': ('Saved.', '已保存并生效。', 'บันทึกแล้ว'),
 'word.pending': ('Saved, but not active yet. Retry or start the speech service.',
                  '已保存，暂未生效。请重试或启动语音服务。',
                  'บันทึกแล้ว แต่ยังไม่ทำงาน ลองใหม่หรือเปิดบริการเสียง'),
 'word.retry': ('Retry', '重试', 'ลองใหม่'),
 'word.refresh': ('Reload dictionary, keep draft', '重新读取词典，保留草稿', 'โหลดใหม่และเก็บฉบับร่าง'),
 'word.failed': ('Could not save. Your changes are still here.',
                 '未能保存，你的输入已保留。',
                 'บันทึกไม่ได้ ข้อมูลยังอยู่'),
 'word.readfailed': ('Could not read your dictionary. Please retry.',
                     '暂时无法读取词典，请重试。',
                     'อ่านพจนานุกรมไม่ได้ โปรดลองใหม่'),
 'word.stale': ('The dictionary changed elsewhere. Reload it before saving; your draft is kept.',
                '词典已在其他地方修改。请重新读取后再保存，当前草稿会保留。',
                'พจนานุกรมถูกแก้ไขที่อื่น โหลดใหม่ก่อนบันทึก ฉบับร่างจะยังอยู่'),
 'word.duplicate': ('This word is already in your dictionary. Edit the existing word.',
                    '这个词已经在词典里，请编辑已有词语。',
                    'มีคำนี้แล้ว โปรดแก้ไขคำเดิม'),
 'word.conflict': ('This spelling overlaps another word or correction. Check the details below.',
                   '这个写法与已有词语或纠正冲突，请检查下面的内容。',
                   'รูปแบบนี้ขัดแย้งกับคำหรือการแก้ไขอื่น ดูรายละเอียดด้านล่าง'),
 'word.invalid': ('Enter a name or phrase of 1–200 characters without line breaks.',
                  '请填写 1–200 个字符的名字或词语，不要包含换行。',
                  'ใส่ชื่อหรือวลี 1–200 อักขระโดยไม่ขึ้นบรรทัดใหม่'),
 'word.correct': ('This spelling is already correct; no correction is needed.',
                  '这个写法已经正确，不需要重复添加。',
                  'รูปแบบนี้ถูกแล้ว ไม่ต้องเพิ่มการแก้ไข'),
 'word.invalidmode': ('A selected mode no longer exists. Choose another mode.',
                      '所选模式已不存在，请重新选择。',
                      'โหมดที่เลือกไม่มีแล้ว โปรดเลือกใหม่'),
 'word.missing': ('This word was removed elsewhere. Reload the dictionary.',
                  '这个词已在其他地方删除，请重新读取词典。',
                  'คำนี้ถูกลบที่อื่นแล้ว โปรดโหลดใหม่'),
 'word.capacity': ('Some words could not be used as recognition hints. Their explicit corrections still '
                   'apply:',
                   '部分词语本次未用于帮助识别，已设置的文字纠正仍有效：',
                   'บางคำไม่ถูกใช้เป็นคำแนะนำ แต่การแก้ไขข้อความยังทำงาน:'),
 'word.legacy': ('Your existing dictionary is still available below. A newer speech service or a review '
                 'of the listed settings is needed for the new editor.',
                 '现有词典仍可在下方使用。使用新编辑方式前，需要更新语音服务，或处理列出的旧设置。',
                 'ยังใช้พจนานุกรมเดิมด้านล่างได้ ต้องอัปเดตบริการเสียงหรือตรวจสอบการตั้งค่าเดิมก่อน'),
 'word.use': ('use My dictionary', '使用我的词典', 'ใช้พจนานุกรมของฉัน'),
 'word.partial': ('partly on', '部分启用', 'เปิดใช้บางส่วน')})

section("dictionary feedback", {'word.deleted': ('Word deleted. Its corrections were removed too.',
                  '已删除词语及其纠正写法。',
                  'ลบคำและการแก้ไขแล้ว'),
 'word.restart': ('Restart the speech service to use the new dictionary. Your existing words are '
                  'unchanged.',
                  '请先重启语音服务，再使用新版词典。现有词语尚未修改。',
                  'โปรดเริ่มบริการเสียงใหม่เพื่อใช้พจนานุกรมใหม่ คำเดิมยังไม่เปลี่ยน')})

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
# The routes `omavoi inject --method` actually takes are "", wtype and
# clipboard; xdotool is a --paste-via choice, not a route, and the chip for it
# was a string nothing could ever reach.
DYNAMIC = {f"modes.inject.{v}" for v in ("auto", "clipboard")} | {
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
