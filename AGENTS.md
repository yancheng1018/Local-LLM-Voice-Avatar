# AGENTS.md · Local-LLM-Voice-Avatar 项目上下文

## 项目概述

Local-LLM-Voice-Avatar（基于 Open-LLM-VTuber v1.2.1 二次开发，v1.0.0 起独立演进）：完全离线运行的语音交互 AI 伴侣，支持 Live2D 虚拟形象、实时语音对话与视觉感知，Python（FastAPI + WebSocket）跨平台应用。
关键端口：主服务 12393（前端 /m/）；外部引擎端口以各模块文档与配置模板为准，新引擎端口不进本文件。

## 高频命令

```bash
uv sync                              # 安装依赖
uv run run_server.py                 # 启动服务器（--verbose 开详细日志）
uv run --extra test python -m pytest -q   # 全量测试（uv virtual 布局包不装 venv，测试内导入项目模块须用 src. 前缀）
ruff check . && ruff format .        # 代码检查 / 格式化
```

GUI 启动器（推荐；自动使用 .venv-gui，环境缺失时会给出创建命令）：

```bash
启动器.bat                                            # 双击用这个；加 debug 参数保留控制台窗口
.\.venv-gui\Scripts\python.exe launcher\OpenLLMVTuber_GUI.py   # 备选：直接运行（依赖 PySide6-Essentials、ruamel.yaml、psutil）
```

## ⚠️ 硬性契约速查

- git 提交身份：yancheng1018 <55277749+yancheng1018@users.noreply.github.com>，勿用旧占位身份（公开仓库隐私；换机/新克隆须先设）

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
frontend-minimal/                  自研极简前端（唯一前端，入口 /m/）
scripts/                           维护脚本（live2d 扫描/标定/修复 4 件 + gpt_sovits 启动器，见 repo-maintenance 工具节）
config_templates/                  默认配置模板
```

## 按需加载索引

| 任务场景 | 读取文件 |
|----------|----------|
| 改配置/角色/人设/语言 | docs/context/config-system.md |
| 改 Live2D 模型/表情/动作/尺寸 | docs/context/live2d.md |
| 改 GUI 启动器/声音模型/编辑器 | docs/context/gui-launcher.md |
| git/搬移文件/分批提交/文档体系维护 | docs/context/repo-maintenance.md |
| 加忽略/资产出库/隐私守卫 | docs/context/repo-ignore-policy.md |
| 改后端/Ollama/streaming/加引擎 | docs/context/ollama-backend.md |
| 续接工作/排优先级 | docs/context/current-work.md |
| 查历史决策/仓库重组历程与施工踩坑 | docs/context/archive.md · docs/context/spec-git-reorganize.md |
| 开发极简自研前端（总入口/遗留） | docs/context/minimal-frontend.md |
| 极简前端 工程/协议/历史/口型 | docs/context/minimal-frontend-foundation.md |
| 极简前端 Live2D 手势/触摸引擎/复位 | docs/context/minimal-frontend-live2d.md |
| 极简前端 Live2D 调试栏/热区叠加层 | docs/context/minimal-frontend-live2d-debug.md |
| 极简前端 Spine 渲染 | docs/context/minimal-frontend-spine.md |
| 极简前端 模型切换/allowlist | docs/context/minimal-frontend-model-switch.md |
| 查 Live2D 触摸引擎设计与 l2d.su 逆向 | docs/context/spec-l2d-touch-engine.md · docs/context/spec-l2dsu-engine.md |
| 写规格书（断言盘点/锚点/基线/行数预检） | docs/context/spec-writing.md |

## 用户级工作流绑定

供用户级命令（~/.zcode/commands/）解析本项目上下文用：
- 当前状态入口：docs/context/current-work.md
- 文档目录：docs/context/（temp_spec / impl_report / fix_instruction / research_* 均在此）
- 归档文件：docs/context/archive.md
- 模块知识索引：即上方「按需加载索引」表

## 维护规则

- 根文件 ≤ 100 行，超限就压缩或再拆
- 单模块 ≤ 200 行，超限就再拆
- 新增结论先归域：写进对应模块文件；只有「任何任务都可能踩」的红线才升级到根文件
- 索引表与实际文件名严格一致，改名必须同步
- 每完成一个阶段，跑一次行数检查和索引表一致性检查
- 默认不执行 git push：push 属发布动作，须用户明确要求（github-p2-release 阶段亦须用户确认）
