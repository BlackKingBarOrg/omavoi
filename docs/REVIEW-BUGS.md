# 界面 Review — 确定的 bug

2026-09-19 · 范围：五个 tab、first-run、setup 清单、HUD、bar 模块、八个语言包（289 条 × 8）
标注 **[实测]** 的是实际跑过命令或用最小用例验证过的，其余是读代码 + 看 `docs/img/` 渲染截图得出的。

这份里的每一条，我认为"是错的"没有讨论余地。
需要拍板的设计/体验问题在 [REVIEW-UX.md](REVIEW-UX.md)。

## 状态

**22 条已修，1 条部分，1 条未做。** 合并于 `8fab56b`（分支 `fix/review-bugs`，
单个提交 `1373539`）。每条下方记了实际怎么改的。

| | |
|---|---|
| 已修 | BUG-01 … 13、15 … 23 |
| 部分 | BUG-14（清单正文在 daemon 侧，跨仓库） |
| 未做 | BUG-24（重拍截图要占用真实桌面） |

正文里的 `文件:行号` 指的是**修改前**的位置——留作记录，现在的行号已经移位了。

### 合并后跑过的检查

| | |
|---|---|
| `tools/qmlcheck.py` | 21 个文件全过 |
| `tools/strings/generate.py` | 307 key × 8 语言，一致性检查零告警 |
| qmllint（软链出 `qs/` 树，接上真实 import） | 全树对比基线只多 1 条，是 `QProcess::ExitStatus` 那个 Quickshell 类型怪癖，基线里 6 个文件已有 12 处 |
| `Strings.qml` 运行时断言 | 168 条：19 个新 key × 8 语言可解析、无 tab 同名、非中日包无汉字、`tf` 替换正常、`xdotool` 已消失 |
| reuse 推导 | 8 个用例，含「认不出就不提供」和 `q5_0` 下划线 |

**没验证的**：插件没有在真实 shell 里加载过。剩余风险集中在两处纯视觉改动——
`ConfigCard` 的 note 折行、词典页新增的 dry run 面板——两者都沿用了页面里已有的布局写法。

---

## P0 — 按钮骗人

### BUG-01 · "Dry run" 按钮什么都不会发生 **[实测]**

`DictionaryView.qml:142`

```qml
Button { text: root.t("dict.dryrun"); onClicked: root.command("omavoi names dryrun") }
```

`root.command` → `Console.qml` 的 `apply()` → `applier` 这个 Process 只接了 stderr，stdout 直接丢掉。

实跑 `omavoi names dryrun` 的输出：

```
1 of 118 stored takes would change

  …（逐条列出改前/改后全文）…
    Omarchi -> Omarchy

Look these over. `omavoi names enable` turns matching on for all of them.
```

整份报告被丢弃，界面上没有任何变化。

**为什么是 P0**：同一页的 `dict.namesblurb` 写着"匹配默认关闭，直到你看过一次试运行 —— 这是这里唯一可能把原本正确的文字改坏的功能"。页面自己规定的安全闸门，在界面上无法通过；而旁边的 "Enable matching" 是能一键打开的。用户只能要么盲开，要么去开终端。

**修法**：给这个调用单独一个带 `StdioCollector` 的 Process，把结果渲染到页面上（`dryrun --json` 如果 daemon 支持的话更好）。

**已修** · `DictionaryView.qml` 自带一个带 `StdioCollector` 的 `dryRunner`，报告渲染在页面上的可关闭面板里；运行中显示 `dict.dryrun.running`，无改动时显示 `dict.dryrun.none`。

---

### BUG-02 · "Edit config" 按钮什么都不会发生 **[实测]**

`SettingsView.qml:575`

```qml
Button { text: root.t("set.editconfig"); onClicked: root.command("omavoi config path") }
```

`omavoi config path` 只往 stdout 打印 `/home/tt/.config/omavoi/config.toml` 一行，被丢弃。按钮写着"编辑配置"，点了毫无反应。

