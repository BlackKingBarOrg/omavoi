# 界面 Review — 设计/体验，需要你拍板

2026-09-19 · 和 [REVIEW-BUGS.md](REVIEW-BUGS.md) 配套。行号已对 `8fab56b`
（bug 修复合并之后）重新核过。其中两条被那批修复顺带解决了，标在原位。

这份里的每一条，代码都在按设计跑，是设计本身值不值得改的问题。有些是刻意为之（代码注释里写了理由），我把那些理由也列出来了，方便你判断是当初想清楚了还是当初没想到。

每条给了我的倾向，但这些都该你定。

---

## 一、同一个控件三种语义

### UX-01 · chip 既是单选、又是开关、又是动作按钮

`ModesView.qml` 的 Modes 详情页上，从上往下：

```
2  RULES     [hallucinations] [fillers] [dictionary] [names] [CJK spacing] | [keep end punctuation]
             ↑ 开关，点一下翻转

3  LLM
   ┌───────────────────────────────────────────────────────┐
   │ step 1  [System agent] [Remote API] [Local model]      │  ← 单选：这一步用哪个
   │ …提示词…                                                │
   └───────────────────────────────────────────────────────┘
   + add a step  [System agent] [Remote API] [Local model]     ← 动作：点了就新增一步
```

后两排相距不到 100px、字一模一样、样式一模一样（都是 `OmChip`），语义完全不同。见 `docs/img/console-modes.webp`。

误操作代价不对称：想改第 1 步用哪个 LLM，点错了下面那排，就多出一个步骤（连带一段默认提示词），得再点 Remove 删掉。

**我的倾向**：把 "+ add a step" 那排换成一个下拉或者一个 `+` 按钮开菜单——它是动作，不该长得像状态。

- [ ] 改
- [ ] 不改，理由：

---

### UX-02 · 按钮没有按钮的样子

截图里 `Download`、`Use`、`Remove`、`Press a key`、`Check again`、`Save`、`Test` 全是无边框纯文字，和旁边的说明文字在视觉上分不清。`console-models.webp` 里：

```
ggml:large-v3   2.9G  Twice the do…  all 99, evenly   already on disk   Use
ggml:large-v3-turbo-q5_0  0.5G  The lightest t…  all 99…  Use   Remove
```

`already on disk  Use` 读起来像一句话，不像"状态 + 可点的东西"。

这应该是 `qs.Ui` 的 `Button` 在这个主题下的默认渲染（`OmChip` 反而有边框）。

**我的倾向**：至少给破坏性和下载类动作加边框。这可能要动 omarchy 主题层，不一定归你们管——先确认是不是有意的极简取向。

- [ ] 改
- [ ] 不改（主题决定的，不动）
- [ ] 其他：

---

## 二、信息被切掉 / 排不下

### UX-03 · Models 目录表的说明几乎全被切断

`ModelRow.qml:66-72` 的 note 列是 `fillWidth` + `minimumWidth: 40`，但同一行里语言列占 148、动作列占 180、名字列占 178。左半栏只有 720px，note 实际只剩百来像素。

实际渲染（`console-models.webp`）：

```
ggml:base                0.1G  Proves the pipel…       en in practice
ggml:small               0.5G  Passable in En…         en and the other high-r…
ggml:medium              1.4G  The floor of u…         all 99, unevenly
ggml:large-v3            2.9G  Twice the do…           all 99, evenly
ggml:large-v3-turbo      1.5G  The default: half the … all 99, unevenly — it i…
llm:qwen3-4b             2.3G  The strongest Chin…     strong zh/en
llm:gemma-3-4b           2.3G  Even coverage acro…     broad multilingual
```

这些 note 是用户选模型时**唯一**的依据，现在每一条都断在词中间。`ModelRow.qml:74-81` 的注释还专门写了语言列"其own column rather than appended to the note，因为 note 会 elide 而这半是比较两个模型的人需要的"——说明当初就知道 note 会被切，选择了保语言列。

可选的做法：note 换行不 elide / hover 出 tooltip / 两个家族改成上下堆叠而不是左右分栏 / 点开一行展开详情。

