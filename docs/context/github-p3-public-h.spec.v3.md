# github-p3-public-h · 新模型登记缺口修复批（roadmap v1.0.1 #8）· spec v3

> v2 经实施暴露第 4 处守卫点（:397）修订而来（2026-10-08 /replan-from-impl）；本版为完整
> 规格，弱模型只读这一份施工，v1/v2 作废。裁决记录：:397 修法经用户 /replan-from-impl 裁定。
> 纪律：未经用户确认不 git add/commit；测试失败只能修实现或停下汇报，不得放宽断言。
> **全局前提：所有命令块按 Git Bash 语法书写（heredoc/管道/tail）；若实施会话 shell 为
> cmd/PowerShell，heredoc 块须改等价 python -c 单行并在报告注明改写。所有命令均在仓库根
> `C:\Coding\Application\Local-LLM-Voice-Avatar` 执行。**

## 续作状态（v2 会话已落盘，先核对再续，不重做）

- S0 ✅ 基线 200 passed；S1 ✅ tests/test_live2d_fallback_guards.py 已建（红面 ②④⑤⑥ 与
  v2 预期一致）；S2 部分 ✅ :197/:350/:712 三处守卫**已落地**（工作区现状）。
- 续作起点：核对下述「核对命令」输出与预期一致 → 从 **S2b（:397 第 4 处守卫）** 开始，
  续走 S3/S3b 及以后。若核对不符 → 停下汇报，不得自行修补。
- 核对命令：
  ```bash
  cd "C:\Coding\Application\Local-LLM-Voice-Avatar"
  uv run --extra test python -m pytest tests/test_live2d_fallback_guards.py -q 2>&1 | tail -8
  ```
  预期：`1 failed, 6 passed`，唯一失败=④（AttributeError @ service_context.py:397）。

## 0. 背景与根因（一段）

新增模型 fengyun_4/rangbaer_5 未登记本机 active 表 `model_dict.local.json`（42 条，含
wuqi_3 不含两新模型；active 解析规则=同名兄弟 `.local` 整份取代基准，
`src/open_llm_vtuber/live2d_model.py:203-212`）。kazagumo 角色卡引用 fengyun_4 →
`service_context.py:335-342` init_live2d 容错把 live2d_model 留 None 继续 → 每个 WS 连接在
`websocket_handler.py:197` 无守卫解引用 `None.model_info` 崩掉（表现为「服务无法启动」）。
下拉缺模型=同一张表缺登记。修复=①补录两条目（含 idle 别名组与 kScale 回填）②守卫 4 处
None 解引用兑现「proceed without Live2D」容错。

**异常类型事实**：`Live2dModel` 对未登记名抛 `KeyError`（live2d_model.py:115-119，:117）。

两疑点闭环（roadmap #8 条目「plan 首核」）：
- rangbaer_5 不在 active 表：已实证（2026-10-08，grep False/False）。
- 日志 `live2d_model_names=[]`：kazagumo 卡未配置 allowlist，[] = 未配置 →
  `resolve_allowed_model_names()` 回退全局名单（minimal-frontend-model-switch.md stage5
  语义），日志打印原始字段值，非缺陷，不处理。

**钉定的事实（2026-10-08 实跑）**：
- 全量基线 **200 passed**（kazagumo.yaml 已在盘）。
- 两源文件 ruff format --check 与 ruff check 双 clean；`ruff format --check tests/` 有两个
  既有脏文件（test_publish_facade.py、test_repo_privacy_guard.py，已登记遗留债，本批不碰）。
- kScale 复算（确定性）：mao_pro=0.5、wuqi_3=0.063 与表内一致；fengyun_4 期望 **0.0621**
  （ppu 380.95，8000×8000 游戏系画布乘 GAME_FACTOR 1.8）、rangbaer_5 期望 **0.0532**
  （ppu 326.53）。
- **v3 新增**：switch_live2d_model 成功尾部 :397 日志解引用 `old_model.live2d_model_name`，
  None 态恢复路径必炸（v2 会话 S3 实证，用例④为凭据）。

## 1. 修改文件清单（含行数预检，spec-writing §5）

