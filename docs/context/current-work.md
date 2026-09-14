## 当前阶段

### 当前需求
> 下一阶段：minimal-frontend stage5 —— 一角色多模型 allowlist。
> 边界已定（stage4 规格 §9；规格书提炼后以 minimal-frontend.md 为准）：
> - 扩展 CharacterConfig/YAML：live2d_model_names（允许列表）+ live2d_model_name（当前/默认）
> - 后端 live2d-models 消息由全局列表改为按当前 conf_uid 返回 allowlist
> - 迁移规则、编辑器 UI、旧 YAML 兼容、默认模型回退：另立 stage5 规格书

### 待处理遗留

- [live2d] 37 个模型 Idle 组大小写不匹配（实际为 `idle`，空闲动作不播放）：
  跑 scan_live2d_models.py 生成根目录 live2d_scan_report.md 查看，用哪个补哪个（加 Idle 别名组）
- [live2d] 40 个模型 emotionMap 为空（情绪关键词不触发表情）：同样按需补
- [环境] pytest 未入 pyproject [project.optional-dependencies]：加 test 组后
  frontend-minimal 测试可 venv 直跑（现需 uv run --with pytest）；仓库杂务，与前端无关
- [doc-lifecycle] 极简前端线 6 份规格书 + 4 份 impl_report 待 /distill-spec
  提炼后删除（触摸引擎线 6 份与热区 1 份已于本阶段清理）

### 相关背景
> 极简自研前端设计与踩坑：docs/context/minimal-frontend.md
> 历史决策：docs/context/archive.md
