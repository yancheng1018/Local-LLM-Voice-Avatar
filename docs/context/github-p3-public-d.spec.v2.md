# github-p3-public-d 规格书 v2 · 干净目录实测 15 分钟快速开始（拷打修订版）

> v1 → v2（/grill-spec 2026-10-08）：6 项用户拍板落档；取证事实修正——测试基线
> 200（非 195）、ASR 首启同步下载 999 MiB 且阻塞监听（v1 的 180s 轮询作废）、
> 前端 DOM 与日志锚点全量补入、12393 实测空闲、github.com 直连不通改走代理。
> 本版为完整规格，弱模型只读这一份施工；v1 原文留存不动。

## 0. 任务与范围

以公开用户视角在干净目录完整走 README「快速开始」（README.md:14-36），验证一次
通过，记录真实耗时对比「约 15 分钟」宣称。**实测型任务：主仓库不修改任何代码；
发现的 README/代码偏差只记录+给建议**，待用户裁决后另行修复。

### 0.1 已裁决口径（用户拍板，不再重问）

| # | 口径 | 拍板 |
|---|------|------|
| 1 | Ollama 模型：忠实 `ollama pull qwen2.5:latest`（~4.7GB 计入总时长），**pull 直连不走代理**（在无代理变量的 shell 执行） | 2026-10-08 |
| 2 | github.com 直连不通 → **克隆/ASR 下载/npm 等依赖步走用户代理 `http://127.0.0.1:7890`**（实测 shell export 代理变量实现） | 2026-10-08 |
| 3 | 干净目录**附带跑全量测试**（uv sync --extra test + pytest，不计入 15 分钟计时） | 2026-10-08 |
| 4 | 实测后干净目录**保留至收尾裁决**，不删 | 2026-10-08 |
| 5 | archive.md 未提交的 p3-c 归档行**随本阶段产物一并提交**（S8，用户已确认授权 commit；不 push） | 2026-10-08 |
| 6 | uv/npm 本机缓存使依赖安装偏快 → **如实记录 + report 注明偏差**（不清缓存） | 2026-10-08 |

### 0.2 关键事实（取证落档，执行层据此设计判据；证据详见当期取证报告）

- 测试基线：主仓库 `uv run --extra test python -m pytest -q` = **200 passed in 48.22s**（exitCode 0，2026-10-08 实跑；roadmap 旧记 195 已过时——p3-b 批 +5）。
- **ASR 首启同步下载阻塞监听**：`sherpa_onnx_asr.py:170` 从 github.com/k2-fsa/releases 下载 sherpa-onnx-sense-voice-zh-en-ja-yue-2024-07-17.tar.bz2（**999 MiB**，落盘 `<repo>/models/`，解压后 1.1GB、峰值约 2.1GB）；初始化链 run_server.py:89-95 → service_context.py:288 → 全部完成**先于** uvicorn 监听。因此：curl 200 即全链路初始化完成；下载期间 curl 恒 000 属正常进度态，**就绪判据必须日志驱动**。
- 日志锚点（重定向于 /tmp/clean_test_server.log，注意 uvicorn 行走标准 logging 带 `INFO:` 前缀，其余走 loguru）：
  - 进度序列：`Initializing ASR: sherpa_onnx_asr`（service_context.py:410）→ `🏃‍♂️Downloading`（asr/utils.py:82）→ `Downloaded`（utils.py:102）→ `Extraction completed`（utils.py:109）→ `Server context initialized successfully.`（run_server.py:92）→ `Starting server on`（run_server.py:98）→ `Uvicorn running on http://localhost:12393`（uvicorn 0.34.0，.venv/.../uvicorn/server.py:213）
  - 失败锚点：`Failed to initialize server context`（run_server.py:94，进程退出）、`The SenseVoice model is missing`（sherpa_onnx_asr.py:185）、`Fail to extract file`（utils.py:157）
  - TTS 锚点：成功 `Finished Generating`（pyttsx3_tts.py:36）；**勿把 `🎙️ GPT-SoVITS generation took` 当引擎判据**（tts_manager.py:215 文案硬编码，对 pyttsx3 同样打出）
