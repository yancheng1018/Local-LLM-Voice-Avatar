# github-p3-public-h · 新模型登记缺口修复批（roadmap v1.0.1 #8）· spec v2

> v1 经 /grill-spec 拷打修订（2026-10-08）：取证工作流 11 条偏差 + 主会话复算 1 条（共 12 处
> 修正，详见 v1 与偏差清单工件；本版为完整规格，弱模型只读这一份施工，v1 作废）。
> 纪律：未经用户确认不 git add/commit；测试失败只能修实现或停下汇报，不得放宽断言。
> **全局前提：所有命令块按 Git Bash 语法书写（heredoc/管道/tail），2026-10-08 实证在本仓
> ZCode Bash 工具下可原样跑通；若实施会话 shell 为 cmd/PowerShell，heredoc 块须改等价
> python -c 单行并在报告注明改写，不得静默换语义。所有命令均在仓库根
> `C:\Coding\Application\Local-LLM-Voice-Avatar` 执行。**

## 0. 背景与根因（一段）

新增模型 fengyun_4/rangbaer_5 未登记本机 active 表 `model_dict.local.json`（42 条，含
wuqi_3 不含两新模型；active 解析规则=同名兄弟 `.local` 整份取代基准，
`src/open_llm_vtuber/live2d_model.py:203-212`）。kazagumo 角色卡引用 fengyun_4 →
`service_context.py:335-342` init_live2d 容错把 live2d_model 留 None 继续 → 每个 WS 连接在
`websocket_handler.py:197` 无守卫解引用 `None.model_info` 崩掉（表现为「服务无法启动」）。
下拉缺模型=同一张表缺登记。修复=①补录两条目（含 idle 别名组与 kScale 回填）②守卫 3 处
None 解引用兑现「proceed without Live2D」容错。

**异常类型事实（v2 修正）**：`Live2dModel` 对未登记名抛 `KeyError`
（live2d_model.py:115-119，:117 raise），不是 ValueError。

两疑点闭环（roadmap #8 条目「plan 首核」）：
- rangbaer_5 不在 active 表：已实证（2026-10-08，grep False/False）。
- 日志 `live2d_model_names=[]`：kazagumo 卡未配置 allowlist 字段，[] = 未配置 →
  `resolve_allowed_model_names()` 回退全局名单（docs/context/minimal-frontend-model-switch.md
  stage5 语义），日志打印的是原始字段值，非缺陷，不处理。

**v2 拷打取证钉定的事实（2026-10-08 实跑）**：
- 全量基线 `uv run --extra test python -m pytest -q` 实跑 **200 passed**（kazagumo.yaml 已在
  盘）；本批改动前基线全绿。
- 两源文件 ruff format --check 与 ruff check **双 clean**；但 `ruff format --check tests/`
  有两个既有脏文件（test_publish_facade.py、test_repo_privacy_guard.py，属已登记遗留格式债，
  本批不碰）。
- kScale 只读复算（scripts/fit_live2d_scale.py 确定性）：mao_pro 复算 0.5、wuqi_3 复算
  0.063，均与表内现值一致；fengyun_4 期望 **0.0621**（ppu 380.95，画布 8000×8000，游戏系
  乘 GAME_FACTOR 1.8）、rangbaer_5 期望 **0.0532**（ppu 326.53，同 8000×8000）。

## 1. 修改文件清单（含行数预检，spec-writing §5）

| # | 文件 | 改动 | 行数预检 |
|---|------|------|---------|
| 1 | `src/open_llm_vtuber/websocket_handler.py` | :197 行内守卫（表达式替换，format 后折为 3-4 行属合法重排） | 现 722 行（存量超标技术债）；增行≤3 |
| 2 | `src/open_llm_vtuber/service_context.py` | :350、:712 两处行内守卫（同上） | 现 751 行（存量超标）；增行≤6 |
| 3 | `tests/test_live2d_fallback_guards.py` | 新建（7 用例） | 预检 ~162 行 ≤200，逐块累加见 §4 |
| 4 | `model_dict.local.json` | 补录 2 条目 + 各回填 kScale；备份为 `model_dict.local.json.bak` | 数据文件；本体与 `.bak` 均被 gitignore（.gitignore:32/:33，check-ignore 实证）不入库 |
| 5 | `live2d-models/fengyun_4/fengyun_4.model3.json`、`live2d-models/rangbaer_5/rangbaer_5.model3.json` | 脚本加精确 `Idle` 别名组（纯数据） | live2d-models/ 整目录被忽略（.gitignore:11 命中，含脚本生成的 .bak），不入库 |
| 6 | `docs/context/minimal-frontend-model-switch.md` | 末尾（紧随 stage6 节，:41-48）追加 1 条 None 降级契约 bullet（~5 行） | 现 **48** 行 +5，余量足 |

