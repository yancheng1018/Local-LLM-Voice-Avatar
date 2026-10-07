# github-p3-public-d 规格书 · 干净目录实测 15 分钟快速开始

> 来源：roadmap v1.0.1 #4（审查基线 4）。任务：以公开用户视角在干净目录完整走
> README「快速开始」（README.md:14-36），验证一次通过，记录真实耗时对比
> 「约 15 分钟」宣称。**实测型任务：全程只记录与验证，不修改主仓库任何
> 代码/文档**；发现的偏差只记录+给建议，待用户裁决后另行修复。

## 0. 范围与前置结论（规划取证，执行层不必复核）

- 流程基准 = README.md:18-36：clone → `uv sync` → `cd frontend-minimal && npm install && npm run build` → `cp config_templates/conf.ZH.default.yaml conf.yaml` → `ollama pull qwen2.5:latest` → `uv run run_server.py` → 浏览器打开 `http://127.0.0.1:12393` 对话。
- 远程默认分支 main 停旧（遗留 [github-p3-public-c]），克隆必须 `-b v1-release`（含 #1/#2/#3 修复）。
- 模板默认引擎链自洽（规划已核对）：`ollama_llm` + `qwen2.5:latest`（conf.ZH.default.yaml:66、:133；base_url `/v1` 后缀由适配器自动转原生 `/api`，ollama_native_llm.py:38-44）；ASR=`sherpa_onnx_asr`（:182，首启自动下载模型）；TTS=`pyttsx3_tts`（:274，离线）；角色指针空 = 直接用模板内 mao 角色（:15、:35-37）；端口 12393（:11）。
- 根路径 `/` 307 重定向到 `/m/`（server.py:151-156），README 地址写法成立。
- `frontend-minimal/dist/` 与 `conf.yaml` 均不入库（.gitignore:2、:28）→ 构建与复制步骤必要。
- 本机现状（2026-10-08 规划时实测）：Ollama 在跑、已有 qwen3.5:9b / qwen3.5:9b_uncen，**无 qwen2.5:latest**。

## 1. 文件清单

| 动作 | 路径 | 说明 |
|------|------|------|
| 新建 | `docs/context/github-p3-public-d.report.md` | 实测记录+实施报告（写入主仓库，模板见 §5） |
| 新建（环境产物） | `C:/Coding/Application/LLMVA-clean-clone-test/`（干净克隆目录） | 实测工作区，实测后**保留**待用户裁决清理 |
| 修改 | 无 | 主仓库零改动（发现 README 缺陷只记录建议，不修） |

## 2. 关键约定（无代码改动，无函数签名）

- 计时口径：总时长 = S2 克隆开始 → S5 收到首条 LLM 回复（用户视角全流程，含 `ollama pull`）；S1 环境检查与 Ollama 常驻服务不计入（README 前置要求用户已装）。每步前后 `date +%s` 差值记录。
- report 记录字段：① 耗时分解表（步骤/开始时刻/结束时刻/耗时秒/结果）；② 环境清单（各工具版本、网络状况、ollama 模型、磁盘余量）；③ 问题清单（编号/现象/根因初判/建议处置）；④ 结论（一次通过与否 + 与「约 15 分钟」对比）。
- 服务日志统一重定向 `/tmp/clean_test_server.log`，所有日志判据在此文件取。

## 3. 实施步骤

### S1 前置检查【工具可完成】

```bash
date; python --version; uv --version; node --version; npm --version
git ls-remote --heads origin 2>&1 | head -5        # 网络连通；失败重试 ≤3 次，仍败 → 停下汇报
curl -s http://localhost:11434/api/tags | head -3   # Ollama 在跑则出 JSON；未跑：ollama serve > /tmp/ollama_serve.log 2>&1 &
ollama list
netstat -ano | grep -E "12393.*LISTEN" || echo PORT_FREE
df -h /c | tail -1   # 需 ≥15GB（uv 依赖 + node_modules + ollama 模型 4.7GB + ASR 模型 + 余量）
```

- 端口 12393 占用处置【需要判断】：被本项目 dev 服务占用 → 停掉并在 report 注明；其他占用者 → 停下问用户。
- `git ls-remote` 连续 3 次失败 → 停下汇报（roadmap 已记录 github.com 间歇可通，#3 当日 push 成功）。

### S2 全新克隆【工具可完成】（总计时开始）

```bash
date +%s > /tmp/ct_t0
cd /c/Coding/Application
git clone -b v1-release https://github.com/yancheng1018/Local-LLM-Voice-Avatar.git LLMVA-clean-clone-test
date +%s > /tmp/ct_t2
```

- 验证：`git -C LLMVA-clean-clone-test log --oneline -1` 输出 a91e2c8（或更新，若后续有新提交则记录实际值并继续）。
- 克隆失败重试 ≤3 次（先 `rm -rf LLMVA-clean-clone-test` 再重试）；仍败 → 停下汇报。

### S3 安装 + 构建 + 模板 conf【工具可完成】

```bash
cd /c/Coding/Application/LLMVA-clean-clone-test
uv sync
date +%s > /tmp/ct_t3a
cd frontend-minimal && npm install && npm run build && cd ..
date +%s > /tmp/ct_t3b
test -f frontend-minimal/dist/index.html && echo DIST_OK
cp config_templates/conf.ZH.default.yaml conf.yaml
```

- 验证判据：`uv sync` 退出码 0；`DIST_OK` 输出存在；`conf.yaml` 存在。任一失败 → 记录问题清单后停下汇报，**不自行修**。

