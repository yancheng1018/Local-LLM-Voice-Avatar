# spec-demo-gif · README 演示 GIF 录制与转制工序

> 2026-10-09 收尾升格为长期文档（原 github-p3-public-f.spec.v2.md；阶段已验收，README 增补部分已随实施落定，本文档核心价值=§3 录制/转制/降级工序与 §9 拍板口径）。

> 2026-10-09 审查裁决压缩：施工段（§0-§2、§4-§8）已应用为仓库 tip 的 README.md 与 tests/test_publish_facade.py 现行内容，仅留 §3 重录工序与 §9 拍板口径；原 414 行全文见 git 历史（github-p3-public-f.spec.v2.md）。

## 3. 演示 GIF 录制与转制工序（roadmap #9，无声 GIF 口径）

拍板口径（2026-10-08 用户）：出镜=角色 kazagumo（fengyun_4，舰船形象公开风险自担）；
形式=无声 GIF 入库；ASR 环节不展示（文字输入），TTS 仅驱动口型；**对话保持日语**
（人设真实，2026-10-08 拷打拍板）；镜头含调试栏/热区叠加层展示与 rangbaer_5 切换。

### R0 基线复核（工具可完成，必须最先做）

```bash
uv run --extra test python -m pytest -q 2>&1 | tail -15
```

应 `211 passed`（2026-10-09 终态基线）；红面或计数漂移 → 停报。

### R1 环境准备（AI 备现场；GSV 启动属「需要判断」）

1. 起 GPT-SoVITS API：按 gui-launcher.md 既有链路（GUI 一键启动或
   `python scripts/gpt_sovits/start_gsv_api.py --root <GSV根目录>`，根目录为用户
   环境既有，规格不预设路径；适配器在位且曾执行，拷打期取证）。
2. 起主服务：`uv run run_server.py`（ollama 服务与模型为用户环境常驻）。
3. 切角色到 kazagumo：前端发送 `switch-config` file=kazagumo.yaml（源级锚
   `frontend-minimal/src/main.ts:367`；文档先例 minimal-frontend.md:23-24）；机制
   不可用则按 docs/context/config-system.md 临时改 conf.yaml 指向 kazagumo.yaml 后
   重启服务（conf_uid 当前为 'mao_pro_001'，conf.yaml:33——此步必做）。录制完不
   改回（后续人工验收还要看）。
4. 冒烟判据：/m/ 一轮文字对话成功（流式回复 + TTS 出声 + 口型动）；调试栏与热区
   叠加层初始关闭，按镜头脚本 E 开关（本阶段要求入镜展示，2026-10-08 用户拍板）。

### R2 录制（AI 自动化优先）

录屏（桌面仅留浏览器窗口，素材输出仓库外；时长上限 120s——A-G 预估 55-65s，
留 LLM 长回复与切换余量）：

```bash
ffmpeg -y -f gdigrab -framerate 30 -i desktop -pix_fmt yuv420p -t 120 /tmp/github-p3-public-f_raw.mp4
```

浏览器自动化（会话内 browser-use 技能）在录制窗口内按镜头脚本驱动
（LLM 回复内容生成式不可预设，断言只锚「回复发生+口型动」）：

| 镜头 | 动作 | 预期画面 |
|------|------|---------|
| A 待机 | 打开 `http://127.0.0.1:12393/m/` 静置 4s | 風雲待机呼吸+眨眼 |
| B 提问 | 文字输入 `こんにちは、風雲さん。` 发送 | 消息上屏 |
| C 回答 | 等待回复完成（约 15-25s） | 流式逐字上屏 + TTS 口型同步 |
| D 触摸 | 画布中部按住水平缓拖 ~100px 放开 | 步进链位移+回弹 |
| E 调试栏 | 开调试栏与热区叠加层 → 热区框/参数可见 → 隔 ≥2s 点按热区 1 次（触发 touch.json 动作，6 规则）→ 关调试栏 | 热区高亮框+点按触发动作（动态演示改动总览表 #4 行） |
| F 切换（可选） | 切换皮肤到 rangbaer_5 → 待机 2s → 切回 fengyun_4 | 模型切换动效（rangbaer_5 已登记可直接选中；流程顺滑才录） |
| G 复位 | 点一键复位，静置 3s | 回待机 |

