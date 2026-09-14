## 当前阶段

### 当前需求
> minimal-frontend stage5（一角色多模型 allowlist）已实现并通过审查（2026-09-15）。
> 待办：stage5 规格 §8 手工验收（服务起后执行，5 项）：
> 1. 给某角色 YAML 手加 `live2d_model_names: [mao_pro, <另一模型名>]` → 下拉只有这 2 项，切换生效
> 2. 无该字段的角色：下拉仍是全局列表
> 3. allowlist 写不存在的模型名：条目不出现，服务端日志有 warning
> 4. 启动器编辑器：允许列表行显示逗号串；保存后 YAML 是列表；清空保存写回 []；不碰该行保存不丢
> 5. spine_test 角色：行为与 stage4 一致

### 待处理遗留

- [live2d] 37 个模型 Idle 组大小写不匹配（实际为 `idle`，空闲动作不播放）：
  跑 scan_live2d_models.py 生成根目录 live2d_scan_report.md 查看，用哪个补哪个（加 Idle 别名组）
- [live2d] 40 个模型 emotionMap 为空（情绪关键词不触发表情）：同样按需补
- [环境] pytest 未入 pyproject [project.optional-dependencies]：加 test 组后
  frontend-minimal 测试可 venv 直跑（现需 uv run --with pytest）；仓库杂务，与前端无关
- [doc-lifecycle] 极简前端线 7 份规格书 + 5 份 impl_report 待 /distill-spec
  提炼后删除（触摸引擎线 6 份与热区 1 份已于 stage4 阶段清理）
- [stage5] launcher ruff format 全文件重排单独立项：stage5 曾尝试对
  launcher/OpenLLMVTuber_GUI.py 跑 format，产生 +332/-181 纯排版 diff
  （该文件历史样式从未 format 过），已回退保持最小功能 diff；
  触发时机：作为独立的排版工程提交，不混入功能阶段

### 相关背景
> 极简自研前端设计与踩坑：docs/context/minimal-frontend.md
> 历史决策：docs/context/archive.md