| # | 文件 | 改动 | 行数预检 |
|---|------|------|---------|
| 1 | `src/open_llm_vtuber/websocket_handler.py` | :197 行内守卫（已落，续作核对即可） | 现 722 行（存量超标技术债）；增行≤3 |
| 2 | `src/open_llm_vtuber/service_context.py` | :350、:712 守卫（已落）+ **:397 日志变量替换（v3 新增，待落）** | 现 751 行（存量超标）；增行≤9（format 折行） |
| 3 | `tests/test_live2d_fallback_guards.py` | 已建（7 用例，续作核对） | 175 行 ≤200 ✅ |
| 4 | `model_dict.local.json` | 补录 2 条目 + 各回填 kScale；备份 `model_dict.local.json.bak` | 本体与 `.bak` 均被 gitignore（.gitignore:32/:33）不入库 |
| 5 | `live2d-models/fengyun_4/fengyun_4.model3.json`、`rangbaer_5/rangbaer_5.model3.json` | 脚本加精确 `Idle` 别名组（纯数据） | 整目录被忽略（.gitignore:11，含 .bak）不入库 |
| 6 | `docs/context/minimal-frontend-model-switch.md` | 末尾（紧随 stage6 节 :41-48）追加 1 条降级契约 bullet（~6 行） | 现 48 行 +6，余量足 |

不改动：kazagumo.yaml（untracked 保持，不 git add）；model_dict.json（基准表钉死仅
mao_pro，绝不触碰）；.gitignore；前端任何文件。唯一性校验
（tests/test_characters_manifest.py:62-72）遍历磁盘全卡即刻生效——「風雲」无重名，绿。

## 2. 守卫点精确规格（4 处改 + 1 处论证不改；前 3 处已落地）

- **websocket_handler.py:197**（已落，核对）：
  `"model_info": session_service_context.live2d_model.model_info if session_service_context.live2d_model else None,`
- **service_context.py:712**（已落，核对）：
  `"model_info": self.live2d_model.model_info if self.live2d_model else None,`
- **service_context.py:350**（已落，核对）：
  `if self.live2d_model is not None and self.live2d_model.live2d_model_name == model_name:`
  （None 态视为「非当前模型」，继续走 candidate 构造；candidate :354 对未登记名抛
  KeyError，上游 :666-675 except Exception 捕获回 error 消息，语义自洽）
- **service_context.py:397（v3 新增，待落）**：
  改前：`f"Switched Live2D model: {old_model.live2d_model_name} -> {model_name}"`
  改后：`f"Switched Live2D model: {old_model_name} -> {model_name}"`
  依据：`old_model_name` 在 :366 捕获自 `character_config.live2d_model_name`；本方法成功
  路径（:368-369）与回滚路径（:390-391）均成对维护 `live2d_model.live2d_model_name ≡
  character_config.live2d_model_name`（init_live2d 成功 :338-339 同样成对），非 None 场景
  两值恒等，替换语义无损；None 场景 `old_model_name` 即角色卡原值（字符串，None 安全）。

**论证不改**：websocket_handler.py:682。到达该行必经 `switch_live2d_model` 成功
（:666-675 失败即 except→error→return），成功路径 self.live2d_model 已置非 None
candidate（:368），None 不可达。执行层不得「顺手」加守卫。

**前端契约依据（勿改前端）**：main.ts:83-89 对空 `model_info` 现成降级
（`if (!modelInfo?.url) ui.setStatus('未配置模型', true)`）；history.ts:7 历史初始化挂在
set-model-and-conf 上，消息照发不省略。

## 3. 断言面盘点（数据改动影响预判，均经独立复核）

| 现有测试 | 与本批关系 | 预期 |
|---|---|---|
| tests/test_characters_manifest.py:55/:62-72 | 读基准表 / 磁盘全卡唯一性 | 不触，绿 |
| tests/test_repo_privacy_guard.py:29 | 断言 .local 被忽略 | 只编辑不入库，绿 |
| tests/test_live2d_model_data.py:69 | FULL_KNOWN ⊆ in_use 子集断言 | +2 条无影响，绿 |
| tests/test_live2d_model_data.py:84 | 补录+kazagumo 卡使 fengyun_4 进 in_use，强校验精确 `Idle` 非空组 | 两新模型现仅小写 `idle`（实证）→ **不修必红**；S5 后绿 |
| tests/test_live2d_model_data.py:111 | 基准/本地 mao_pro 条目逐字段一致 | 只回填两条（S6），mao_pro 字节不动，绿；不跑全量 fit=最小 diff 原则（复算实证一致，非防红） |
| frontend-minimal/tests/test_model_load_guards.py:60 | 读基准表 | 不触，绿 |
| frontend-minimal/tests/test_live2d_model_switch.py（:57-131、:324-342） | 全部 tmp_path fixture | 不触，绿 |

