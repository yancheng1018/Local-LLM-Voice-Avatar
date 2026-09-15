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

### 相关背景
> 极简自研前端设计与踩坑：docs/context/minimal-frontend.md
> 历史决策：docs/context/archive.md