不改动：kazagumo.yaml（用户卡，untracked 保持，不 git add）；model_dict.json（基准表，
test_model_dict_base_public_trimmed 钉死仅 mao_pro，绝不触碰）；.gitignore；前端任何文件。
**唯一性校验语义（v2 修正）**：test_character_identity_unique_on_disk
（tests/test_characters_manifest.py:62-72）用 `CHARACTERS_DIR.glob("*.yaml")` 遍历**磁盘全部
卡片**（含 untracked 的 kazagumo.yaml），即刻生效——「風雲」无重名，基线实测绿，无需动作；
git tracked 与否只影响 test_demo_character_tracked_and_valid（:48）。

## 2. 守卫点精确规格（3 处改 + 1 处论证不改）

改法均为行内表达式替换，函数签名不变；替换行超 ruff 88 列（132/102 字符），S3b 对触碰
文件跑 ruff format 折行属预期，**静态断言 ⑥ 的正则空白不敏感（\s*）已兼容折行**：

- **websocket_handler.py:197**（`_send_initial_messages`，class WebSocketHandler:94）：
  `"model_info": session_service_context.live2d_model.model_info,`
  →
  `"model_info": session_service_context.live2d_model.model_info if session_service_context.live2d_model else None,`
- **service_context.py:712**（`async def handle_config_switch` 内 set-model-and-conf 发送块）：
  `"model_info": self.live2d_model.model_info,`
  →
  `"model_info": self.live2d_model.model_info if self.live2d_model else None,`
- **service_context.py:350**（`async def switch_live2d_model`，:344）：
  `if self.live2d_model.live2d_model_name == model_name:`
  →
  `if self.live2d_model is not None and self.live2d_model.live2d_model_name == model_name:`
  （None 态视为「非当前模型」，继续走 candidate 构造——与 stage6「重选任何模型一步恢复」
  哲学一致，docs/context/minimal-frontend-model-switch.md stage6 节。注意：candidate 构造
  :354 对未登记名抛 KeyError，上游 WS handler :666-675 except Exception 捕获后回 error 消息，
  语义自洽）

**论证不改**：websocket_handler.py:682（模型切换成功后发送点）。到达该行必经
`context.switch_live2d_model(model_name)` 成功（:666-675 失败即 except→error→return），
成功路径已把 self.live2d_model 置为非 None candidate（service_context.py:368），None 不可达。
执行层不得在此「顺手」加守卫。

**前端契约依据（已实证，勿改前端）**：main.ts:83-89 对 `model_info` 空值现成降级
（`if (!modelInfo?.url) ui.setStatus('未配置模型', true)`），后端发 `null` 即可。
history.ts:7 的历史初始化挂在 set-model-and-conf 上，消息照发不省略。

## 3. 断言面盘点（数据改动影响预判，v2 全部经独立复核）

| 现有测试 | 与本批关系 | 预期 |
|---|---|---|
| tests/test_characters_manifest.py:55 | 读基准 model_dict.json（只含 mao_pro） | 不触，绿 |
| tests/test_characters_manifest.py:62-72 唯一性 | 磁盘全卡即刻校验，「風雲」无重名（实测） | 不触，绿 |
| tests/test_repo_privacy_guard.py:29 | 断言 model_dict.local.json 被忽略 | 只编辑不入库，绿 |
| tests/test_live2d_model_data.py:69 `test_inuse_names_resolved_and_nonempty` | FULL_KNOWN ⊆ in_use，子集断言 | +2 条无影响，绿 |
| tests/test_live2d_model_data.py:84 `test_inuse_models_have_exact_idle_group` | 补录+kazagumo 卡使 fengyun_4 进 in_use，强校验精确 `Idle` 非空组 | 两新模型现仅小写 `idle` 组（实证）→ **不修必红**；S5 加别名组后绿 |
| tests/test_live2d_model_data.py:111 `test_mao_pro_entry_not_drifted` | 基准/本地 mao_pro 条目逐字段一致 | 只回填两条新条目（S6），mao_pro 条目字节不动，绿。**v2 修正**：复算实证 mao_pro=0.5 与现值一致（v1「全量 fit 必写 0.4994」论断作废）；不跑全量 fit 的理由降级为**最小 diff 原则**（避免整文件重写的无关 diff 面），非防红 |
| frontend-minimal/tests/test_model_load_guards.py:60 | 读基准表 | 不触，绿 |
| frontend-minimal/tests/test_live2d_model_switch.py（:57-131 三用例 + :324-342 运行时 allowlist，v2 修正范围） | 全部 tmp_path fixture+显式路径实参，不触本机表 | 不触，绿 |