**我的倾向**：note 允许折行。这一列现在等于没有。

> 2026-09-19：引擎卡片上那条（`audio leaves this ma…`）已经在 BUG-17 里修掉了——
> `ConfigCard` 的 note 改成折行两行。这里说的是 `ModelRow` 的目录表，还没动。

- [ ] 改，方式：
- [ ] 不改，理由：

---

### UX-04 · Settings 整页只用了左边 40%

`console-settings.webp`：所有控件贴左，说明文字 `Layout.maximumWidth: Style.space(760)`，右边一半以上是空的。而 Models 是左右两栏铺满。同一个 console 两套布局语言。

在 1440×900 的卡片里，Settings 要滚动才能看完，同时右边空着 600px。

**我的倾向**：分两栏（hotkey/audio 一栏，HUD/history/update 一栏）。

- [ ] 改
- [ ] 不改，理由：

---

### UX-05 · 词典页的 Remove 离它那一行 1000px 远

`DictionaryView.qml:112`：`Item { Layout.fillWidth: r.shadowed_by === "" }` 把 Remove 顶到最右边。`console-dictionary.webp` 里，规则文字在左边 25%，Remove 在最右缘，中间整片空白。

十几条规则的时候，横穿一整屏去点对的那一行，很容易点错。

**我的倾向**：Remove 收到内容右边，或者整页限宽到 900px 居中。

- [ ] 改
- [ ] 不改，理由：

---

## 三、缺的东西

### UX-06 · 历史没有时间

`HistoryView.qml` 列表一行只有：模式名 + 时长 + 文本。详情页 8 个指标（audio / level / decode / RTF / model / language / mode / injected）里也没有时间戳。

README 写"Every take is kept, with the numbers behind it"，但"什么时候说的"是回看列表时最先要的那一列。

同时列表固定只取 40 条（`Console.qml:265` 的 `history -n 40`），没有翻页，而 Settings 里 `keep audio for` 能设到 500。

**我的倾向**：列表加相对时间（"3 分钟前"），详情加绝对时间；40 条那个上限加个"更多"。

- [ ] 改
- [ ] 不改，理由：

---

### UX-07 · "Enable matching" 只能开不能关

`DictionaryView.qml:166-178`（`dict.enable`，:176）只有一个 `omavoi names enable`。界面上没有关回去的入口。

而这个功能自己的说明（`dict.namesblurb`）写着它"是这里唯一可能把原本正确的文字改坏的"。开了之后发现不对，只能开终端。

（每一行的 `matching` / `seed only` 是状态显示，不可点。）

**我的倾向**：改成一个开关。

- [ ] 改
- [ ] 不改，理由：

---

### UX-08 · names 表三列没表头

`DictionaryView.qml:130-160` 渲染 `n.name` / `n.key` / `n.match` 三列并排，没有任何列标题。"key" 是什么、"match" 是什么，完全靠猜。rules 那边至少有 `heard → meant` 的 blurb 兜着。

**我的倾向**：加表头。

- [ ] 改
- [ ] 不改，理由：

---

### UX-09 · AUDIO 那组只有数字，没有参照

`SettingsView.qml:306-320`：`pre-roll 600ms` / `tail 250ms` / `warn below -45 dBFS` / `max take 300s`。

- 没有输入设备选择（用哪个麦克风）
- 没有电平表——用户没法知道 -45 dBFS 对自己这只麦是什么概念，也没法验证麦克风在工作
- `max take` 显示 300 而不是 "5 min"

`set.prerollwhy` 对 pre-roll 有解释，另外三个没有。

**我的倾向**：至少加一个实时电平条（录音时 HUD 有，设置页没有）。设备选择要看 daemon 支不支持。

- [ ] 改，范围：
- [ ] 不改，理由：

---

## 四、危险动作

### UX-10 · 破坏性操作零确认

现在只有"清空历史"有确认框。一键即生效的有：

