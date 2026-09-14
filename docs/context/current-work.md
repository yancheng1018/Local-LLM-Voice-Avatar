## 当前需求

> git_stage3 已收尾：ruff 清零、Temp 悬空引用订正、git 上游残留清除。
> 后续需求写在这里。

### 待处理
- 其余模型按需处理：37 个 Idle/Talk 组大小写不匹配（跑 `scan_live2d_models.py`
  生成 `live2d_scan_report.md` 查看），
  40 个 emotionMap 为空；两者都只影响对应模型被使用时的表现，用哪个补哪个
 

> 极简自研前端的完整设计、实现细节、踩坑记录见 docs/context/minimal-frontend.md