CLI 里本来就有 `omavoi config edit`（`omavoi config -h` 的子命令列表：`{init,show,get,set,edit,path}`）。

**修法**：改成 `omavoi config edit`。

**已修** · 改成 `omavoi config edit`。

---

### BUG-03 · 更新完成后按钮写 "Check again"，点下去是重跑整套更新

`UpdateView.qml:218-224`

```qml
text: plan.done ? root.t("up.again")        // "Check again"
      : plan.failure !== "" ? root.t("first.retry")
      : root.t("up.run")
onClicked: { plan.reset(); plan.begin() }   // 四步全跑一遍
```

`plan.begin()` 跑的是：`omarchy plugin update` → `uv tool install --reinstall` → `install.sh` → `systemctl restart omavoid`。标签说的是"再查一次"。

**修法**：`up.again` 分支改成只调 `root.refresh()`（重新探测 behind/dirty），或者把标签改成"再更新一次"。

**已修** · `plan.done` 时按钮只做 `plan.reset() + root.refresh()`；runner 回到 idle 形态，Update 按钮随之回来，想再更新一次仍是一次点击。

---

## P1 — 文案本身是错的

### BUG-04 · 英文和泰文界面里印着中文"远程 API"

`Strings.qml:256` · 源头 `tools/strings/generate.py:455-457`

```python
"models.speechapi.sub": ("Audio leaves this machine. Selected above under 远程 API.",
                         "音频会离开本机。在上面的「远程 API」里选中它才会生效。",
                         "เสียงจะออกจากเครื่องนี้ เลือก \"远程 API\" ด้านบนเพื่อใช้งาน"),
```

中文那栏的标签被粘进了 en 和 th 两栏。`docs/img/console-models.webp` 里能直接看到这行。

同一条还有第二个问题：它要指向上面那张引擎卡片的名字，但各语言对不上——

| | 这条里写的 | 卡片实际标签 (`models.e.api`) |
|---|---|---|
| en | `远程 API` | `Remote API` |
| th | `远程 API` | `API ระยะไกล` |
| de | `„Entfernte API\"` | `Remote-API` |
| fr / es / ja / vi / zh | ✓ 一致 | |

德语那条还混用了 `„…\"`（德式开引号 + 直引号）。

**修法**：改 `generate.py` 的表，重新生成 `Strings.qml`。顺手把 de 的引号和名字对齐。

**已修** · 改 `generate.py` 的规范表后重新生成。en 用 `Remote API`，th 用 `API ระยะไกล`；de 改成卡片实际用的 `Remote-API`，引号也从 `„…\"` 改成 `„…“`。

---

### BUG-05 · `%1` 没被替换，直接显示在屏幕上

`EndpointFields.qml:99-101`

```qml
fields.checkNote = r.ok === true
  ? fields.t("models.f.testok") + (r.models ? "  " + r.models.length : "")
```

`models.f.testok` = `"answered, %1 models — pick one below"`，这里用的是 `t()` 不是 `tf()`，占位符原样留着，数字再拼在后面。测试端点成功后屏幕上是：

```
answered, %1 models — pick one below  57
```

八种语言都一样（zh：`有响应,%1 个模型 —— 在下面选一个  57`）。

**修法**：`fields.tf("models.f.testok", (r.models || []).length)`。

**已修** · `t()` → `tf("models.f.testok", (r.models || []).length)`。

---

### BUG-06 · 本地模型的问题被标成 "no key"

`ModelsView.qml:505-509`

```qml
status: !l ? root.t("models.k.unset")
        : l.live_problem ? root.t("models.nokey")     // ← 任何问题都显示"没有密钥"
        : l.live_running === true ? root.t("models.running")
        : (l.remote ? root.t("models.ready") : root.t("models.coldshort"))
```

`docs/img/console-models.webp` 里：`Local model  gemma-3-4b  …  no key`，而同一页下方的红字是 `local: llm:gemma-3-4b is not downloaded. Run: omavoi model pull llm:gemma-3-4b`。