## 4. 新建测试文件规格 `tests/test_live2d_fallback_guards.py`

写法约束（v2 补强）：
- 全程不依赖 pytest-asyncio 插件——async 调用一律 `asyncio.run(...)` 包在同步测试函数内。
- 实例构造用 `Cls.__new__(Cls)` 绕开重构造器。**v2 事实**：ServiceContext 属性全部在
  `__init__` 实例级赋值、无类级默认（service_context.py:59-89，live2d_model 在 :64），
  `__new__` 实例**没有**这些属性——凡被测路径触碰的属性（live2d_model、character_config、
  agent_engine、system_prompt、construct_system_prompt 等）必须在用例输入里**逐个显式挂上**；
  WebSocketHandler 同理（send_group_update 挂 async 空操作，绕开 chat_group_manager 依赖，
  真体在 websocket_handler.py:379）。
- 不依赖网络/引擎/GUI；导入项目模块用 `src.` 前缀（uv 布局约定，AGENTS.md）。
- 锚定异常类型用 KeyError（不是 ValueError）。

行数预检（逐块累加）：docstring+imports ~22；公共 Fixture（FakeWS/StubAgent）~26；用例
① ~13、② ~22、③ ~14、④ ~24、⑤ ~14、⑥ ~13、⑦ ~14；合计 ≈162 ≤200。

| # | 用例名 | 输入 | 预期/断言点 | 现状 |
|---|--------|------|------------|------|
| ① | `test_init_live2d_unknown_model_leaves_none` | `ctx = ServiceContext.__new__(ServiceContext)`；**显式挂 `ctx.live2d_model = None`** 与 `ctx.character_config = SimpleNamespace()`；`ctx.init_live2d("no_such_model_xyz")` | 不抛异常；`ctx.live2d_model is None`（失败路径不赋值，:337-342 仅成功分支 :338 赋值；本机走 .local 表、公开克隆走基准表，该名两环境均不存在） | 绿（锁契约） |
| ② | `test_send_initial_messages_none_model_sends_null_model_info` | `handler = WebSocketHandler.__new__(WebSocketHandler)`；挂 `handler.send_group_update` 为 async 空操作；FakeWS 收集 send_text；`ctx=SimpleNamespace(live2d_model=None, character_config=SimpleNamespace(character_name="風雲", conf_uid="kazagumo_001"))`；`asyncio.run(handler._send_initial_messages(ws, "uid-1", ctx))` | 不抛异常；恰 3 条发送（full-text / set-model-and-conf / control start-mic）；第 2 条 json：`type=="set-model-and-conf"`、`model_info is None`、`conf_name=="風雲"`、`conf_uid=="kazagumo_001"`、`client_uid=="uid-1"` | **红→绿**（现 :197 None 解引用 AttributeError） |
| ③ | `test_send_initial_messages_with_model_passes_model_info` | 同②但 live2d_model=SimpleNamespace(model_info={"name":"mao_pro","url":"/x"}) | 第 2 条 `model_info == {"name":"mao_pro","url":"/x"}`（防过度守卫截断正常路径） | 绿 |
| ④ | `test_switch_live2d_model_from_none_state_recovers` | ServiceContext.__new__；**显式挂** live2d_model=None、character_config=SimpleNamespace(live2d_model_name="fengyun_4", persona_prompt="p", language="ja", human_name="指揮官")、agent_engine=StubAgent（记录 set_live2d_model/set_system）、system_prompt="old"、`construct_system_prompt = async def(persona_prompt, language="", human_name=""): return "new-prompt"`（实例属性遮蔽方法）；目标 `"mao_pro"`（基准与 .local 两环境均含；pytest 从仓库根跑，Live2dModel 默认 cwd 相对路径解析到 active 表）；`asyncio.run(ctx.switch_live2d_model("mao_pro"))` | 不抛异常；`ctx.live2d_model` 为 Live2DModel 实例且 `live2d_model_name=="mao_pro"`；`character_config.live2d_model_name=="mao_pro"`；StubAgent 收到 set_live2d_model(candidate) 与 set_system("new-prompt") | **红→绿**（现 :350 None.live2d_model_name AttributeError） |
| ⑤ | `test_switch_live2d_model_bad_name_from_none_raises_state_unchanged` | 同④但目标 `"no_such_model_xyz"`，`pytest.raises(KeyError)`（**v2 修正**：live2d_model.py:117 抛 KeyError） | 守卫落地后：candidate 构造（:354）先于任何状态变更抛 KeyError；`ctx.live2d_model is None` 不变、`character_config.live2d_model_name=="fengyun_4"` 不变 | **红→绿**（守卫前 :350 先抛 AttributeError，非 KeyError，用例红） |
| ⑥ | `test_handle_config_switch_model_info_guard_static` | 读 `src/open_llm_vtuber/service_context.py` 源码文本；`re.search(r'"model_info":\s*self\.live2d_model\.model_info\s+if\s+self\.live2d_model\s+else\s+None', src)` | 命中（空白不敏感正则兼容 format 折行；书写纪律见 docs/context/minimal-frontend-model-switch.md:16-20） | **红→绿** |
| ⑦ | `test_switch_model_send_site_682_unreachable_none_documented` | 读 websocket_handler.py 源码；断言 `re.search(r'await context\.switch_live2d_model\(model_name\)', src)` 且其后 20 行内含 `"Live2D 模型切换失败：模型加载失败"` | 命中（锁定 :682 非 None 可达性论证前提：失败路径必 return） | 绿 |

