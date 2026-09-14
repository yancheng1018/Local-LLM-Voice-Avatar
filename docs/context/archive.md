# 历史归档（已完成记录）

> 压缩格式：日期 + 做了什么 + 留下的契约/文件。过程性叙述不复述，事实以代码与 git log 为准。

## 2026-09-10 综合会话（GUI v2.0~v2.4 与遗留修复）
- GUI 启动器迭代至 v2.4：模型页、角色编辑器、贴图预览、voices/ 声音模型体系、Live2D 导入（自动登记 model_dict.json）、启动后自动开浏览器；另做 streaming_mode 注解等遗留修复
- 留下：`启动器.bat`（须保持 GBK 编码、不加 chcp）；conf.yaml `ref_audio_path` 指向 `voices/加藤惠/ref.wav`；加藤惠 Live2D 因 Cubism 2.1 前端不支持而弃用并移出 model_dict.json，其余 41 条 url 核对有效

## 2026-09-10 Live2D 动作表现优化
- 为 xinnong_6 / mao_pro 补 Idle / Talk 动作组与 tapMotions（默认角色从完全静止变为有待机/说话/点击反应）；修正 mao_pro emotionMap 三处错误映射（fear/sadness 原指开心、anger 原指闭眼）并扩至 50 键；重写 live2d_expression_prompt.txt（每句最多一个关键词且放句首）
- 留下：`<think>` 内句子不提取表情、显示文本剔除 [关键词]（transformers.py）；`scan_live2d_models.py` + `live2d_scan_report.md`；非显而易见结论：41 个模型中 37 个 Idle/Talk 组大小写不匹配，mao_pro 是唯一有 HitAreas 的模型，xinnong_6 无表情文件（情绪关键词对它天然无效）

## 2026-09-11 尺寸自适应与关键词显示
- 新增 `fit_live2d_scale.py`：按 moc3 CanvasInfo（u32@0x44）重算全部 41 个模型 kScale，游戏系模型（逻辑画布高 > 5）追加 ×1.5 目测倍率；emotionMap 为空时跳过表情提示词（防 LLM 编造关键词），显示文本正则兜底剔除剩余方括号 token（与 TTS 侧 ignore_brackets 对齐）
- 留下：moc3 顶点自动求包围盒因 keyform 间接索引不可行（勿重试）；mao_pro kScale 保持 0.5（标定自洽）；TTS 重启后首句 65s 属 GPT-SoVITS 冷启动非回归，首音频延迟高也与 `faster_first_response=false` 有关——复现时可加启动预热并改 true（用户暂不改）

## 2026-09-13 上下文文件重构
- 将 ZCODE_CONTEXT.md（约 990 行）拆分为 AGENTS.md（77 行）+ docs/context/ 下 7 个模块文件，实现按需加载
- 根文件保留概述、端口、高频命令、硬性契约速查、索引表、维护规则
- 索引表按任务场景指向模块文件；新增 minimal-frontend.md 收录极简前端设计
- 原文件已删除，备份保留为 ZCODE_CONTEXT.md.bak
## 2026-09-14 合并 Live2D 触摸引擎规格书
- 将 temp_spec_stage1~6 合并为 docs/context/spec-l2d-touch-engine.md
- 固化偏离站点项 D1~D3、明确不做清单、遗留 C4/C6
- 删除已合并的 temp_spec_stage1~6

## 2026-09-14 仓库整理与上游切割（git_stage1~3）
- 三阶段：文件归位与索引整理 → 与上游切割 → 收尾清理（lint/悬空引用/残留）
- 合并 temp_spec_git_stage1~3 与 impl_report_git_stage1~3 为 docs/context/spec-git-reorganize.md，原文删除
- 留下：无 remote、`push.default = nothing`、ruff 归零；`config_templates/` 确认为运行时依赖；
  `frontend/` 忽略但保磁盘（`server.py:172` 无守卫，删前须补）；`Temp/` 逆向产物确认不可找回（见 docs/assets/README.md）
