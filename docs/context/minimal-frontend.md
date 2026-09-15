# 极简自研前端（frontend-minimal/）· 总入口

背景：现有前端功能大量冗余（用户不用麦克风/群聊/聊天历史/配置切换 UI），
且需要支持 Spine 模型（现有 Cubism 专属前端无法加载）。决定从零写极简前端，
起步只做基础功能，架构保留扩展性。

## 分册索引

| 分册 | 收录内容 |
|------|----------|
| [minimal-frontend-foundation.md](minimal-frontend-foundation.md) | 阶段一：工程/构建/WS 协议子集/音频队列；阶段三：聊天历史 + 口型同步 |
| [minimal-frontend-live2d.md](minimal-frontend-live2d.md) | 阶段四：手势互动/目光跟随/心跳保活；stage2：参数驱动引擎；stage3：一键复位 |
| [minimal-frontend-spine.md](minimal-frontend-spine.md) | 阶段二：Spine 渲染 |
| [minimal-frontend-model-switch.md](minimal-frontend-model-switch.md) | stage4：同角色切换 Live2D 模型（预留 stage5 与契约候选落点） |

## 遗留与后续

**遗留**：
- mao_pro 表情的肉眼视觉验收未完成（管线已验证：expressions[0] 正确传入、
  表情文件 exp_08 按需加载成功）；下次起服务后发一条带情绪的消息看效果即可
- 联调时出现 TTS 120s 超时（GPU 100% 被 Ollama+GPT-SoVITS 争用），
  属已知环境性能问题，与前端无关
- 默认角色 zh_米粒（xinnong_6）无表情文件，表情验证需切 mao_pro
  （`switch-config` file=mao_pro.yaml）
- 两个 cutscene 模型只有环境循环动画，emotionMap 的映射（joy→loop_2 等）
  只是占位；等有带表情动画的 Spine 模型再补有意义的映射

Spine 接手要点见 minimal-frontend-spine.md；当前无待启动阶段。后续可考虑：
- 有带表情动画的 Spine 模型后补全 emotionMap 映射