本地 llama.cpp 根本不需要 key。用户照着这个标签会去找地方填密钥。

**修法**：`live_problem` 时显示一个中性的"有问题"，或者直接显示 `live_problem` 的首句。

**已修** · 新增 `models.notready`。`live_problem` 只在 `remote === true && has_key !== true` 时才说 "no key"，其余显示"未就绪"——具体原因下面那行红字本来就有。

---

### BUG-07 · 同一屏上两句话互相矛盾

`ModelsView.qml:447` 与 `:507`

LLM 栏顶部：`RUNNING NOW  none loaded — each starts on its first use`
正下方卡片：`System agent  claude  …  ▶ running`

两处用了两个不同判据：

```qml
// :52  顶部那行
llmResident = (engines.llm||[]).filter(l => l.live === true && (l.pid||0) > 0)
// :507 卡片
running: !!(l && l.live_running === true)
```

一个 agent 是外部进程，没有我们能记的 pid，所以永远进不了 `llmResident`，但 `live_running` 是 true。

**修法**：统一成一个判据，或者让顶部那行的空态文案不否定卡片（例如"没有由本机启动的服务"）。

**已修** · `llmResident` 去掉 pid 条件，只看 `live`；pid 和 url 仅在有值时才印。顶栏和卡片从此是同一个判据。

---

### BUG-08 · 历史详情里警告显示两遍

`HistoryView.qml:252-271` 和 `:395-403`

同一个 `view.take.warnings` 数组渲染了两次：一次在 "WHAT WENT WRONG" 标题下（前缀 `· `），一次在页面底部（前缀 `! `）。两块都是橙色，中间隔着 LLM steps / raw text / post-processing / segment confidence。

**修法**：删掉 `:395-403` 那一块（后者没有标题，明显是前者提出来之前的遗留）。

**已修** · 删掉底部那份无标题的重复 Repeater。

---

### BUG-09 · 首屏说"两个问题"，实际问三个

`generate.py` 的 `first.blurb`，八个语言包全部：

> Two questions, then one button.（两个问题,然后一个按钮。）

而 `FirstRun.qml` 上是 `1 语言` / `2 模型` / `3 快捷键` / `4 WHAT WILL RUN`。`FirstRun.qml:10` 的文件注释也还是"Two questions, then one button."——快捷键那一步是后加的，文案和注释都没跟上。

**修法**：八种语言改成"三个问题"。

**已修** · 八个语言包 + README 都改成三个问题。

---

### BUG-10 · 泰语和越南语里有两个同名 tab

| | `nav.settings` | `nav.setup` |
|---|---|---|
| th | `ตั้งค่า` | `ตั้งค่า` |
| vi | `Cài đặt` | `Cài đặt` |

`Console.qml:110-124`：setup tab 在 `done < total` 时会挂到标签栏最后。也就是安装没完成的那段时间里，泰语/越南语用户的标签栏上会并排出现两个一模一样的词。

**修法**：th 的 setup 改成"การติดตั้ง"一类，vi 改成"Thiết lập"一类。

**已修** · th `การติดตั้ง`，vi `Thiết lập`。八种语言下 `nav.setup` 与 `nav.settings` 均已不同。

---

### BUG-11 · 窗口匹配已关，但文案还是窗口口径

`ModesView.qml:100`

```qml
readonly property bool showWindowMatch: false
```

整个窗口匹配 UI 被藏了，现在点一个模式是**全局**切换（`omavoi mode use <name>`）。但这两条文案没跟着改：

- `modes.here` = `here` / `当前` / `ที่นี่` —— 列表里那个角标
- `modes.activehere` = `active in this window` / `在当前窗口生效`

`docs/img/console-modes.webp` 和 `console-modes-zh.webp` 上都能看到。用户会以为这是个按窗口生效的设置。

**修法**：改成"当前"/"in use"这种全局口径的说法。

