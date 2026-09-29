## 忽略与资产出库策略

> 做加忽略规则、资产出库/隐私退役、tracked-but-ignored 排查前读这里。
> 拆分自 repo-maintenance.md（2026-09-30，github-p2-precheck-d）。

### 忽略规则与已追踪文件的冲突（重要）

`.gitignore` 是**声明式**的，它只影响未追踪文件。已经进入索引的文件即使后来
被规则命中，**依然保持追踪**——这是设计如此，不是 bug，也无需 `git rm --cached`。

| 现象 | 真相 |
|------|------|
| 加了 `voices/` 规则后 `voices/<声音名>/voice.json` 仍被追踪 | 正常，它本就在索引里 |
| 想提交该类文件的**修改**，`git add voices/...` 被拒（ignored） | **这才是真问题**，须 `git add -f` |

自查有哪些已追踪文件落进了忽略范围：

```bash
git ls-files -i -c --exclude-standard
```

2026-09-30 批 b 后口径：**无 tracked-but-ignored 项**（`avatars/` 2 项、`backgrounds/` 15 项
已随 github-p2-precheck-b `git rm --cached` 出索引保磁盘，finalize_exec_distill-b1 已随批 a
出索引；voices/ 私有资产更早已随 github-p0-privacy 出索引）。

### 本仓库的忽略策略

- `live2d-models/*` 整体忽略，仅 `!mao_pro/` 一个上游示例模型入库（shizuku 已删，其死白名单行随 distill-b2 清理）。
- `models/`、`Spine-models/`、`voices/` 忽略但**保磁盘**（avatars/、backgrounds/ 已随 github-p2-precheck-c 删盘退役）。
- `frontend/`（旧官方前端）已于 github-p1-robust（2026-09-29）整体退役：目录删除，server.py mount
  与 run_server.py 启动检查删除，GUI 前端选项删除，根路径 307 引导 /m/；防回潮守卫 =
  tests/test_server_frontend_guard.py。恢复路径 = 上游 https://github.com/Open-LLM-VTuber/Open-LLM-VTuber-Web
  （branch=build）clone 回 frontend/ + 从上游 server.py 抄回 mount 段（忽略规则保留，防重取后误入库）。
- `conf.yaml` 忽略，入库模板是 `config_templates/conf.ZH.default.yaml`。
- 根目录 `conf.yaml.bak` / `.backup`、`model_dict.json.bak` 属脚本自动备份，一并忽略。
- `docs/context/temp_spec_*.md` 与 `docs/context/impl_report_*.md` 忽略：施工期的临时图纸，
  结论沉淀进归档文档后即弃。**已入库的同名历史文件不受影响**（声明式规则只作用于未追踪文件），
  改它们仍须 `git add -f`。阶段收尾时把有长期价值的规格书改名为 `spec-*.md` 入库。
- 私有资产出库（github-p0-privacy，2026-09-29）：`launcher/launcher_config.json`（运行时状态，
  缺失时 launcher 自动重建）、characters/ 下 5 个本地角色 yaml、`docs/assets/_ships_cache/` 与
  `su_ships-CN.json`（舰船数据缓存）已 `git rm --cached` 出索引并补忽略规则，磁盘保留。
  其中 ja_test.yaml 已于 github-p0-characters 本地改名 shinano.yaml（忽略项与守卫前缀同步换名）。
- 私有声音名守卫名单（github-p0-decouple）：`tests/private_names.local.txt` 为本地忽略文件，
  每行一个私有名（`#` 注释）；守卫在名单缺失时 skip（静默失效）→ 换机/新克隆须重建。
- git filter-repo 默认重写**所有 ref**：`git branch` 备份会被一并重写，退路必须放仓库外
  （`git bundle create ../<名>.bundle --all`；github-p0-privacy 实证，两轮重写均此法）。
- github-p0-privacy 终态：42 项出索引保磁盘；voices 声音卡、launcher_config.json、舰船缓存
  34 项已抹历史；作者全量 `yancheng1018 <55277749+yancheng1018@users.noreply.github.com>`；
  索引守卫 = tests/test_repo_privacy_guard.py（新增出库资产须同步补其 PRIVATE_PATH_PREFIXES
  与 .gitignore）。
