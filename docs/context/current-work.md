## 当前阶段

### 当前需求
> git_stage3 已收尾：ruff 清零、Temp 悬空引用订正、git 上游残留清除。
> 后续需求写在这里。

### 待处理遗留

- 其余模型按需处理：37 个 Idle/Talk 组大小写不匹配（跑 `scan_live2d_models.py`
  生成 `live2d_scan_report.md` 查看），40 个 emotionMap 为空；
  两者都只影响对应模型被使用时的表现，用哪个补哪个。

- pytest 未纳入任何依赖组……
  待把 pytest 加入 pyproject.toml `[project.optional-dependencies]` 新 test 组后该命令即废；
  此项与 minimal-frontend 无关，属仓库环境杂务。

### 相关背景
> 极简自研前端的完整设计、实现细节、踩坑记录见
> docs/context/minimal-frontend.md