规避项：点按不连续推进动作链超过 2 步（TouchBody 链几何退化区，hotzone-arch
遗留①）；调试栏仅镜头 E 开启，开关动作各留 ~1s 便于观感。

### R3 转制 GIF（工具可完成）

先审素材定选段（`ffprobe /tmp/github-p3-public-f_raw.mp4` 取时长；抽帧核对 A-G
起止），再转制：

```bash
ffmpeg -y -ss <A起> -to <G止> -i /tmp/github-p3-public-f_raw.mp4 -vf "fps=12,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" -loop 0 docs/assets/demo.gif
```

体积 >10MB → 依次降 fps=10 / scale=720 / 缩短选段重转，直至 ≤10MB（守卫测试硬门）。

### R4 失败降级（人工录制，仅当 R2 自动化失败）

自动化同一故障 ≥3 次（动效不渲染 / 录屏黑屏 / 交互不可驱动）→ 停报附尝试记录，
转人工（AI 已备好现场：服务与页面就绪 `http://127.0.0.1:12393/m/`；人只做：
①Win+Alt+R 开始录制 ②按镜头 B-E 脚本操作 ③再按 Win+Alt+R 停止；判定=素材含完整
回复+拖拽+调试栏热区点按画面；耗时约 5 分钟）。转制 R3 仍由 AI 完成。

## 9. 遗留吸收与裁决落档

遗留吸收（两条已从 current-work.md 移除，处置记录）：

- [github-p3-public-d] 弱网注记候选：①ollama qwen2.5 ~4.7GB → S3-1；②ASR 999MB +
  hf-mirror 预置跳过 → S3-2；③「ASR 就绪无专属日志行」排障注记未采纳独立条目——
  核心信息已由 S3-2「下载完成前语音对话不可用」承载，日志行级细节未取证不写。
- [github-p3-public-e] 测试口径注记：→ S2 节尾 blockquote + test_readme_test_count_note。
  数字口径：主仓实跑 200→207（R-1 后），克隆 190+10（p3-public-e 记录）。

规划与用户裁决落档：

- roadmap #9 并入本阶段：2026-10-08 用户指示；原「public 后补挂」作废；GIF 入库的
  commit+push 仍须用户确认（#9 既有口径，本规格不授权）。
- 出镜拍板（2026-10-08 用户）：私有舰船形象公开风险自担；无声 GIF 入库（≤10MB）；
  角色指定 kazagumo（fengyun_4，登记由 stage h 完成、touch.json 用户手修）。
- 追加拍板（同日用户）：R-1 授权规划会话顺手修复（fix_live2d_idle_groups.py
  fixed=2、全量 207 复绿，证据见 git 历史）；镜头 F 切换目标=rangbaer_5；新增调试栏+热区
  叠加层展示镜头 E（改动总览表 #4 行的动态演示位）。
- 拷打拍板（同日 /grill-spec 四项）：①演示对话保持日语（人设真实，README 中文读者
  可接受）；②测试口径注记接受写死数字+漂移风险（守卫只防删节不查真伪）；③docs/assets
  章程句扩充（兼收对外演示媒体）追认；④10 项表内容维持现稿。
- 「改动总览」节位置：放「## 基于上游的声明」之后（先声明 fork 关系再列差异）。
- README 行数不受 ≤100 约束：依据 repo-maintenance.md:149-154 检查清单口径。
- 10 项表内容浓缩自 AGENTS.md 目录速览/索引 + 各分册文档 + 现 README 核心特性；
  表内不提 l2d.su 逆向来源（内部知识，公开 README 不必要）；README 新增文本不含
  私有模型名（alt 文案用通用描述）。