**S1 红面预期（v2 修正）**：②④⑤⑥ 红，①③⑦ 绿。

## 5. 实施步骤（S0-S10；标〔工〕=工具可完成原样执行，〔判〕=需要判断）

- **S0〔工〕基线实跑**：拷打取证实跑 2026-10-08 = **200 passed**（kazagumo 卡在盘）。
  现场复跑确认无漂移：
  ```bash
  cd "C:\Coding\Application\Local-LLM-Voice-Avatar"
  uv run --extra test python -m pytest -q 2>&1 | tail -5
  ```
  若非全绿 → 停下汇报红面，不得继续（新增收集数以实跑为准，禁算术推算）。
- **S1〔判〕写测试**：按 §4 新建 tests/test_live2d_fallback_guards.py，跑
  `uv run --extra test python -m pytest tests/test_live2d_fallback_guards.py -q 2>&1 | tail -20`
  取证红面（预期 ②④⑤⑥ 红，①③⑦ 绿；分布不符 → 停下汇报，勿改断言凑数）。
- **S2〔判〕落守卫**：按 §2 精确改 3 处（只改列出的表达式，不动 :682）。
- **S3〔工〕守卫绿证**：重跑 S1 命令 → 7 用例全绿。
- **S3b〔工〕格式与 lint（v2 新增）**：只对 3 个触碰文件执行，**禁止全仓 ruff format .**
  （tests/ 两既有脏文件 test_publish_facade/test_repo_privacy_guard 属已登记遗留债）：
  ```bash
  uv run ruff format src/open_llm_vtuber/websocket_handler.py src/open_llm_vtuber/service_context.py tests/test_live2d_fallback_guards.py
  uv run ruff check src/open_llm_vtuber/websocket_handler.py src/open_llm_vtuber/service_context.py tests/test_live2d_fallback_guards.py
  uv run --extra test python -m pytest tests/test_live2d_fallback_guards.py -q 2>&1 | tail -5
  ```
  预期：format 折守卫行（合法重排，增行≤9）；check 0 错误；测试仍全绿（⑥ 正则空白不敏感）。