| 动作 | 位置 | 代价 |
|---|---|---|
| Delete mode | `ModesView.qml:358` | 整个模式，含手写提示词 |
| Remove（LLM 步骤） | `ModesView.qml:649` | 那一步的提示词 |
| Remove（模型权重） | `ModelRow.qml:139` | 最多 6.8 GB，要重下 |
| Remove（词典规则/名称） | `DictionaryView.qml:114 / 157` | 一行 |

`Console.qml:655-659` 的注释解释了为什么不确认：

> Removing a mode, a model or a dictionary rule is one click here and always has been -- each of those can be written again or downloaded again. Every take you have ever dictated cannot.

我觉得这个理由对词典规则成立，对另外三个不太成立：一段调好的 LLM 提示词不是"能重写"的东西，6.8GB 也不是"能重下"的东西（尤其在慢网上）。

**我的倾向**：Delete mode 和 Remove 权重加确认；步骤删除做成可撤销（或者至少提示词非空时才确认）。

- [ ] 改，范围：
- [ ] 不改，理由：

---

## 五、发现不了的东西

### UX-11 · UPDATE 埋在 Settings 最底部

`SettingsView.qml:564-571`，要滚到底才看得见。`console-settings.webp` 里刚好卡在折叠线上——只露出 "UPDATE / Up to date" 两行，按钮在屏幕外。

更新是个低频但重要的动作，而且 README 专门解释了"daemon 的正确升级命令不是显而易见的那个"——正因为如此才更不该藏。

**我的倾向**：有新版本时在标签栏上给个角标；或者升级单独成一个入口。

- [ ] 改
- [ ] 不改，理由：

---

### UX-12 · bar 上右键 = 开始/停止录音，哪都没写 —— **已在 BUG-13 里一并修掉**

`BarWidget.qml:186-193`：

```qml
if (b === Qt.RightButton && root.setupReady) link.send("record")
```

tooltip 只说了左键（"Click to start"）。这是快捷键没配好时唯一的替代入口，但没有任何地方提到。

> 2026-09-19：修 BUG-13（bar 模块没翻译）时顺手做了——`setupReady` 时
> tooltip 末尾追加一行 `bar.tip.rightclick`，八种语言都有。无需再决定。

- [x] 已改

---

### UX-13 · 安装完成没有收尾

`FirstRun.qml:483-487` 的 `first.done`（"Ready — hold your key and talk"）实际上看不到：`onFinished: root.refresh()` → `probeDaemon` 立刻返回 → `daemonPresent = true` → FirstRun 整个 `visible: false`。

装了好几分钟（含 3GB 下载），结束时直接跳进空的 History 页。空态那句 "no takes yet — hold RIGHTCTRL and talk" 算是接住了，但没有一个"成功了"的时刻。

**我的倾向**：`done` 时停在那一屏，给一个"进入控制台"的按钮。

- [ ] 改
- [ ] 不改，理由：

---

## 六、措辞/阈值

### UX-14 · 数据库过期的阈值是 1 天，但话说得很绝对

`FirstRun.qml:94`：`dbStale: root.dbAgeDays >= 1`

`first.dbstale.age` + `first.dbstale`（BUG-19 之后拆成了两句）：

> Your package database is %1 days old. **Installing anything now fails with 404**: the versions it lists are no longer on the mirrors.

代码注释自己写的是"a database older than **a few days**"。任何一台今天没跑过 `pacman -Sy` 的机器都会看到这个橙色告警框 + "Update system packages" 按钮，而 1 天前的库绝大多数情况下装得好好的。

第一屏就吓人一下，而且那个按钮会拉起一个全系统升级的终端。

**我的倾向**：阈值提到 3–5 天，措辞从断言改成"可能"。BUG-19 只修了"1 days old"
的单复数，阈值和这句断言都没动——那是这一条要定的。

- [ ] 改，阈值：
- [ ] 不改，理由：

---

### UX-15 · HUD 尺寸叫 tiny / small / large

`SettingsView.qml:411-413`，值是 `xs` / `s` / `m`，标签是 `tiny` / `small` / `large`（`set.size.xs/s/m`）。

三档里中间那档叫 small、最大的叫 large，看起来像少了一档 medium。实际缩放是 0.78 / 1.0 / 1.25。

