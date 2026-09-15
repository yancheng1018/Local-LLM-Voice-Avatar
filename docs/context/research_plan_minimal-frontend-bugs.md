# 研究大纲 · minimal-frontend 现存 bug 成因（research_plan）

> 生成于 2026-09-15，/plan-research 产物。执行命令：/research-doc。
> 本文件是规划，不是研究结论；下述「初步线索」仅为定位提示，未经证实。

## 1. 研究问题定义

minimal-frontend 当前两个已知 bug 的确切成因：①GUI 角色编辑器人设留空保存后服务器启动失败；②选择 shizuku 模型无法显示，且从 shizuku 切回正常模型后也无法显示。

## 2. 需要回答的子问题

| # | 子问题 | 初步线索（待证实） |
|---|--------|--------------------|
| Q1 | bug1-a：人设留空时启动失败的完整链路——GUI 保存到底写了什么（空字符串 / 漏键不写）→ 配置加载在哪一步抛错 → 报错如何呈现给用户（服务器日志 / GUI 运行日志） | `character.py:25` persona_prompt 为必填 Field；`character.py:90-96` 空值直接 raise ValueError。GUI 侧 `OpenLLMVTuber_GUI.py:1657` 保存时无空值拦截 |
| Q2 | bug1-b：GUI 保存路径为何没拦截——`_save_character_inline` / `char_edit_fields` 通道对必填字段有无校验；对比 conf_uid「留空自动补 `{conf_name}_001`」的既有做法 | gui-launcher.md 记载「空的可选字段不会写入 YAML」，但 persona 非可选；需确认空值走哪条分支 |
| Q3 | bug2-a：shizuku 无法显示的成因——入口文件 `shizuku.model3.json` 嵌套在 `live2d-models/shizuku/runtime/` 下而非模型根目录，`model_dict.json` 登记路径、后端 switch 处理、前端加载、HTTP 静态路由四层中哪一层断掉 | `model_dict.json` 在仓库根（`./model_dict.json`），其 shizuku 条目内容未查 |
| Q4 | bug2-b：从 shizuku 切回正常模型后仍不显示的成因——前端 l2d.ts 加载/切换/销毁顺序（旧模型先释放？加载失败后状态未回滚？）、main.ts 切换流程、后端 `switch-live2d-model` 处理 | 前端入口 `main.ts:394-401`；后端 `websocket_handler.py` / `service_context.py` |
| Q5 | 交叉判定：两 bug 是否共享根因；shizuku 是「路径登记问题」还是「模型文件本身问题」——判定用户「直接删除 shizuku」是否足以消除 bug2 全部症状（切回失败必须另有解释） | 对照 stage4/5 已定契约（minimal-frontend-model-switch.md） |

## 3. 每个子问题的查阅位置

**Q1/Q2（bug 1，GUI + 配置校验）**
- `launcher/OpenLLMVTuber_GUI.py:1536,1594,1657`（人设读/默认值/写回）＋ `_save_character_inline` 函数体（rg 定位，读完整写回分支）
- `src/open_llm_vtuber/config_manager/character.py:25,90-96`（必填 + 空值校验器）
- 配置加载调用链：rg `CharacterConfig(` / `validate` 于 `src/open_llm_vtuber/config_manager/`，找到抛错点
- 报错呈现：`run_server.py` 启动异常路径 + GUI「运行日志」窗口如何转发 stderr

**Q3/Q4（bug 2，模型路径 + 前端切换）**
- `model_dict.json`（shizuku 条目的路径写法）
- `live2d-models/shizuku/runtime/shizuku.model3.json`（入口嵌套 + FileReferences 相对路径）
- 前端：`frontend-minimal/src/main.ts:394-401`、`frontend-minimal/src/renderer/l2d.ts`（加载/切换/释放全流程）
- 后端：`src/open_llm_vtuber/websocket_handler.py`、`src/open_llm_vtuber/service_context.py`（`switch-live2d-model` 处理与 model_dict 读取）
- 静态路由：rg `live2d-models` 于 `src/open_llm_vtuber/server.py`（模型 URL 如何拼、嵌套目录是否可达）

**Q5（交叉）**
- `docs/context/minimal-frontend-model-switch.md`（stage4/5 契约：allowlist、切换 merge 底只能是 conf.yaml 自身块）
- `docs/context/config-system.md`（角色配置结构、默认角色指针方案）

## 4. 输出文档结构（/research-doc 产出的 research_minimal-frontend-bugs.md 章节）

1. 背景与复现条件（两个 bug 的操作路径、环境）
2. Bug 1：GUI 人设留空致启动失败——保存写回分支 + 校验抛错点 + 报错呈现，完整链路
3. Bug 2a：shizuku 无法显示——四层路径解析逐层核查结论
4. Bug 2b：切回正常模型仍不显示——前端加载/切换/销毁状态机走查结论
5. 根因归纳与交叉分析（含「删除 shizuku 是否足够」判定）
6. 修复方向候选（仅列候选，不做设计）＋ 遗留候选
7. 附录：涉及文件与行号清单

## 5. 已知约束和边界

- 本研究**只查成因**：不写实现代码、不做修复设计；修复另走 fix_instruction 流程
- bug2 若结论为「shizuku 模型文件本身的问题」，用户已接受直接删除该模型；但「切回正常模型仍不显示」**必须查清**（它影响正常模型，不能靠删 shizuku 消失）
- 硬性契约：list[str] 字段不得走 `char_edit_fields` 通道；角色自我认知名来自 persona_prompt（意味着人设不允许为空是**有意设计**，修复方向不得是放宽校验）；模型切换 merge 底只能是 conf.yaml 自身块
- `OpenLLMVTuber_GUI.py` 只跑 `ruff check` 不 format（排版 diff 会淹没改动；研究阶段本就不改它）
- 研究阶段允许起服务观察复现（不改代码）；若需实测 shizuku 切换，注意 GPU 争用已知问题（Ollama+GPT-SoVITS），不属本 bug 范畴
- 待确认疑点（执行前需用户裁决）：
  1. bug2 是否要求起服务实测复现，还是纯代码走查下结论即可（实测更可靠但需占 GPU/端口）
  2. 第 6 章「修复方向候选」是否保留（默认保留但仅列候选、不展开设计）
