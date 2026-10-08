# spec-demo-gif · README 演示 GIF 录制与转制工序

> 2026-10-09 收尾升格为长期文档（原 github-p3-public-f.spec.v2.md；阶段已验收，README 增补部分已随实施落定，本文档核心价值=§3 录制/转制/降级工序与 §9 拍板口径）。

> roadmap v1.0.1 #6 + Backlog #9（2026-10-08 用户指示并入本阶段，原「public 后补挂」
> 口径作废）；规划 2026-10-08（/plan-feature，强模型规划档）。
> **本文件为 v2 拷打后定稿（/grill-spec 2026-10-08），弱模型只读这一份施工；
> v1 原版保留作历史，不再维护。**
> 吸收遗留两条（已从 current-work.md 移除）：[github-p3-public-d] 快速开始弱网注记、
> [github-p3-public-e] 克隆内测试口径注记。
> 实施纪律：只改 §1 列出的文件；不执行 git add/commit/push（含 GIF 入库的提交，收尾
> 经 /review-spec 由用户确认）；不动 current-work.md / roadmap.md / AGENTS.md。
> 任一插入锚点对不上或工序触发停报条件 → 停下报告，不自行择位、不放宽断言。

## 0. 基线与对账（规划时实测 + 拷打期取证）

- 全量测试基线（2026-10-08 三次实跑）：规划首跑 `200 passed`；并行阶段
  github-p3-public-h（fengyun_4/rangbaer_5 补录+None 守卫，已验收）report 记
  `207 passed`；用户手修 fengyun_4 模型文件后本规格收尾复跑 = **`1 failed, 206 passed`**。
  红面：`test_inuse_models_have_exact_idle_group` 报 `fengyun_4: 无精确 Idle 组（大小写
  变体: ['idle']）`（tests/test_live2d_model_data.py:95）。
  **R-1（前置阻塞，已解除 2026-10-08）**：手修曾把组名带回小写 idle 致上述红面；
  用户裁决授权规划会话顺手修复——重跑 `scripts/fix_live2d_idle_groups.py`
  （repo-maintenance.md:95 口径，h 阶段 S5 同款）输出 `fixed=2`（fengyun_4+
  rangbaer_5，后者同批回退一并修复，no-variant=38 属预期分布），复跑全量
  **`207 passed in 52.57s`** 复绿。R0 复核应 `207 passed` → 全量预期 211；
  R0 实测红面或计数漂移 → 停报。
- README.md 现状 93 行。行数检查口径 = `AGENTS.md docs/context/*.md`
  （repo-maintenance.md:149-154），README.md 与 tests/ 不在口径内——新增行数不受
  ≤100/≤200 约束（机械定案，依据已附）。
- README 断言面盘点：`tests/test_publish_facade.py:14-22` 的 `README_ANCHORS`
  （"Local-LLM-Voice-Avatar" / "pyttsx3" / "Open-LLM-VTuber" / "Live2D" / "v1.2.1" /
  "MIT"）与 `README_FORBIDDEN`（旧身份串）是全库唯一 README 正文锚点。本规格对
  README **只增不删**，锚点全部保持命中；FORBIDDEN 串不引入。
  tests/test_server_frontend_guard.py 的 README 命中仅为 `legacy/README.md` 退役路径
  断言，与正文无关。
- 工具前提（规划时实证）：ffmpeg n9.0.1 在位；`docs/assets/` 为既定资产目录（归档
  清单 docs/assets/README.md），`git check-ignore docs/assets/demo.gif` 无命中
  （exit=1，可入库）。
- 录制目标就绪度（规划时实测）：characters/kazagumo.yaml → live2d_model_name
  'fengyun_4'（用户指定 2026-10-08，登记由 stage h 完成；touch.json 用户手修、
  Idle 组别 R-1 已复修）；fengyun_4/touch.json 在位 6 条规则；角色卡无
  live2d_model_names 键——allowlist 回退全局名单，rangbaer_5（stage h 登记）可
  直接切换（websocket_handler.py:38-40 语义）；角色卡无 emotions 键（无表情映射，
  镜头不追求表情切换）；语言 ja。