- 前端 DOM 锚点（源码与现有 dist 均已验证保留；重新构建后哈希文件名变但选择器不变）：
  - 输入框 `#text-input`（index.html:30），发送 = 其上 keydown Enter 或点 `#send-btn`（ui.ts:37-40）；空文本不发（ui.ts:118）
  - AI 气泡 = `#subtitles .sentence:not(.mine)`，最新一条加 `:last-child`（ui.ts:136-164；.current 不作区分依据）；**气泡在「该句音频开始播放」时才追加**（audio.ts:117 门控），等待判据基于气泡出现或状态文本，**不可用固定延时**
  - canvas = `#stage canvas`（全页唯一，l2d.ts:139-146）
  - 状态机 `#status-text`（index.html:16）：`已连接 · <名>`（模型就绪，main.ts:276）→ `思考中…`（main.ts:293）→ `就绪`（chain-end/播放完，main.ts:66/297）
- 端口 12393：2026-10-08 实测空闲（取证脚本「000=被占用」为判断 bug，000=连接拒绝=无监听）；S1 仍复查。
- 本机 conf.yaml ≠ 模板链（asr 禁用+GSV TTS）——**实测在干净目录 cp 模板 conf，模板链 ollama_llm+sherpa_onnx_asr+pyttsx3_tts 成立**（conf.ZH.default.yaml:66/:182/:274），与主仓库无关。
- 环境（2026-10-08）：python 3.14.7（超 3.10-3.12，但 .python-version=3.10 且本机 uv 已装 3.10，uv sync 自动落 3.10 无网络依赖）；node v24.21.0 / npm 11.19.0（无 engines 段）；磁盘 104 GiB 富余；Ollama 11434 在跑（qwen3.5:9b 已有、qwen2.5:latest 无）；代理 127.0.0.1:7890 通 github.com（200），系统 ProxyOverride 已豁免 127.*。

## 1. 文件清单

| 动作 | 路径 | 说明 |
|------|------|------|
| 新建 | `docs/context/github-p3-public-d.report.md` | 实测记录+实施报告（模板见 §2） |
| 新建（环境产物） | `C:/Coding/Application/LLMVA-clean-clone-test/` | 干净克隆目录，实测后**保留**（拍板 #4） |
| 提交 | 主仓库 git commit（S8） | archive.md（p3-c 归档行）+ 本 spec.v2 + report + 状态簿记一并入库（拍板 #5；**不 push**） |
| 修改 | 无 | 主仓库零代码/文档修改；README 缺陷只记录建议，不修 |

## 2. 关键约定（无代码改动，无函数签名）

- 计时口径：总时长 = S2 克隆开始 → S5 首条 AI 气泡出现（用户视角全流程，含 ollama pull 与 ASR 999MB 下载）；S1 检查与 S3.5 附带测试**不计入**。每步前后 `date +%s` 差值。
- report 字段：① 耗时分解表（步骤/起止时刻/耗时秒/结果/口径注记：代理步·直连步·缓存偏差步）；② 环境清单（工具版本/网络与代理/Ollama/磁盘/缓存偏差声明）；③ 问题清单（编号/现象/根因初判/建议处置）；④ 结论（一次通过与否 + 与「约 15 分钟」对比 + 口径适用范围声明）；⑤ 待确认疑点（执行实际情况）。
- 服务日志统一重定向 `/tmp/clean_test_server.log`。

## 3. 实施步骤

### S1 前置检查【工具可完成】

```bash
date; uv --version; node --version
# 代理连通（github 经 7890 可达）
curl -s -m 5 -x http://127.0.0.1:7890 -o /dev/null -w "PROXY_GITHUB=%{http_code}\n" https://github.com
# 端口（预期 000=空闲；被占用 → 见判断规则）
curl -s -m 3 -o NUL -w "PORT=%{http_code}\n" http://127.0.0.1:12393/m/
# Ollama 服务与模型现状
curl -s -m 3 http://localhost:11434/api/tags | head -c 200; echo
# 磁盘（需 ≥18GB：依赖+node_modules+克隆+ollama 4.7GB+ASR 峰值 2.1GB）
python -c "import shutil;print(round(shutil.disk_usage('C:/').free/2**30,1),'GiB')"
```

- 【需要判断】PORT 非 000：被本项目 dev 服务占 → 停掉并记 report；他者占 → 停下问用户。
- PROXY_GITHUB≠200 → 停下汇报（代理不可用，等窗口或问用户）。

### S2 全新克隆【工具可完成】（总计时开始，走代理·拍板 #2）