**已修** · 八语言改成全局口径：`modes.here` → `in use` / `使用中`，`modes.activehere` → `the mode in use` / `当前使用的模式`。

---

### BUG-12 · HUD 对所有拒绝原因都写 "no speech"

`Hud.qml:256-262`

```qml
text: root.phase === "done" ? root.doneText
                            : strings.t("hud.nospeech")   // 固定"没听到说话"
```

后面紧跟一个 `root.rejectedWhy`（`:272-280`），那是 daemon 给的原始英文原因、未翻译。所以拒绝原因只要不是"没听到声音"，第一行就是错的，第二行是英文。

**修法**：`rejectedWhy` 有值时用它，没有才回落到 `hud.nospeech`；rejection 原因在 daemon 侧做成可翻译的 key。

**已修** · 有 `rejectedWhy` 就显示它，没有才回落到 `hud.nospeech`；原先另起一行重复显示的那个元素一并删掉。（原因文本仍是 daemon 给的英文，要本地化得 daemon 侧出 key。）

---

## P1 — i18n 漏洞（"八种语言"是卖点）

### BUG-13 · Bar 模块整个没翻译

`BarWidget.qml:113-141` —— 七条硬编码英文：

```
"󰍬  Setup"
"Recording · release the key to transcribe"
"Omavoi — not set up yet. Click to start."
"Omavoi — setup unfinished"
"Omavoi — not installed yet. Click to set it up."
"Transcribing…"
"Omavoi — ready"
```

这个文件里**没有 `Strings` 实例**（全项目只有 `Console.qml` 和 `Hud.qml` 各一份）。而 `Strings.qml:12` 的注释写着：

> Instantiated per root component (console, HUD, **bar module**)

注释说的第三个从来没存在过。中文用户的 bar 上永远是英文。

附带：`BarIconButton` 里的 `missing` 分支（`:139` 的 "not installed yet" 和 `:131` 的 `󰇚` 图标）是死代码——`reading.visible` 已经覆盖了 `missing`，那个按钮在这个状态下不可见。同一状态两套措辞，只是其中一套永远看不到。

**修法**：加一个 `Strings { lang: link.uiLang }`（`IpcLink` 已经在推 `uiLang` 了），七条文案进语言包。

**已修** · `BarWidget.qml` 加了 `Strings { lang: link.uiLang }`，八条文案进语言包（`bar.stopped` + 七条 tooltip）。顺带删掉了 `BarIconButton` 里那个永远不可见的 `missing` 分支。

---

### BUG-14 · Setup 清单的正文只有英文 **[实测]**

`SetupView.qml:76-95` 渲染的 `modelData.title` / `.detail` / `.note` 全部来自 daemon 的 `omavoi setup --json`：

```
- Typing and audio tools            | pw-record, wtype, wl-clipboard, hyprctl, xdotool
- Speech engine (Vulkan)            | /usr/bin/whisper-server, backends: cpu, vulkan
- Model weights (ggml:large-v3-turbo)
- Hotkey (RIGHTALT via evdev)       | the daemon is reading it
- Start at login                    | omavoid.service is enabled
```

first-run 是全中文的（它自带列表，不问 daemon），装完紧接着的这一屏就变成中文外壳套英文内容。断层很硬，而这是新用户看到的第二屏。

另外 `SetupView.qml:85` 的 `text: "optional"` 是硬编码英文，八种语言下都显示英文。

**修法**：`"optional"` 进语言包是这边就能修的。正文需要跨仓库决定——daemon 出 key 由插件翻，或者 daemon 自己按 `ui.language` 出文案。

**部分** · `"optional"` 已进语言包（`setup.optional`）。清单正文来自 daemon 的 `setup --json`，仍是英文——那要先定「daemon 出 key 由插件翻」还是「daemon 自己按 `ui.language` 出文案」，是跨仓库的决定。

---

### BUG-15 · 提示词输入框上三条硬编码英文

`OmTextArea.qml:79 / 83 / 88`

```qml
text: "unsaved"
label: "Revert"
label: "Save  ⌃⏎"
```