## 4. 测试文件规格 `tests/test_live2d_fallback_guards.py`（已建，v3 无改动，核对用）

7 用例：① init 容错留 None（绿）② :197 发 null（红→绿）③ 正常 model_info 透传（绿）
④ None 态切换恢复（红→绿，**兼作 :397 回归守卫**）⑤ 坏名 KeyError 且状态不变（红→绿）
⑥ :712 静态守卫正则（红→绿）⑦ :682 可达性前提锁定（绿）。写法：__new__ 构造+被测属性
逐个显式挂（ServiceContext 属性全实例级，service_context.py:59-89）；asyncio.run 不依赖
pytest-asyncio；异常锚 KeyError；静态正则空白不敏感（\s*）兼容 format 折行。

**S1 红面基准（v2 会话已取证）**：守卫落地前 ②④⑤⑥ 红、①③⑦ 绿；:397 修复前 ④ 红
（AttributeError）——④ 的绿即 :397 修复的验收。

## 5. 实施步骤（S2b 起续作；〔工〕=工具可完成，〔判〕=需要判断）

- **S0-S2（已落盘）**：见「续作状态」节核对，不重做。
- **S2b〔判〕落第 4 处守卫**：按 §2 改 :397（仅此一处替换，不动 :682）。
- **S3〔工〕守卫绿证**：
  ```bash
  uv run --extra test python -m pytest tests/test_live2d_fallback_guards.py -q 2>&1 | tail -8
  ```
  预期 7 用例全绿。
- **S3b〔工〕格式与 lint**：只对 3 个触碰文件，**禁止全仓 ruff format .**：
  ```bash
  uv run ruff format src/open_llm_vtuber/websocket_handler.py src/open_llm_vtuber/service_context.py tests/test_live2d_fallback_guards.py
  uv run ruff check src/open_llm_vtuber/websocket_handler.py src/open_llm_vtuber/service_context.py tests/test_live2d_fallback_guards.py
  uv run --extra test python -m pytest tests/test_live2d_fallback_guards.py -q 2>&1 | tail -5
  ```
  预期：format 折守卫行（合法重排）；check 0 错误；测试仍全绿。
- **S4〔工〕备份+补录登记**：
  ```bash
  cp model_dict.local.json model_dict.local.json.bak
  git check-ignore model_dict.local.json.bak || echo "不被忽略，停下汇报"
  uv run python - <<'EOF'
  import json
  from pathlib import Path
  p = Path("model_dict.local.json")
  entries = json.loads(p.read_text(encoding="utf-8"))
  known = {e["name"] for e in entries}
  def entry(name):
      # 模板=GUI 登记模板 launcher/OpenLLMVTuber_GUI.py:1965-1977，url 推导同 :1956
      return {
          "name": name, "description": "",
          "url": f"/live2d-models/{name}/{name}.model3.json",
          "kScale": 0.5, "initialXshift": 0, "initialYshift": 0,
          "kXOffset": 1150, "idleMotionGroupName": "Idle",
          "emotionMap": {}, "tapMotions": {},
      }
  for name in ("fengyun_4", "rangbaer_5"):
      if name not in known:
          entries.append(entry(name))
  p.write_text(json.dumps(entries, ensure_ascii=False, indent=4), encoding="utf-8")
  print("entries:", len(entries))
  EOF
  ```
  预期 `entries: 44`（幂等）；check-ignore 无输出=被忽略（正常）。
- **S5〔工〕Idle 别名组**（幂等、逐文件整字节 .bak 落被忽略目录、只加别名组）：
  ```bash
  uv run python scripts/fix_live2d_idle_groups.py
  ```
  预期仅 fengyun_4、rangbaer_5 新增 `Idle`（无小写 talk 变体，Talk 跳过）；若动了其他
  既有模型 → 如实记录到 report（契约对齐，非缺陷），继续。
- **S6〔工〕kScale 两条回填**（期望值钉定 0.0621/0.0532；不跑全量 fit）：
  ```bash
  uv run python - <<'EOF'
  import json, sys
  sys.path.insert(0, "scripts")
  from fit_live2d_scale import find_moc3, parse_canvas_info, compute_kscale
  expected = {"fengyun_4": 0.0621, "rangbaer_5": 0.0532}
  p = "model_dict.local.json"
  entries = json.load(open(p, encoding="utf-8"))
  for e in entries:
      if e["name"] not in expected:
          continue
      info = parse_canvas_info(find_moc3(e["url"]))
      k = compute_kscale(info[0], info[3], info[4])
      print(e["name"], "旧", e["kScale"], "新", k)
      assert k is not None and abs(k - expected[e["name"]]) < 1e-9, (
          f"{e['name']} kScale={k} 与钉定期望 {expected[e['name']]} 不符，停下汇报"
      )
      e["kScale"] = k
  with open(p, "w", encoding="utf-8") as f:
      json.dump(entries, f, indent=4, ensure_ascii=False)
  EOF
  ```