```bash
date +%s > /tmp/ct_t0
export HTTP_PROXY=http://127.0.0.1:7890 HTTPS_PROXY=http://127.0.0.1:7890 NO_PROXY=localhost,127.0.0.1
cd /c/Coding/Application
git clone -b v1-release https://github.com/yancheng1018/Local-LLM-Voice-Avatar.git LLMVA-clean-clone-test
git -C LLMVA-clean-clone-test log --oneline -1   # 预期 a91e2c8（或更新，记录实际值并继续）
date +%s > /tmp/ct_t2
```

- 必须 `-b v1-release`（远程默认分支 main 停旧）。克隆失败：`rm -rf LLMVA-clean-clone-test` 后重试 ≤3 次；仍败停下汇报。
- NO_PROXY 必须随代理一起 export（否则后续 curl 127.0.0.1:12393 会被代理拦截）。

### S3 安装 + 构建 + 模板 conf【工具可完成】（同 shell，代理变量延续）

```bash
cd /c/Coding/Application/LLMVA-clean-clone-test
uv sync            # .python-version=3.10 → uv 用本机已装 3.10；缓存命中偏快，如实计时并注明
date +%s > /tmp/ct_t3a
cd frontend-minimal && npm install && npm run build && cd ..
date +%s > /tmp/ct_t3b
test -f frontend-minimal/dist/index.html && echo DIST_OK
cp config_templates/conf.ZH.default.yaml conf.yaml
```

- 验证：uv sync 退出 0；DIST_OK；conf.yaml 存在。任一失败 → 记问题清单后停下，**不自行修**。

### S3.5 附带全量测试【工具可完成】（拍板 #3；不计入计时）

```bash
cd /c/Coding/Application/LLMVA-clean-clone-test
uv sync --extra test
uv run --extra test python -m pytest -q 2>&1 | tail -80
```

- 预期：以实跑输出为准，**全部通过（允许克隆语义 skip）**；对照主仓库基线 200 passed（§0.2）。skip 数与主仓库差异如实记录。失败 → 记问题清单（这是 #1 公开克隆修复在真实克隆下的验证），停下汇报。

### S4 Ollama 模型 pull【工具可完成】（**直连口径·拍板 #1**）

```bash
# 新起干净 shell（无 HTTP_PROXY/HTTPS_PROXY），确保 pull 直连：
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy ollama pull qwen2.5:latest
ollama list | grep qwen2.5 && echo PULL_OK
```

- pull 由常驻 Ollama 服务执行（本服务环境无代理），shell 变量双保险排除。
- 失败重试 ≤3；仍败 → 停下汇报（勿自行改回代理口径，需用户裁决）。

### S5 启动 + 全链路验证【工具可完成 + 需要判断】（代理 shell——ASR 999MB 下载走代理）

```bash
cd /c/Coding/Application/LLMVA-clean-clone-test
export HTTP_PROXY=http://127.0.0.1:7890 HTTPS_PROXY=http://127.0.0.1:7890 NO_PROXY=localhost,127.0.0.1
uv run run_server.py --verbose > /tmp/clean_test_server.log 2>&1 &
# 就绪轮询：日志驱动 + curl 终判，窗口 45 分钟（999MB 经代理速度未知）：
for i in $(seq 1 540); do
  grep -q "Uvicorn running on" /tmp/clean_test_server.log && break
  grep -qE "Failed to initialize server context|Traceback" /tmp/clean_test_server.log && break
  sleep 5
done
grep -cE "🏃‍♂️Downloading|Downloaded .* successfully|Extraction completed|Server context initialized successfully|Starting server on|Uvicorn running on" /tmp/clean_test_server.log
curl -s -o NUL -w "M_CODE=%{http_code}\n" http://127.0.0.1:12393/m/
curl -s -o NUL -w "ROOT=%{http_code} REDIR=%{redirect_url}\n" http://127.0.0.1:12393/
```

- 日志判据【需要判断】逐条核对：进度锚点序列齐全（§0.2）；**无** `frontend-minimal/dist 未构建`；无 `Failed to initialize server context` / `Traceback` / `The SenseVoice model is missing`。
- `M_CODE=200`；`ROOT=307` 且 REDIR 含 `/m/`。
- 浏览器自动化（会话内浏览器自动化技能，截图存档；本地地址经系统 ProxyOverride 豁免直连）：
  1. 打开 `http://127.0.0.1:12393/m/`，等待 `#status-text` = `已连接 · `开头（模型就绪；截图确认 mao_pro 渲染、`#stage canvas` 存在）；
  2. `#text-input` 填「你好」→ press Enter（或 click `#send-btn`）；`#status-text` 应现 `思考中…`；
  3. 等待 `#subtitles .sentence:not(.mine):last-child` 出现且文本非空——**气泡受 TTS 播放门控（audio.ts:117），须轮询等待，禁用固定延时**；超时上限 180s（含 pyttsx3 合成与播放启动）；
  4. 气泡出现即 `date +%s > /tmp/ct_t5`（**总计时终点**）；随后等 `#status-text` 回 `就绪`（回合完成）；
  5. 服务日志核对该轮：含 `Finished Generating`（pyttsx3 成功）；收集浏览器 console 全部 error（逐条列出，执行层不得自行豁免，仅记录）。