- 录制环境就绪度（拷打期取证代理 2026-10-08）：frontend-minimal/dist 已构建
  （index.html 2026-10-08 23:03）；voices/ 三卡在位（激活链=
  conf.yaml:364 `ref_audio_path` → `voices\光辉\ref.wav`，text/prompt_lang 均 ja）；
  `scripts/gpt_sovits/start_gsv_api.py` 在位且曾执行（有 __pycache__）；前端切角色
  命令源级锚 `frontend-minimal/src/main.ts:367`（`ws.send({ type: 'switch-config',
  file })`）；conf.yaml:33 conf_uid 当前为 'mao_pro_001'——切角色步骤必要性得证。
  注：声音卡为光辉（ja）非風雲专属——GIF 无声不暴露音色，仅驱动口型；若日后升格
  有声视频，需另备風雲声音卡（届时另议）。

## 1. 修改文件表

| 文件 | 操作 | 行数预检 |
|------|------|---------|
| README.md | 修改：S1-S5 五处，文本 §2 逐字照抄 | 93 → 约 114（S2 块 19 行 + S5 块 2 行；不在行数检查口径） |
| docs/assets/demo.gif | 新建：二进制演示 GIF（§3 录制转制产出） | ≤10MB 硬门（测试断言） |
| docs/assets/README.md | 修改：章程句扩一句 + 归档清单加一行（§2 S6） | 现约 93 行 +2（docs/assets/ 不在行数检查口径 docs/context/*.md 内） |
| tests/test_publish_facade.py | 修改：末尾追加常量块 + 1 辅助函数 + 4 测试函数（§4 逐字照抄） | 179 → 约 235（tests/ 不在行数检查口径） |
| docs/context/github-p3-public-f.report.md | 新建：实施交接报告（骨架 §6） | 阶段产物，不入索引 |

## 2. README.md / docs/assets 增补内容（逐字照抄，不润色、不增删标点）

### S1 核心特性 bullet 补半句（触摸引擎适配口径，roadmap 2026-10-07 用户拍板）

定位：README.md:10。将整行

```markdown
- **自研极简前端**：轻量 Live2D 舞台，带触摸/手势交互引擎，可自定义模型与互动热区。
```

替换为：

```markdown
- **自研极简前端**：轻量 Live2D 舞台，带触摸/手势交互引擎，可自定义模型与互动热区——Azur Lane 类 touch.json 模型解锁全部触摸特性，mao_pro 等无规则数据模型走启发式兜底。
```

### S2 新节「相对上游的改动总览」（含克隆测试口径注记）

插入位置：「## 基于上游的声明」节的末段（上游文档见 …两行）之后、「## Live2D 素材
授权声明」之前。插入内容（含节前空行，紧贴原文）：

```markdown

## 相对上游的改动总览

自 v1.2.1 切分以来的主要差异浓缩为 10 项（细节见 docs/context/ 各模块文档与提交历史）：

| # | 改动 | 说明 |
|---|------|------|
| 1 | 自研极简前端 | 从零重写的唯一前端（入口 `/m/`）：轻量 Live2D 舞台、WS 协议子集、音频队列、聊天历史与口型同步；上游官方前端整体退役 |
| 2 | Live2D 触摸规则引擎 | Azur Lane 类 `touch.json` 规则驱动交互：热区、动作链、冷却与条件门槛 |
| 3 | 手势+参数驱动引擎 | 拖拽步进链、目光跟随、参数写入与一键复位；无规则数据的模型走启发式兜底 |
| 4 | Live2D 调试栏与热区叠加层 | 前端内置可视化调试：热区/参数/动作实时查看 |
| 5 | Spine 渲染支持 | 极简前端同时支持 Spine 模型（上游 Cubism 专属前端无法加载） |
| 6 | 前端模型切换与 allowlist | 同角色多 Live2D 模型切换，白名单控制可选集 |
| 7 | Ollama 原生接入 | `ollama_native_llm` 走原生 `/api/chat`：显式 `num_gpu` / `num_ctx`、思考模式、模型预热 |
| 8 | GUI 启动器 | PySide6 一键启动全套服务，环境自检与缺失提示 |
| 9 | 声音模型体系 | 声音卡管理、参考音频与 GPT-SoVITS 权重热切换（GUI 内置） |
| 10 | 模型维护脚本链 | Live2D 扫描/标定/修复 4 件 + GPT-SoVITS API 启动适配器（`scripts/`） |

> 运行测试：`uv run --extra test python -m pytest -q`。新克隆内预期约 190 passed + 10 skipped——跳过项为公开克隆守卫按设计生效（关联本机私有数据的用例），非缺用例。
```

触摸引擎按拍板口径占表内 2 行（第 2/3 行）、不独立成节。10 行表内容 2026-10-08
拷打确认维持现稿；测试口径注记写死数字的漂移风险经用户拍板接受（「约」字 hedge，
守卫只防整节被删，不查真伪）。

### S3 快速开始弱网注记（两处，[github-p3-public-d] 遗留吸收）

S3-1 定位：README.md:28（有序列表第 1 项首行）。将整行

```markdown
1. 拉一个 Ollama 模型（配置默认已指向 Ollama）：`ollama pull qwen2.5:latest`。
```

替换为：

```markdown
1. 拉一个 Ollama 模型（配置默认已指向 Ollama）：`ollama pull qwen2.5:latest`（约 4.7GB，弱网耗时较长）。
```

S3-2 定位：README.md:36（`浏览器打开 …` 段落整行）。将整行

```markdown
浏览器打开 `http://127.0.0.1:12393` 即可对话。首次启动会自动下载语音识别模型，之后完全离线运行。
```

替换为：

```markdown
浏览器打开 `http://127.0.0.1:12393` 即可对话。首次启动会自动下载语音识别模型（SenseVoice，约 1GB，源为 GitHub Releases），下载完成前语音对话不可用，之后完全离线运行。弱网环境可先手动获取模型放入 `models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/`（目录或同名压缩包已存在即跳过自动下载；镜像渠道如 hf-mirror.com）。
```

事实依据（规划时读码核实）：默认 ASR = sherpa_onnx_asr/sense_voice
（config_templates/conf.ZH.default.yaml:182,226,246）；本地已有即跳过的两级判据在
`src/open_llm_vtuber/asr/sherpa_onnx_asr.py:162-179`。

### S5 演示 GIF 嵌入（hero 位，roadmap #6「主角位留给 #9」）

定位：README.md:3（一句话定位语整行）之后、「## 核心特性」之前。插入（宽度 480 为
默认值，观感异议在报告提出即可）：

```markdown

<p align="center"><img src="docs/assets/demo.gif" width="480" alt="语音对话与 Live2D 触摸交互演示（无声循环）"></p>
```

（S4=GIF 资产本身，由 §3 工序产出，非文本块。）

### S6 docs/assets/README.md 登记（章程扩充经 2026-10-08 用户追认）

定位：docs/assets/README.md:3（`> 与 docs/context/ 的分工…` 行）之后新增一行：

```markdown
> 2026-10-08 起兼收对外演示媒体（README 引用的自录产物，登记入现行归档清单）。
```

现行归档清单表（该文件 `### 现行归档清单` 表末，即 `su_survey_touch_json.py` 行
之后）追加一行（镜头序列与 §3 R2 一致：待机→对话口型→拖拽→调试栏热区→切换→
复位）：

```markdown
| `demo.gif` | README 首屏演示动图（自录：待机→对话口型→拖拽→调试栏热区点按→切 rangbaer_5→复位，无声循环 ≤10MB；github-p3-public-f） | 直接观看；重录按 docs/context/github-p3-public-f.spec.v2.md §3 |
```

## 3. 演示 GIF 录制与转制工序（roadmap #9，无声 GIF 口径）

拍板口径（2026-10-08 用户）：出镜=角色 kazagumo（fengyun_4，舰船形象公开风险自担）；
形式=无声 GIF 入库；ASR 环节不展示（文字输入），TTS 仅驱动口型；**对话保持日语**
（人设真实，2026-10-08 拷打拍板）；镜头含调试栏/热区叠加层展示与 rangbaer_5 切换。

### R0 基线复核（工具可完成，必须最先做）

```bash
uv run --extra test python -m pytest -q 2>&1 | tail -15
```

应 `207 passed`（R-1 修复后实跑基线，§0）→ 后续全量预期 211；红面或计数漂移 → 停报。

### R1 环境准备（AI 备现场；GSV 启动属「需要判断」）

1. 起 GPT-SoVITS API：按 gui-launcher.md 既有链路（GUI 一键启动或
   `python scripts/gpt_sovits/start_gsv_api.py --root <GSV根目录>`，根目录为用户
   环境既有，规格不预设路径；适配器在位且曾执行，§0 取证）。
2. 起主服务：`uv run run_server.py`（ollama 服务与模型为用户环境常驻）。
3. 切角色到 kazagumo：前端发送 `switch-config` file=kazagumo.yaml（源级锚
   `frontend-minimal/src/main.ts:367`；文档先例 minimal-frontend.md:23-24）；机制
   不可用则按 docs/context/config-system.md 临时改 conf.yaml 指向 kazagumo.yaml 后
   重启服务（conf_uid 当前为 'mao_pro_001'，conf.yaml:33——此步必做）。录制完不
   改回（后续人工验收还要看）。
4. 冒烟判据：/m/ 一轮文字对话成功（流式回复 + TTS 出声 + 口型动）；调试栏与热区
   叠加层初始关闭，按镜头脚本 E 开关（本阶段要求入镜展示，2026-10-08 用户拍板）。

### R2 录制（AI 自动化优先）

录屏（桌面仅留浏览器窗口，素材输出仓库外；时长上限 120s——A-G 预估 55-65s，
留 LLM 长回复与切换余量）：

```bash
ffmpeg -y -f gdigrab -framerate 30 -i desktop -pix_fmt yuv420p -t 120 /tmp/github-p3-public-f_raw.mp4
```

浏览器自动化（会话内 browser-use 技能）在录制窗口内按镜头脚本驱动
（LLM 回复内容生成式不可预设，断言只锚「回复发生+口型动」）：

| 镜头 | 动作 | 预期画面 |
|------|------|---------|
| A 待机 | 打开 `http://127.0.0.1:12393/m/` 静置 4s | 風雲待机呼吸+眨眼 |
| B 提问 | 文字输入 `こんにちは、風雲さん。` 发送 | 消息上屏 |
| C 回答 | 等待回复完成（约 15-25s） | 流式逐字上屏 + TTS 口型同步 |
| D 触摸 | 画布中部按住水平缓拖 ~100px 放开 | 步进链位移+回弹 |
| E 调试栏 | 开调试栏与热区叠加层 → 热区框/参数可见 → 隔 ≥2s 点按热区 1 次（触发 touch.json 动作，6 规则）→ 关调试栏 | 热区高亮框+点按触发动作（动态演示改动总览表 #4 行） |
| F 切换（可选） | 切换皮肤到 rangbaer_5 → 待机 2s → 切回 fengyun_4 | 模型切换动效（rangbaer_5 可直接选中，依据 §0 就绪度；流程顺滑才录） |
| G 复位 | 点一键复位，静置 3s | 回待机 |

规避项：点按不连续推进动作链超过 2 步（TouchBody 链几何退化区，hotzone-arch
遗留①）；调试栏仅镜头 E 开启，开关动作各留 ~1s 便于观感。

### R3 转制 GIF（工具可完成）

先审素材定选段（`ffprobe /tmp/github-p3-public-f_raw.mp4` 取时长；抽帧核对 A-G
起止），再转制：

```bash
ffmpeg -y -ss <A起> -to <G止> -i /tmp/github-p3-public-f_raw.mp4 -vf "fps=12,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" -loop 0 docs/assets/demo.gif
```

体积 >10MB → 依次降 fps=10 / scale=720 / 缩短选段重转，直至 ≤10MB（守卫测试硬门）。

### R4 失败降级（人工录制，仅当 R2 自动化失败）

自动化同一故障 ≥3 次（动效不渲染 / 录屏黑屏 / 交互不可驱动）→ 停报附尝试记录，
转人工（AI 已备好现场：服务与页面就绪 `http://127.0.0.1:12393/m/`；人只做：
①Win+Alt+R 开始录制 ②按镜头 B-E 脚本操作 ③再按 Win+Alt+R 停止；判定=素材含完整
回复+拖拽+调试栏热区点按画面；耗时约 5 分钟）。转制 R3 仍由 AI 完成。

## 4. 测试（沿用 tests/test_publish_facade.py，文件末尾追加）

```python
README_DELTA_HEADING = "## 相对上游的改动总览"
README_DELTA_ROW_ANCHORS = ("触摸规则引擎", "手势+参数驱动")
README_WEAKNET_ANCHORS = (
    "4.7",
    "hf-mirror",
    "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17",
)
README_TESTNOTE_ANCHORS = ("190 passed", "10 skipped", "非缺用例")


def _readme_section(readme: str, heading: str) -> str:
    """截取 README 中指定二级标题到下一个二级标题之间的正文。"""
    start = readme.index(heading)
    body = readme[start + len(heading) :]
    next_h2 = body.find("\n## ")
    return body if next_h2 == -1 else body[:next_h2]


def test_readme_upstream_delta_table():
    """相对上游改动总览：表头+数据共 11 行（10 项），触摸引擎占 2 行（roadmap #6 口径）。"""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert README_DELTA_HEADING in readme, "缺少「相对上游的改动总览」节"
    rows = [
        line
        for line in _readme_section(readme, README_DELTA_HEADING).splitlines()
        if line.startswith("|") and "---" not in line
    ]
    assert len(rows) == 11, f"表头+数据行应共 11 行，实得 {len(rows)}"
    for anchor in README_DELTA_ROW_ANCHORS:
        assert any(anchor in row for row in rows[1:]), f"触摸引擎行缺失锚点: {anchor}"
    assert "解锁全部触摸特性" in readme, "核心特性 bullet 缺少触摸适配口径半句"


def test_readme_quickstart_weaknet_notes():
    """快速开始弱网注记：两处大下载体积与预置跳过渠道（p3-public-d 遗留吸收）。"""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for anchor in README_WEAKNET_ANCHORS:
        assert anchor in readme, f"README 缺少弱网注记锚点: {anchor}"


def test_readme_test_count_note():
    """测试口径注记：公开克隆 skip 面说明，避免误读为缺用例（p3-public-e 遗留吸收）。"""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for anchor in README_TESTNOTE_ANCHORS:
        assert anchor in readme, f"README 缺少测试口径注记锚点: {anchor}"


def test_readme_demo_gif():
    """README 演示 GIF：资产在位、GIF 魔数、体积 ≤10MB、README 引用+归档登记（roadmap #9）。"""
    gif = REPO_ROOT / "docs" / "assets" / "demo.gif"
    assert gif.is_file(), "docs/assets/demo.gif 缺失（演示图未产出）"
    data = gif.read_bytes()
    assert data[:4] == b"GIF8", "demo.gif 魔数不符（非 GIF 格式）"
    assert len(data) <= 10 * 1024 * 1024, f"demo.gif 超 10MB 上限: {len(data)}"
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/assets/demo.gif" in readme, "README 未嵌入演示 GIF"
    listing = (REPO_ROOT / "docs" / "assets" / "README.md").read_text(encoding="utf-8")
    assert "demo.gif" in listing, "docs/assets/README.md 未登记 demo.gif"
```

断言自演（spec-writing §11，编写时对照 §2/§3 逐条核对）：

- 行计数：节内以 `|` 开头且不含 `---` 的行 = 表头 1 + 数据 10 = 11；节尾 blockquote
  与引导句不入计数；S5 的 `<p><img>` 行不以 `|` 开头，不干扰。
- `手势+参数驱动` 锚在数据第 3 行、`触摸规则引擎` 锚在数据第 2 行；`解锁全部触摸特性`
  仅存在于 S1 bullet，不与表内措辞交叉。
- demo.gif 守卫用魔数+体积，无字节/哈希断言（GIF 二进制不受行尾契约影响）。
- 新增 4 个测试函数（无参数化）→ 全量预期 **211 passed**（R-1 解决后基线 207
  实跑 + 4，spec-writing §3；R0 复核以实跑为准并记入报告）。

## 5. 实施步骤（分类，按序执行）

工具可完成（原样执行）：

0. R0 基线复核（§3 R0，必须最先）：R-1 已于规划期解除（§0），应 207 passed；
   见红或漂移即停报。
1. README 文本四处：S1 → S3-1 → S3-2 → S2（逐字照抄）。
2. §3 R1 环境准备中可脚本化部分（起主服务、切角色、冒烟）。
3. §3 R2 录屏命令 + 浏览器自动化镜头脚本 A-G。
4. §3 R3 转制 GIF 至 ≤10MB。
5. S5 README 嵌入 + S6 docs/assets/README.md 登记（GIF 产出后）。
6. §4 测试代码追加（GIF 产出后追加才不悬空）。
7. §7 全量测试 + ruff：
   ```bash
   ruff check . && ruff format --check tests/test_publish_facade.py
   ```
   （全量 `ruff format` 禁跑——仓内存量格式债 3 文件与本阶段无关。）
8. 复核：
   ```bash
   wc -l README.md tests/test_publish_facade.py docs/assets/README.md
   ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 docs/assets/demo.gif
   ```

需要判断：GSV API 启动链路取径（gui-launcher.md）、角色切换机制取舍（switch-config
优先）、镜头 F 取舍（顺滑才录）、R3 选段起止（抽帧核对）、GIF 压缩梯度选择。

停报条件（停下写报告等裁决，不自行绕过）：R0 红/漂移；R2 同一故障 ≥3 次（转 R4
人工须在报告记录后进行）；R3 反复压缩仍 >10MB；任一 §2 锚点对不上。

## 6. 实施报告骨架（docs/context/github-p3-public-f.report.md，新建）

```markdown
# github-p3-public-f.report.md · 实施交接报告

> 实施日期 / 实施档位 / 规格版本：v2

## 1. 改动清单（文件:行 级）
## 2. R0 基线复核结果（实跑输出末 3 行）
## 3. 录制证据（镜头执行日志摘要、自动化/人工取径、失败尝试记录若有）
## 4. GIF 数据（时长/分辨率/体积、压缩梯度若用）
## 5. 测试证据（全量输出末 15 行原样 + ruff 输出）
## 6. 行数账（README / test_publish_facade / docs/assets README 改前后）
## 7. 规格偏差记录（无偏差写「无」）
## 8. 待确认疑点（无则写「无」）
```

## 7. 运行测试（弱模型原样执行，不要修改）

```bash
uv run --extra test python -m pytest -q 2>&1 | tail -80
```

预期：`211 passed`（R-1 解决后基线 207 + 4；以报告 §2 实跑记录为准）。退出码非 0 时
只汇报：失败用例名、断言差异、最后 20 行 traceback；不得改断言、不得改测试文本。

## 8. 人工验收清单（1 项）

GIF 成片观感（主观项）：AI 为何做不了=画面得体性与节奏属主观审美；已备现场=
docs/assets/demo.gif（本地预览）或 GitHub README 渲染页；步骤=①打开 GIF 循环看一轮
（~40s）②确认風雲画面、动效节奏、调试栏/热区帧无异常；判定=画面与节奏认可、舰船
出镜内容无不当；预计耗时 2 分钟。

## 9. 遗留吸收与裁决落档

遗留吸收（两条已从 current-work.md 移除，处置记录）：

- [github-p3-public-d] 弱网注记候选：①ollama qwen2.5 ~4.7GB → S3-1；②ASR 999MB +
  hf-mirror 预置跳过 → S3-2；③「ASR 就绪无专属日志行」排障注记未采纳独立条目——
  核心信息已由 S3-2「下载完成前语音对话不可用」承载，日志行级细节未取证不写。
- [github-p3-public-e] 测试口径注记：→ S2 节尾 blockquote + test_readme_test_count_note。
  数字口径：主仓实跑 200→207（R-1 后），克隆 190+10（p3-public-e 记录）。

规划与用户裁决落档：

- roadmap #9 并入本阶段：2026-10-08 用户指示；原「public 后补挂」作废；GIF 入库的
  commit+push 仍须用户确认（#9 既有口径，本规格不授权）。
- 出镜拍板（2026-10-08 用户）：私有舰船形象公开风险自担；无声 GIF 入库（≤10MB）；
  角色指定 kazagumo（fengyun_4，登记由 stage h 完成、touch.json 用户手修）。
- 追加拍板（同日用户）：R-1 授权规划会话顺手修复（fix_live2d_idle_groups.py
  fixed=2、全量 207 复绿，证据 §0）；镜头 F 切换目标=rangbaer_5；新增调试栏+热区
  叠加层展示镜头 E（改动总览表 #4 行的动态演示位）。
- 拷打拍板（同日 /grill-spec 四项）：①演示对话保持日语（人设真实，README 中文读者
  可接受）；②测试口径注记接受写死数字+漂移风险（守卫只防删节不查真伪）；③docs/assets
  章程句扩充（兼收对外演示媒体）追认；④10 项表内容维持现稿。
- 「改动总览」节位置：放「## 基于上游的声明」之后（先声明 fork 关系再列差异）。
- README 行数不受 ≤100 约束：依据 repo-maintenance.md:149-154 检查清单口径。
- 10 项表内容浓缩自 AGENTS.md 目录速览/索引 + 各分册文档 + 现 README 核心特性；
  表内不提 l2d.su 逆向来源（内部知识，公开 README 不必要）；README 新增文本不含
  私有模型名（alt 文案用通用描述）。

v2 事实偏差修正（拷打期发现，相对 v1）：

1. S6 归档清单行镜头描述过时（v1 缺调试栏/切换镜头）→ 已按 A-G 序列更新。
2. R2 录屏时长上限 -t 90 → 120（A-G 预估 55-65s，留 LLM 长回复与切换余量）。
3. §1 docs/assets/README.md 行数预检措辞「容忍口径内」不准——该文件不在
   docs/context/*.md 检查口径内，非容忍例外。
4. §1 README 行数预估 113 → 约 114（S2 块 19 行逐块累加复核，spec-writing §10）。
5. R1.3 switch-config 先例补源级锚 frontend-minimal/src/main.ts:367（v1 仅有文档
   先例）。
6. §0 补录制环境就绪度证据块（dist 已构建/voices 三卡/GSV 适配器曾执行/conf_uid
   现值），并注声音卡为光辉（ja）非風雲专属——无声 GIF 不暴露，升格有声视频时另议。