### S4 Ollama 模型【工具可完成，默认忠实 README】

```bash
ollama pull qwen2.5:latest     # ~4.7GB，下载耗时计入总时长
ollama list | grep qwen2.5 && echo PULL_OK
```

- 【需要判断】若用户已裁决改用本机模型（见 §7 疑点 1）：跳过 pull，改干净目录 `conf.yaml` 中 `agent_config.llm_configs.ollama_llm.model` 为 `'qwen3.5:9b'`，report 中注明偏差。默认走忠实 pull。
- pull 失败重试 ≤3 次；仍败 → 停下汇报（可顺带请示是否切换疑点 1 的备选口径继续）。

### S5 启动 + 全链路验证【工具可完成 + 需要判断】

```bash
cd /c/Coding/Application/LLMVA-clean-clone-test
uv run run_server.py --verbose > /tmp/clean_test_server.log 2>&1 &
# 轮询就绪（≤180s，首次启动含 ASR 模型下载）：
for i in $(seq 1 60); do code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:12393/m/); [ "$code" = "200" ] && break; sleep 3; done; echo "M_CODE=$code"
curl -s -o /dev/null -w "ROOT=%{http_code} REDIR=%{redirect_url}" http://127.0.0.1:12393/
```

- 服务日志判据（`/tmp/clean_test_server.log`，【需要判断】逐条核对）：
  - **不含**「frontend-minimal/dist 未构建」（该 warning 源自 server.py:147）；
  - 含 ASR（sherpa_onnx_asr）初始化/模型下载完成记录；
  - 无 traceback / 未捕获异常。
- 浏览器自动化（用会话内浏览器自动化技能，截图存档）：
  1. 打开 `http://127.0.0.1:12393/m/`，等待 mao_pro 渲染：Live2D canvas 元素存在 + 截图可见模型 + console 无致命错误；
  2. 文本输入「你好」发送，轮询 ≤120s 等待 assistant 回复气泡出现且文本非空（含 LLM 首 token 时间）；
  3. 记录首回复时刻 `date +%s > /tmp/ct_t5`（总计时终点）；
  4. 服务日志含该轮对话处理与 pyttsx3 TTS 合成记录；收集浏览器 console 全部 error。
- 判据只锚可确定项：`M_CODE=200`；`ROOT=307` 且 REDIR 含 `/m/`；回复气泡文本长度 >0；日志行匹配上述关键词。回复内容质量/音色好听与否**不**作判据（主观项不验）。
- 任一判据失败 → 截图+日志片段记入问题清单，停下汇报，不自行修。

### S6 收尾【工具可完成 + 需要判断】

```bash
# 停实测服务（按端口找 PID，只停干净目录启动的那个进程）
netstat -ano | grep -E "12393.*LISTEN"
# taskkill //PID <pid> //F   （确认 PID 属 uv run run_server.py 后执行）
git -C /c/Coding/Application/Local-LLM-Voice-Avatar status --short   # 主仓库确认零意外改动
```

- 汇总耗时分解表（S2 克隆 / S3 uv sync / npm install+build / S4 pull / S5 启动就绪 / 首回复）与「约 15 分钟」宣称对比结论。
- 问题清单逐条整理（README 文字与现实不符处，给建议修正文案，**不修改 README**）。

### S7 记录落档【工具可完成】

- 按 §2 字段把全部结果写入 `docs/context/github-p3-public-d.report.md`（主仓库）。
- report 末尾附「待确认疑点」节：§7 疑点的执行中实际情况（如 pull 实际耗时）。

## 4. 测试用例列表

**无新增测试用例**（实测验证型任务，无代码改动；验证判据已内嵌 S3/S5）。干净目录不走全量测试（roadmap #4 括号范围外，走不走见 §7 疑点 2）。主仓库全量测试仅作回归基线，见 §5。

## 5. 运行测试

### 运行测试（弱模型原样执行，不要修改）

```bash
uv run --extra test python -m pytest -q 2>&1 | tail -80
```

- 命令出处：AGENTS.md 高频命令。上一轮实跑基线：195 项全过（2026-10-07，出处 roadmap.md v1.0.1 #1 结论列）；本阶段预期同为全过（零代码改动）。
- 退出码非 0 时只汇报：失败用例名、断言差异、最后 20 行 traceback。

## 6. 人工验收清单

**无**。全部验证点已自动化（curl 状态码 / 服务日志匹配 / 浏览器自动化交互与截图 / console 读取）。音色听感属主观项且非本阶段验收判据，不列。

## 7. 疑点（待用户裁决；规格内默认值不阻塞执行）

1. **Ollama 模型口径**：忠实 pull `qwen2.5:latest`（~4.7GB、耗时计入，很可能使总时长超 15 分钟——这本身是实测结论点）vs 改用本机已有 `qwen3.5:9b`（README.md:29 允许的合法路径，report 注明偏差）。**默认：忠实 pull**。
2. **干净目录是否附带走全量测试**（可验证 #1 公开克隆修复在真实克隆下的效果；#1 修复时仅 git archive 模拟过）。**默认：不走**（范围外）。
3. **实测后干净目录处置**（GB 级占用）。**默认：保留待裁决**。
4. （规划期登记，非执行项）`docs/context/archive.md` 有 4 行未提交的 p3-c 归档行——收尾簿记滞后，待用户裁决是否补提交（规划会话不执行 git commit）。