- 任一判据失败 → 截图+日志片段记入问题清单，停下汇报，不自行修。

### S6 收尾【工具可完成 + 需要判断】

```bash
# 停实测服务：按端口找 PID，确认属 LLMVA-clean-clone-test 的进程树后杀树
netstat -ano | grep -E "12393.*LISTEN"      # 取 PID
# wmic process where processid=<PID> get commandline   # 确认归属后：
# taskkill //PID <PID> //T //F
```

- 汇总耗时分解表：S2 克隆 / S3 uv sync / npm install+build / S4 pull（直连）/ S5 启动就绪（含 ASR 下载，代理）/ 首气泡——各步标注口径（代理步/直连步/缓存偏差步），合计 vs「约 15 分钟」。
- 问题清单逐条整理（README 与现实不符处给建议修正文案，不修改 README）。

### S7 记录落档【工具可完成】

- 全部结果按 §2 字段写入 `docs/context/github-p3-public-d.report.md`（主仓库）；末尾「待确认疑点」节列执行实际情况（pull 实际耗时、代理实测速度、缓存命中情况等）。

### S8 提交【工具可完成】（拍板 #5；用户已确认授权本步 commit，**不 push**）

```bash
cd /c/Coding/Application/Local-LLM-Voice-Avatar
uv run --extra test python -m pytest -q 2>&1 | tail -80   # 提交前回归（预期同基线 200 passed）
git add -A
git status --short   # 核对清单：archive.md + docs/context/github-p3-public-d.spec.v2.md + report + roadmap.md + current-work.md（不应有其他）
git commit -m "docs(context): github-p3-public-d——干净目录实测 15 分钟快速开始：实测 report+簿记收口（含 p3-c 归档补账）"
```

- 提交身份必须是 `yancheng1018 <55277749+yancheng1018@users.noreply.github.com>`（项目硬性契约；提交前 `git config user.name/user.email` 核对，不符先停下问）。
- 【需要判断】commit 信息按实际产物微调（如实反映 report 结论；若实测发现重大问题致阶段转向，停 S8 问用户）。工作树出现清单外文件 → 停下问。

## 4. 测试用例列表

**无新增测试用例**（实测验证型任务，无代码改动；验证判据已内嵌 S3/S5）。干净目录 S3.5 与主仓库 S8 的全量测试均为**原样运行现有套件**（克隆态 skip 语义即 #1 修复的验证本身），不是新用例，处置不挂收尾待办。

## 5. 运行测试

### 运行测试（弱模型原样执行，不要修改）

主仓库回归（S8 提交前）：

```bash
uv run --extra test python -m pytest -q 2>&1 | tail -80
```

- 基线：200 passed in 48.22s（2026-10-08 实跑，拷打会话取证）；本阶段零代码改动，预期同为 200 passed。
- 退出码非 0 → 只汇报：失败用例名、断言差异、最后 20 行 traceback。

干净目录附带测试（S3.5）：

```bash
cd /c/Coding/Application/LLMVA-clean-clone-test && uv sync --extra test && uv run --extra test python -m pytest -q 2>&1 | tail -80
```

- 预期：全部通过（允许克隆语义 skip），skip 计数与主仓库差异如实记录；无既有实跑数可引用，以实跑输出为准。

## 6. 人工验收清单

**无**。全部验证点已自动化（curl 状态码 / 日志锚点匹配 / 浏览器自动化交互、截图与 console 读取）。音色听感属主观项且非本阶段验收判据，不列。

## 7. 执行中升级条款（疑点已全部裁决，无未决）

- 代理 7890 失效 / S2 克隆与 S5 ASR 下载仍不可达 → 停下问用户（等窗口或改口径）。
- S4 pull 直连反复失败（registry.ollama.ai 不可达）→ 停下问用户是否临时改走代理（口径变更须用户拍板）。
- 实测发现 README 命令级错误（如步骤 typo）→ 只记录建议修正文案入 report，不修改 README。