- **S7〔工〕数据终验**（口径：`load_model_dict("model_dict.json")` 经 resolve_model_dict_path
  取 active=.local，与前端下拉同源，live2d_model.py:203-212/:215-244）：
  ```bash
  uv run python -c "
  from src.open_llm_vtuber.live2d_model import Live2dModel, load_model_dict
  import json
  names = [e['name'] for e in load_model_dict('model_dict.json')]
  assert 'fengyun_4' in names and 'rangbaer_5' in names and len(names) == 44, names
  for n in ('fengyun_4', 'rangbaer_5'):
      m = Live2dModel(n)
      assert m.model_info['url'].endswith(n + '.model3.json')
      print(n, m.model_info['url'], 'kScale=', m.model_info['kScale'])
      d = json.load(open(f'live2d-models/{n}/{n}.model3.json', encoding='utf-8'))
      assert d['FileReferences']['Motions'].get('Idle'), n + ' 缺精确 Idle 别名组'
  print('data OK')
  "
  ```
- **S8〔工〕全量回归**：命令见 §6；预期=S0 实跑数（200）+ 新文件 7 用例（收集数以实跑
  为准）全绿、0 failed；`test_mao_pro_entry_not_drifted` 必须仍绿。
- **S9〔判〕文档、泄漏面检查与报告**：
  - docs/context/minimal-frontend-model-switch.md 末尾（紧随 stage6 节）追加：
    「**live2d_model=None 降级契约（github-p3-public-h）**：init_live2d 容错失败后
    live2d_model=None，连接不拒、降级服务。所有 set-model-and-conf 发送点
    （_send_initial_messages / handle_config_switch）守卫 None、model_info 发 null——前端
    main.ts 对空值现成降级（未配置模型）；switch_live2d_model None 态视为可切换（含成功
    尾部日志用 old_model_name 不解引用模型对象），下拉重选任意已登记模型即恢复。新模型
    入库须走登记（GUI 模型页扫描补录/导入流程），只放目录不登记=查表必失败（未登记名抛
    KeyError）。」
  - 泄漏面检查：`git status --porcelain` 确认无新增 untracked 数据面（.bak 类全落忽略规则；
    预期新增 untracked 仅 tests/test_live2d_fallback_guards.py）。
  - 覆写 docs/context/github-p3-public-h.report.md 为完整版：S1 红面/S3 绿面/S3b 折行
    diff 摘录、S4-S7 输出摘录、S5 若动了既有模型逐个列出、:397 偏离始末（v2 遗漏→v3 补
    全的裁决链）、遗留候选。
  - 不得 git add/commit。

### 运行测试（弱模型原样执行，不要修改；Git Bash 语法）

```bash
cd "C:\Coding\Application\Local-LLM-Voice-Avatar"
uv run --extra test python -m pytest -q 2>&1 | tail -40
```

如果退出码不是 0，只汇报：失败用例名、断言差异、最后 20 行 traceback。

## 6. 人工验收清单（1 项，五要素）

- **AI 为何做不了**：模型渲染比例与显示效果属主观观感（GAME_FACTOR=1.8 源于用户
  2026-09-11 目测校准），自动化截图无法裁决「比例合适」。
- **已备好的现场**：S0-S9 全绿后修复已就位。启动器=仓库根 `启动器.bat`（或加 debug 参数）；
  页面 http://localhost:12393/m/ 。
- **编号步骤**：① 启动器选角色 kazagumo（風雲）→ 启动服务；② 打开 /m/ 等待连接与模型
  加载；③ 看模型显示与比例（不溢出、不过小、不空白；参照吾妻观感）；④ 顶栏模型下拉确认
  fengyun_4 与 rangbaer_5 均在列表；⑤ 关闭服务。
- **通过/失败判定**：连接成功（无反复重连）、模型可见且比例可接受、下拉含两个新模型名
  → 通过；任一不成立 → 失败并记录现象。
- **预计耗时**：3 分钟。
