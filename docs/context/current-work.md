## 当前阶段

### 当前需求
> minimal-frontend 阶段一~五全部完成并验收通过（2026-09-15）。stage5（一角色多模型
> allowlist）经两轮审查修复：fix1（合并底套默认角色指针）被手工复验驳回，
> fix2 改为 conf.yaml 自身块作 merge 底后四点复验通过。
> 无既定下一阶段；待办与遗留见下方清单。

### 待处理遗留

- [live2d] 37 个模型 Idle 组大小写不匹配（实际为 `idle`，空闲动作不播放）：
  跑 scan_live2d_models.py 生成根目录 live2d_scan_report.md 查看，用哪个补哪个（加 Idle 别名组）
- [live2d] 40 个模型 emotionMap 为空（情绪关键词不触发表情）：同样按需补
- [环境] pytest 未入 pyproject [project.optional-dependencies]：加 test 组后
  frontend-minimal 测试可 venv 直跑（现需 uv run --with pytest）；仓库杂务，与前端无关
- [stage5] launcher ruff format 全文件重排单独立项：stage5 曾尝试对
  launcher/OpenLLMVTuber_GUI.py 跑 format，产生 +332/-181 纯排版 diff
  （该文件历史样式从未 format 过），已回退保持最小功能 diff；
  触发时机：作为独立的排版工程提交，不混入功能阶段
- [stage6] l2d.ts `load()` 先销毁后加载、失败不恢复旧模型：本阶段只修状态机
  （清空模型名，重选任意模型即可恢复），失败后舞台仍短暂空白直到用户重选。
  是否收敛为统一「重建回滚」模式（与 ensureRenderer 同属先销毁无回滚）另立项
- [stage6] characters/en_nuke_debate.yaml 的 `live2d_model_name: "shizuku-local"`
  本就与登记名不符；stage6 删除 shizuku 后目录也不存在（删前删后该角色都无模型），
  不影响启动。建议删除该示例角色或改指向有效模型，待裁决
- [stage6] 既有失败基线：`test_live2d_model_switch.py::test_resolver_runtime_allowlist`
  报 `ModuleNotFoundError: No module named 'prompts'`（测试导入路径问题，非代码回归）；
  已用 stash 基线比对确认与 stage6 改动无关，勿当回归处理

### 相关背景
> 极简自研前端设计与踩坑：docs/context/minimal-frontend.md
> 历史决策：docs/context/archive.md