这个控件出现在每个 mode 的 decoder hint 和每一条 LLM 提示词上——是用户改动最频繁、盯得最久的控件。改了字之后弹出来的三个提示全是英文。

**修法**：三条进语言包。

**已修** · `edit.unsaved` / `edit.revert` / `edit.save`；`OmTextArea` 新增 `strings` 属性，`ModesView` 在两个调用点传下去。`⌃⏎` 保留不译。

---

### BUG-16 · 中文/日文标点不统一

zh 包 289 条里 12 条用了半角逗号/分号/冒号，其余用全角：

```
first.blurb          两个问题,然后一个按钮。
first.cancelled      密码框被取消了,所以什么都没有安装
first.pacman404      软件包数据库过期了,镜像上已经没有它记录的那些版本。
first.group.needed   你还不在 input 组里,所以任何键都读不到。
hist.fellthrough     已回落,保留了上一步的文本
modes.speechonly1    …对速度比准确率更重要的模式,值得备一个小的。
models.f.testok      有响应,%1 个模型 —— 在下面选一个
models.k.agent.argv  …放进命令行,同一用户下的任何进程都能从 /proc 看到
models.k.local.sub   llama.cpp,由本程序启动和管理;步骤可以…
first.reuse / first.hotkey.other / up.dirty
```

ja 包 3 条（`up.nofetch`、`up.dirty`、`set.key.type`）。

**修法**：改 `generate.py` 的中日文条目，重新生成。

**已修** · zh 12 条、ja 3 条全部改成全角。现在两个包里 CJK 后跟半角标点的条目为 0。

---

## P2 — 小的

### BUG-17 · Remote API 卡片上的隐私提示被切断

`ConfigCard.qml:129-140` 把 note 列固定在 132px：

```qml
Layout.preferredWidth: Style.space(132)
elide: Text.ElideRight
```

`models.e.api.note` = `"audio leaves this machine"`，在 `docs/img/console-models.webp` 上显示为：

```
audio leaves this ma…
```

全页最重要的一句隐私提示断在词中间。（catalogue 表里几乎所有 note 也都被切，那一条归 UX 文档的 UX-04，因为怎么修有选择；这一条我认为不能留。）

**已修** · `ConfigCard` 的 note 列从 elide 改为折行（最多两行），宽度 132 → 150。

---

### BUG-18 · "use what is here" 可能选中一个不在盘上的模型

`Console.qml:229-238` 的探测：

```sh
ls -1 "$HOME"/.local/share/*/models/ggml-large-v3*.bin \
      "$HOME"/.local/share/omavoi/models/ggml/*.bin 2>/dev/null | head -1
```

第二个 glob 匹配 omavoi 自己目录下的**任何** `.bin`，`head -1` 取排序第一个——可能是 `ggml-base.bin`。

`FirstRun.qml:115`：

```qml
var chosen = (root.model === "reuse") ? "ggml:large-v3-turbo" : root.model
```

不管找到的是什么，都跳过下载、直接 `omavoi model use ggml:large-v3-turbo`。如果找到的不是 turbo，装完就指向一个不存在的权重。

界面上也不显示找到的是哪个文件，用户无从判断。

**修法**：探测结果解析出实际的 model key 带进 `chosen`；chip 旁边显示文件名。

**已修** · 探测改成 `head -8`；`FirstRun` 从文件名反推 catalogue key，chip 旁显示实际文件名，认不出任何一个候选时就不提供这个选项。8 个用例的运行时测试全过。

---

### BUG-19 · "1 days old"

`FirstRun.qml:384` + `first.dbstale` = `"Your package database is %1 days old."`

`dbAgeDays` 在 shell 里已经整除过了，`Math.round` 之后正好是 1 的时候显示 `1 days old`。
（阈值本身该不该是 1 天，见 UX-08。）

**已修** · 拆成 `first.dbstale.age`（带 %1）和 `first.dbstale.age1`（无占位符），余下那句不再含计数。（阈值本身没动，见 UX-14。）

