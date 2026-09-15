# 极简前端 · Spine 渲染

> 拆分自 minimal-frontend.md（2026-09-15）。总入口与遗留 → minimal-frontend.md；兄弟分册：基础管线 →
> minimal-frontend-foundation.md、Live2D → minimal-frontend-live2d.md、模型切换 → minimal-frontend-model-switch.md

**阶段二已完成**（Spine 渲染，2026-09-11）：

- 模型：`Spine-models/`（注意大写 S，与用户放入的目录一致）下的
  cutscene_char061404 / cutscene_char067603，均为 **Spine 4.1 格式**
  （.skel 二进制头版本号 4.1.-），过场 rig，动画只有 loop/loop_2/
  loop_water/cut_A/cut_B 系列
- 运行时选型：**@esotericsoftware/spine-webgl@4.1.56（精确锁定）**。
  弃用原计划 spine-pixi（要求 pixi v8，与 L2D 的 v7 冲突）；
  spine-webgl 用独立 canvas + WebGL，与 pixi 零冲突。**版本必须与
  skel 格式匹配**，4.3 运行时读不了 4.1 skel
- `server.py` 挂载 `/Spine-models`（目录存在才挂）；model_dict.json 已登记
  两个模型（emotionMap 的值 = **Spine 动画名**，复用后端关键词管线，
  前端把 expressions[0] 当动画播放）
- `src/renderer/spine.ts`：SpineRenderer，main.ts 按 url 后缀分流
  （`.skel` → Spine，否则 Live2D），切换类型时销毁旧渲染器释放上下文
- 相机适配：按「待机动画首帧」的**网格顶点实算 AABB**（SkeletonData 的
  x/y/w/h 含未显示的场景件，偏大；ClippingAttachment 要排除）居中并
  zoom = max(W/屏宽, H/屏高) / 0.9
- ⚠️ **spine OrthoCamera 语义**：可见世界尺寸 = viewport × zoom
  （zoom 越大看得越广，与 pixi/常识相反）
- ⚠️ **最大的坑**：gl.viewport 永远是 WebGL 上下文创建时 canvas 的默认
  300×150，spine 运行时不会更新；必须每帧/尺寸变化时手动
  `gl.viewport(0,0,canvas.width,canvas.height)`，否则画面缩成左下角一小块
- AssetManager 用 pathPrefix='' + 完整 URL（拼 pathPrefix 会出双斜杠 404）
- ManagedWebGLRenderingContext 没有 dispose()：换模型时直接丢弃旧 canvas 由
  GC 回收 WebGL 上下文
- 表情验证通过：setExpression('loop_2') → 播完 complete 回调自动回待机；
  真实对话 LLM 输出 [开心]/[joy]（日志 306 次 joy + 109 次开心）→
  动画切换生效；字幕中关键词被后端剔除
- 联调用 `characters/spine_test.yaml`（edge_tts，避免起 GPT-SoVITS）
- **角色切换下拉**（右上角）：连接后发 `fetch-configs`，收 `config-files`
  （`[{filename, name}]`，name 即 character_name）；选择后发
  `switch-config {file}`，服务端推新的 `set-model-and-conf`，前端按
  conf_name 同步选中项并清空音频队列/字幕。切 Live2D ↔ Spine 双向验证通过
- ⚠️ **/m 必须带尾斜杠才 404 之外可用**：Starlette 不为 mount 自动补斜杠，
  server.py 已加 `/m` → `/m/` 307 重定向
- **聊天记录含用户气泡**：前端把用户发送的消息也加进字幕区（右侧蓝色
  `.sentence.mine`），与 AI 句子（左侧）共存，保留最近 8 条
- **启动器前端选择**（v2.7）：服务页「自动打开浏览器」旁新增下拉
  原版前端 / 极简前端，存 `launcher_config.json` 的 `frontend_choice`
  （default/minimal，默认 minimal），「立即打开界面」与自动打开共用；
  改 launcher 代码需重启启动器（bat 直跑 .py 无需打包）
