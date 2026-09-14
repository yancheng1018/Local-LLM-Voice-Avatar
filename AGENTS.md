# AGENTS.md · Open-LLM-VTuber v1.2.1-zh 项目上下文

## 项目概述

Open-LLM-VTuber v1.2.1-zh：完全离线运行的语音交互 AI 伴侣，支持 Live2D 虚拟形象、实时语音对话与视觉感知，Python（FastAPI + WebSocket）跨平台应用。
硬件：RTX 3070 Ti（8GB VRAM）；LLM：Ollama + qwen3.5:9b（Q4_K_M 量化）；TTS：GPT-SoVITS v4 DPO。

## 关键端口

| 服务 | 端口 |
|------|------|
| Ollama | 11434 |
| GPT-SoVITS | 9880 |
| Open-LLM-VTuber | 12393 |

## 高频命令

```bash
uv sync                              # 安装依赖
uv run run_server.py                 # 启动服务器（--verbose 开详细日志）
ruff check . && ruff format .        # 代码检查 / 格式化
```

GUI 启动器（推荐；自动使用 .venv-gui，环境缺失时会给出创建命令）：

```bash
启动器.bat                                            # 双击用这个；加 debug 参数保留控制台窗口
.\.venv-gui\Scripts\python.exe launcher\OpenLLMVTuber_GUI.py   # 备选：直接运行（依赖 PySide6-Essentials、ruamel.yaml、psutil）
```

## ⚠️ 硬性契约速查

- Ollama 已改用原生 /api/chat 接口，勿回退（详见 docs/context/ollama-backend.md）
- streaming_mode 必须是字符串（详见 docs/context/ollama-backend.md）
- 角色自我认知名来自 persona_prompt，不是 character_name（详见 docs/context/config-system.md）
- 默认角色是指针方案（v2.6 起）（详见 docs/context/config-system.md）
- 动 Live2D 前必读 docs/context/live2d.md 的硬性契约

## 目录速览

```
run_server.py                      入口
conf.yaml / characters/            用户配置 / 角色配置
src/open_llm_vtuber/               后端主体
  server.py                        FastAPI + WebSocket 服务器
  agent/stateless_llm/             LLM 实现（ollama_native_llm.py 已改原生 /api/chat）
  asr/ · tts/ · vad/               语音识别 / 合成 / 活动检测
  config_manager/ · conversations/ 配置管理 / 对话系统
launcher/                          GUI 启动器（PySide6）
live2d-models/                     Live2D 模型
frontend/                          官方前端（Git 子模块）；frontend-minimal/ 自研极简前端
config_templates/                  默认配置模板
legacy/                            上游遗留部件（本项目不用，详见 legacy/README.md）
```

## 按需加载索引

| 任务场景 | 读取文件 |
|----------|----------|
| 改配置/角色/人设/语言 | docs/context/config-system.md |
| 改 Live2D 模型/表情/动作/尺寸 | docs/context/live2d.md |
| 改 GUI 启动器/声音模型/编辑器 | docs/context/gui-launcher.md |
| git/加忽略/搬移文件/分批提交/文档体系维护 | docs/context/repo-maintenance.md |
| 改后端/Ollama/streaming/加引擎 | docs/context/ollama-backend.md |
| 续接工作/排优先级 | docs/context/current-work.md |
| 查历史决策 | docs/context/archive.md |
| 开发极简自研前端 | docs/context/minimal-frontend.md |
| 查 l2d.su 热区/动作链引擎逆向 | docs/context/spec-l2dsu-engine.md |
| 查 Live2D 触摸引擎设计 | docs/context/spec-l2d-touch-engine.md |
| 查 git 仓库重组历程与施工踩坑 | docs/context/spec-git-reorganize.md |

## 用户级工作流绑定

供用户级命令（~/.zcode/commands/）解析本项目上下文用：
- 当前状态入口：docs/context/current-work.md
- 文档目录：docs/context/（temp_spec / impl_report / fix_instruction / research_* 均在此）
- 归档文件：docs/context/archive.md
- 模块知识索引：即上方「按需加载索引」表

## 当前进行中

极简自研前端（frontend-minimal/）阶段一~五已完成并验收通过（2026-09-15；阶段五=一角色多模型 allowlist，含 fix2 跨角色残留修正）。
待办、下一步与细节见 docs/context/current-work.md。
上下文文件已于 2026-09-13 重构，详见 docs/context/archive.md

## 维护规则

- 根文件 ≤ 100 行，超限就压缩或再拆
- 单模块 ≤ 200 行，超限就再拆
- 新增结论先归域：写进对应模块文件；只有「任何任务都可能踩」的红线才升级到根文件
- 索引表与实际文件名严格一致，改名必须同步
- 每完成一个阶段，跑一次行数检查和索引表一致性检查
- 默认不推送到互联网：本仓库为本地定制版，除非明确要求，不执行 git push