**我的倾向**：改成 small / medium / large，或者 tiny / small / big。

- [ ] 改
- [ ] 不改，理由：

---

### UX-16 · 中文界面里 chip 说"自动"，紧接着的说明说 "auto"

`console-modes-zh.webp` 的 INJECT 段：

```
4  注入   [自动] [wtype] [剪贴板]
auto 默认用 wtype，遇到 XWayland 客户端和已知的 Electron 应用则改为粘贴 — …
```

chip 叫"自动"，说明里叫 "auto"。`modes.injecthint` 的中译保留了英文值名。

（`wtype` 保留英文是对的——那是程序名，`Strings.qml` 开头的规则也这么写了。但 `auto` 是个 UI 选项，不是程序名。）

**我的倾向**：说明里改成"自动"。

- [ ] 改
- [ ] 不改，理由：

---

### UX-17 · "Press a key" 等待时把一整句塞进按钮

`SettingsView.qml:204`

```qml
text: root.capturing ? root.t("set.key.press") : root.t("set.key.rebind")
```

`set.key.press` = `"waiting — press it now, or hold a combination"`（中文："等待中 —— 现在按下，或按住一个组合键"）。按钮会被撑到那么宽，同一行后面的三个控件跟着跳位。

**我的倾向**：按钮保持"按一个键"并置灰，那句话放到下面那行状态文字里（那一行已经在做"要么说明为什么不工作、要么说明在哪些设备上工作"）。

- [ ] 改
- [ ] 不改，理由：

---

### UX-18 · RULES 的 chip 中文命名不齐

`console-modes-zh.webp`：`幻觉过滤` / `语气词` / `词典` / `名称` / `中英间距`。

英文那排全是名词（hallucinations / fillers / dictionary / names / CJK spacing），中文里"幻觉过滤"多了个动词。另外 `中英间距` 对应的是 CJK spacing——日文、韩文也在这个规则范围里，"中英"把它说窄了。

**我的倾向**：统一成名词（"幻觉"），CJK 那条改成"CJK 间距"或"中日韩间距"。

- [ ] 改
- [ ] 不改，理由：

---

## 七、这条我拿不准，你判断

### UX-19 · HUD 会把刚说的话显示在屏幕正下方

`Hud.qml:253-271`，`done` 状态下把注入的文本原样显示出来，最宽 420×scale，停留 350ms 或 1400ms。

优点很明显（"看见它打了什么再决定要不要撤"），`set.hudnote` 也解释了为什么默认是 "changed"。

但这是唯一一个把用户口述内容渲染到**全屏 overlay** 上的地方——录屏、投屏、有人站在身后的时候，这段文字是暴露的。目前唯一的关法是 `keep the result up = never`，而那个设置的描述（"a silent correction you never saw is worse"）是从"看不看得见改动"角度写的，没提这一层。

不是 bug，产品取向问题。

**我的倾向**：不改行为，但在 `set.hudnote` 里补一句"这会把你说的话显示在屏幕上"，让 `never` 这个选项的隐私含义能被找到。

- [ ] 改文案
- [ ] 加一个"只显示改动数量不显示文本"的档
- [ ] 不改，理由：

---

## 附：我判断为"刻意为之、看起来没问题"的

列出来只是让你确认我没看漏了什么背景：

- 窗口匹配整个藏起来（`showWindowMatch: false`）——注释说明了理由（没调好之前，一个能配置但不生效的控件比没有更差）。但它留下的文案残留是 BUG-11。
- LLM 目录的 `Use` 写的是全局 local 配置而不是某个模式——注释解释了，模式里可以按步骤覆盖。
- Setup 清单里需要 root 的行给的是 `Copy` 而不是 `Run`，下面再单独一个"一次性装完"的按钮——注释说明了 polkit 每次调用都会弹密码。不过 `Copy` 点下去没有任何反馈（剪贴板静默写入），这个可以顺手加个"已复制"。
- 首屏一次 `pkexec` 打包所有包 + `usermod`——同上，合理。
- `omavoi` 命令全部走子进程而不是走 socket——`IpcLink` 注释解释了（daemon 应答后会关连接）。