---

### BUG-20 · 一个模型都没下载时，提示说"只下载了一套权重"

`ModesView.qml:509`

```qml
visible: root.speechChoices.length <= 1
```

`<= 1` 把 0 也包进去了，`modes.speechonly1` 写的是"Only one set of weights is downloaded"。

**已修** · 0 个时显示新增的 `modes.speechnone`，1 个时才是原来那句。

---

### BUG-21 · daemon 只是停了，bar 上却说"还没装"

`BarWidget.qml:25` + `IpcLink.qml:19`

```qml
readonly property bool missing: link.state === "stopped"
```

`stopped` 的含义是"socket 上没人应答"——`IpcLink` 自己的注释写着"usually the daemon is restarting"。但 bar 在这个状态下显示 `󰍬  Setup`，tooltip 是"Omavoi — not set up yet"。

每次 `systemctl restart omavoid`（Settings 里就有这个按钮）都会让 bar 闪一下"还没装"。

**修法**：`missing` 用 `setupKnown && !setupReady` 判断，socket 断开单独显示"服务已停止"。

**已修** · 新增 `command -v omavoi` 探测，区分「没装」「服务停了」「装到一半」三态；探测答复前两态都不声明，避免启动瞬间闪错标签。

---

### BUG-22 · 模式列表里的链路名没翻译，和详情页对不上

`ModesView.qml:104-109` 的 `chainOf()` 直接拼配置里的 entry 名：

```
speech → agent
speech → local
```

同一个东西在详情页里叫 `System agent` / `Local model`（`llmLabel()`，有翻译）。中文界面下列表仍然是 `speech → agent`（见 `console-modes-zh.webp`）。

**修法**：`chainOf` 改用 `llmLabel(name, false)`。

**已修** · `chainOf` 改用 `llmLabel(name, false)`，并新增 `modes.chainspeech` 作为首段。

---

### BUG-23 · 死字符串 + README 和界面说法冲突

- `modes.inject.xdotool` 八种语言都有，但注入方式只提供 `["auto", "wtype", "clipboard"]`（`ModesView.qml:748`），这条永远取不到。
- README 依赖表：xdotool 的用途是"typing into XWayland windows — WeChat, Feishu, Steam"。
- `modes.injecthint`（界面上）：auto 在 XWayland 和已知 Electron 应用里**改成粘贴**。

两处说法对不上——要么 README 写错了，要么 xdotool 这条路径还在但没暴露。

**已修** · 删掉 `modes.inject.xdotool`（连同 `DYNAMIC` 白名单和五个语言包）。README 依赖表改成「在 XWayland 客户端里发送粘贴按键」——查过 `omavoi inject --help`，`--method` 只有 wtype / clipboard，xdotool 是 `--paste-via` 的选项。

---

### BUG-24 · README 的截图和现在的代码对不上

`docs/img/console-settings.webp` 里 "keep audio for" 的说明底下直接就是隐私框，中间**没有** "Clear all history" 按钮——那是 `SettingsView.qml:485-500` 现在有的东西。

README 是项目门面，截图停在几个版本之前。

**未做** · 截图要重拍，而重拍得把已安装的插件临时指到仓库，会动到正在使用的桌面。本轮改动还让它更旧了（`here` → `in use`、中文 `当前` → `使用中`、bar 模块现在是本地化的）。

---

## 我查过但**不是** bug 的

- `SetupView.qml:47` 的 `card.width` 跨文件引用 `Console.qml` 的 id。qmllint 报 unqualified access，看起来像坏的。我写了最小 QML 用例实测（Qt 6.11.2）：QQmlContext 链会兜住，运行时正常解析。留着是维护隐患（这个组件一旦在别处实例化就会炸），不是现在的 bug。
- 八个语言包的 key 集合完全一致，289 条无缺无多；`%1` 占位符在所有语言里都对得上（除 BUG-05 那条是调用方的问题）。