- **S4〔工〕备份+补录登记**（v2：备份名改用被 .gitignore:33 覆盖的 `.bak`）：
  ```bash
  cd "C:\Coding\Application\Local-LLM-Voice-Avatar"
  cp model_dict.local.json model_dict.local.json.bak
  git check-ignore model_dict.local.json.bak || echo "不被忽略，停下汇报"
  uv run python - <<'EOF'
  import json
  from pathlib import Path
  p = Path("model_dict.local.json")
  entries = json.loads(p.read_text(encoding="utf-8"))
  known = {e["name"] for e in entries}
  def entry(name):
      # 模板=GUI 启动器登记模板 launcher/OpenLLMVTuber_GUI.py:1965-1977，
      # url 推导同 :1956；字段口径同 wuqi_3 既有条目
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
  预期输出 `entries: 44`（幂等：重复执行不加条）。check-ignore 无输出即被忽略（正常）。
- **S5〔工〕Idle 别名组**（契约：前端硬编码精确 `Idle`/`Talk`，大小写完全一致才播放；
  脚本幂等、逐文件整字节备份 .bak 到被忽略的 live2d-models/ 内、只加别名组不改既有键）：
  ```bash
  uv run python scripts/fix_live2d_idle_groups.py
  ```
  预期输出仅 fengyun_4、rangbaer_5 新增 `Idle`（两者无小写 talk 变体，Talk 跳过）；
  若报告还动了其他既有模型 → 如实记录到 report（属契约对齐，非本批缺陷），继续。
- **S6〔工〕kScale 两条回填**（v2：钉定期望值 fengyun_4=0.0621、rangbaer_5=0.0532；
  不跑全量 `uv run python scripts/fit_live2d_scale.py`——非防红（复算实证 mao_pro=0.5
  一致），为最小 diff 原则，只回填两条）：
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
- **S7〔工〕数据终验**（名单构造口径：`load_model_dict("model_dict.json")` 经
  resolve_model_dict_path 取 active=.local，与前端下拉 list_frontend_models 同源，
  live2d_model.py:203-212/:215-244）：
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
- **S8〔工〕全量回归**：命令见 §6 测试命令块；预期=200（S0 实跑数）+ 新文件 7 用例
  （收集数以实跑为准）全绿、0 failed；`test_mao_pro_entry_not_drifted` 必须仍绿。
- **S9〔判〕文档、泄漏面检查与报告**：
  - docs/context/minimal-frontend-model-switch.md 末尾（紧随 stage6 节）追加：
    「**live2d_model=None 降级契约（github-p3-public-h）**：init_live2d 容错失败后
    live2d_model=None，连接不拒、降级服务。所有 set-model-and-conf 发送点
    （_send_initial_messages / handle_config_switch）守卫 None、model_info 发 null——前端
    main.ts 对空值现成降级（未配置模型）；switch_live2d_model None 态视为可切换，下拉
    重选任意已登记模型即恢复。新模型入库须走登记（GUI 模型页扫描补录/导入流程），只放
    目录不登记=查表必失败（未登记名抛 KeyError）。」
  - **泄漏面检查（v2 新增）**：`git status --porcelain` 确认无新增 untracked 数据面
    （.bak 类须全部落在忽略规则内；预期新增 untracked 仅 tests/test_live2d_fallback_guards.py）。
  - 写 docs/context/github-p3-public-h.report.md：红绿取证（S1 红面/S3 绿面/S3b 折行 diff
    摘录）、S4-S7 输出摘录、S5 若动了既有模型逐个列出、遗留候选（如有）。
  - 不得 git add/commit（用户确认后另行处理）。

### 运行测试（弱模型原样执行，不要修改；Git Bash 语法）

```bash
cd "C:\Coding\Application\Local-LLM-Voice-Avatar"
uv run --extra test python -m pytest -q 2>&1 | tail -40
```

如果退出码不是 0，只汇报：失败用例名、断言差异、最后 20 行 traceback。

## 6. 人工验收清单（1 项，五要素）

- **AI 为何做不了**：模型渲染比例与显示效果属主观观感（GAME_FACTOR=1.8 源于用户
  2026-09-11 目测校准），自动化截图无法裁决「比例合适」。
- **已备好的现场**：本规格 S0-S9 全绿后修复已就位。启动器=仓库根 `启动器.bat`（或加
  debug 参数保留控制台）；页面 http://localhost:12393/m/ 。
- **编号步骤**：① 启动器选角色 kazagumo（風雲）→ 启动服务；② 打开 /m/ 等待连接与
  模型加载；③ 看模型显示与比例（不溢出、不过小、不空白；参照吾妻观感）；④ 顶栏模型
  下拉确认 fengyun_4 与 rangbaer_5 均在列表；⑤ 关闭服务。
- **通过/失败判定**：连接成功（无反复重连）、模型可见且比例可接受、下拉含两个新模型名
  → 通过；任一不成立 → 失败并记录现象。
- **预计耗时**：3 分钟。
