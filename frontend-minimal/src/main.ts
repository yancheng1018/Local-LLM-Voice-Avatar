import './style.css';
import { WSClient, defaultWsUrl } from './ws';
import { AudioQueue, type AudioMessage } from './audio';
import { UI } from './ui';
import { L2DRenderer } from './renderer/l2d';
import { SpineRenderer } from './renderer/spine';
import { HistoryManager } from './history';
import type { CharacterRenderer, ModelInfo } from './renderer/types';
import { TouchChain } from './renderer/l2d_touch';

const ui = new UI();

// 连续触摸递进链参数（复刻碧蓝航线：连点按编号推进 touch_idle，闲置重置，走完冷却）
const CHAIN_RESET_MS = 10000; // 闲置 10 秒后链从头开始
const CHAIN_COOLDOWN_MS = 60000; // 完整走完一轮后冷却 60 秒再重开

// 按模型 url 后缀分流：.skel → Spine（独立 WebGL canvas），否则 Live2D（pixi）。
// 两类渲染器互斥使用，切换时销毁旧的释放上下文。
const stage = document.getElementById('stage')!;

// 音量源先占位（audioQueue 在下方创建），构造后再回填
let getVolume: () => number = () => 0;
let renderer: CharacterRenderer = new L2DRenderer(stage, () => getVolume());
let touchDebugOn = false; // 热区可视化开关状态（换模型后需重申）
let debugPanelOn = false; // 调试栏开关状态（换 L2D 模型后需重申）
let currentLive2DModelName = ''; // 最近一次成功加载的 Live2D 模型名；加载失败时清空（服务端 set-model-and-conf 同步）

/** tapMotions 表 {动作组: 权重} 加权随机；组名可能为空串（mao_pro），null=无可用动作 */
function pickWeightedMotion(table: Record<string, number>): string | null {
  const entries = Object.entries(table).filter(([, w]) => w > 0);
  const total = entries.reduce((sum, [, w]) => sum + w, 0);
  if (entries.length === 0 || total <= 0) return null;
  let r = Math.random() * total;
  for (const [group, w] of entries) {
    r -= w;
    if (r <= 0) return group;
  }
  return entries[entries.length - 1][0];
}

function ensureRenderer(modelInfo: ModelInfo): CharacterRenderer {
  const wantSpine = modelInfo.url.endsWith('.skel');
  const isSpine = renderer instanceof SpineRenderer;
  if (wantSpine !== isSpine) {
    renderer.dispose();
    renderer = wantSpine
      ? new SpineRenderer(stage) // Spine 模型嘴为贴图切换式，不做口型同步
      : new L2DRenderer(stage, () => getVolume());
  }
  return renderer;
}

// AudioContext 需要用户手势后才能出声；发送即手势，届时 resume
const audioCtx = new AudioContext();

const ws = new WSClient(defaultWsUrl());
const audioQueue = new AudioQueue(audioCtx, (msg) => ws.send(msg), {
  onSentenceStart: (msg) => {
    ui.appendSubtitle(msg.display_text?.text ?? '');
    // 前端只消费 expressions[0]（与原前端一致）
    const expr = msg.actions?.expressions?.[0];
    if (expr !== undefined) renderer.setExpression(expr);
    // 说话伴随动作（模型缺 Talk 组时内部自动跳过）
    renderer.setAnimation('Talk');
  },
  onPlaybackComplete: () => {
    renderer.resetExpression();
    ui.setStatus('就绪');
    ui.setBusy(false);
  },
});
getVolume = () => audioQueue.volumeLevel;

const history = new HistoryManager(ws, ui);

// ---- 消息处理（websocket_handler.py 的协议子集）----

// 状态提示（"Connection established" / "Thinking..." 等）
ws.register('full-text', (data) => {
  ui.setStatus(String(data.text ?? ''));
});

ws.register('set-model-and-conf', (data) => {
  const modelInfo = data.model_info as ModelInfo | undefined;
  if (!modelInfo?.url) {
    ui.setStatus('未配置模型', true);
    return;
  }
  currentConfName = String(data.conf_name ?? modelInfo.name);
  // 同步角色下拉选中项（conf_name 即 config-files 里的 name）
  const select = document.getElementById('char-select') as HTMLSelectElement;
  if (select.options.length > 0) {
    for (const opt of Array.from(select.options)) {
      opt.selected = opt.textContent === currentConfName;
    }
  }
  ui.setStatus(`加载模型 ${modelInfo.name}…`);
  // 连接/重连/切角色后上下文都已重建，重新载入该角色的最新历史
  history.init();

  // 先确定渲染器实例（可能新建），再注入互动处理器与触摸链回调，避免赋值到旧实例
  const activeRenderer = ensureRenderer(modelInfo);
  ui.setLive2DModelEnabled(false); // load 完成前禁用，防止连续选择竞争

  // 手势互动：拖动 → touch_drag*；长按 → touch_special；单击头 → touch_head；
  // 单击身 → touch_idle 递进链（碧蓝航线连续触摸：按编号顺序推进，闲置重置，
  // 走完一轮后冷却）。tapMotions 热区表仅对有真实 HitAreas 的模型生效
  if (activeRenderer instanceof L2DRenderer) {
    // 递进链状态（index/时间戳跨交互保留；组列表每次交互时实时取——
    // 处理器赋值发生在新模型 load 完成前，当时取到的是上一个模型的组）
    const chain = { index: 0, lastAt: 0, exhaustedAt: 0 };
    // 规则驱动链：按模型名作用域持久化（链进度/冷却跨刷新与换模型保留）
    const touchChain = new TouchChain(`l2d-touch:${modelInfo.name}`);
    // 换模型时链从零开始
    chain.index = 0;
    chain.lastAt = 0;
    chain.exhaustedAt = 0;
    // 规则区交互门槛 + idle 回放组名需要链状态：注入只读回调（spec stage3 §3.2/§3.4）
    activeRenderer.actionAllowed = (n) => touchChain.isActionAllowed(n);
    activeRenderer.chainIdleIndex = () => touchChain.currentIndex;
    activeRenderer.chainStepIndex = (rid) => touchChain.stepIndex(rid);
    activeRenderer.resetTouchChain = () => touchChain.reset();
    const chainGroups = () =>
      activeRenderer
        .getMotionGroups()
        .filter((g) => /^touch_idle\d*$/.test(g))
        .sort(
          (a, b) =>
            parseInt(a.replace(/\D/g, '') || '0', 10) -
            parseInt(b.replace(/\D/g, '') || '0', 10),
        );

    activeRenderer.onInteraction = ({ kind, areas, region, rule }) => {
      const tm = modelInfo.tapMotions as
        | Record<string, Record<string, number>>
        | undefined;
      const groups = activeRenderer.getMotionGroups();
      const available = activeRenderer.getPlayableActionNames();
      const byPattern = (re: RegExp) => {
        const list = groups.filter((g) => re.test(g));
        return list.length ? list[Math.floor(Math.random() * list.length)] : null;
      };
      const play = (action: string | null, ruleId?: number) => {
        // playAction 按动作名索引匹配（组名/条目名/文件名），无命中为 no-op
        if (action !== null) void activeRenderer.playAction(action, ruleId);
      };

      // 播放门控（spec stage3 §3.4.1）：触摸动作播放期间只放行当前命中区自身规则链
      if (activeRenderer.isPlayingTouchAction) {
        if (rule && rule.id === activeRenderer.playingTouchRuleId) {
          play(touchChain.resolve(rule, kind, available), rule.id);
        }
        return;
      }

      // touch.json 规则热区命中（游戏同款数据）：交给 TouchChain 按 actionTrigger 类型
      // + ATA 白名单 + limitTime 冷却决定播什么（null=被拦截，不播）
      if (rule) {
        const param = String(rule.parameter ?? '');
        // 默认热区伪规则（spec stage3 §3.6）：Head/Special 直连 playAction 不进链；
        // Body 走 touch_idleN 编号递进链
        if (param === 'touchhead' || param === 'touchspecial') {
          play(param === 'touchhead' ? 'touch_head' : 'touch_special', rule.id);
          return;
        }
        if (param === 'touchbody') {
          const now = Date.now();
          if (now - chain.lastAt > CHAIN_RESET_MS) chain.index = 0; // 闲置太久重置
          if (chain.exhaustedAt && now - chain.exhaustedAt < CHAIN_COOLDOWN_MS) return;
          const idleList = chainGroups();
          if (idleList.length > 0) {
            const gname = idleList[chain.index % idleList.length];
            chain.index++;
            chain.lastAt = now;
            if (chain.index >= idleList.length) {
              chain.exhaustedAt = now; // 走完一轮，进入冷却
              chain.index = 0;
            }
            // 三字段链步进查找（spec stage6 §2.1）：parameter === 组名 | drawAbleName 驼峰化
            //（空 parameter 规则如 TouchIdleN）| action 含组名；走 TouchChain 自动应用
            // ATA.idle/enable/ignore 与 limitTime 冷却；找不到规则则直接 playAction(gname)
            const chainRule = activeRenderer.findChainRule(gname);
            const action = chainRule ? touchChain.resolve(chainRule, kind, available) : gname;
            if (action !== null) play(action, chainRule?.id);
          } else {
            play(byPattern(/^touch_body$/) ?? byPattern(/^touch_/));
          }
          return;
        }
        play(touchChain.resolve(rule, kind, available), rule.id);
        return;
      }
      // 有规则数据的模型：点在规则区域之外（如场景背景）不反应（游戏同款）
      if (activeRenderer.hasTouchRules) return;

      if (kind === 'drag') {
        play(byPattern(/^touch_drag\d*$/) ?? byPattern(/^touch_/));
        return;
      }
      if (kind === 'longpress') {
        play(
          byPattern(/^touch_special$/) ??
            byPattern(/^touch_(head|body)$/) ??
            byPattern(/^touch_/),
        );
        return;
      }

      // 单击：tapMotions 命中真实热区（键名非空才视为定向热区）
      for (const area of areas) {
        if (area && tm?.[area]) {
          play(pickWeightedMotion(tm[area]));
          return;
        }
      }

      // 无热区命中：按头/身区域
      if (region === 'head') {
        play(
          byPattern(/^touch_head$/) ??
            byPattern(/^touch_special$/) ??
            byPattern(/^touch_/),
        );
        return;
      }

      // 身体：递进链（连续触摸按编号推进）
      const now = Date.now();
      if (now - chain.lastAt > CHAIN_RESET_MS) chain.index = 0; // 闲置太久重置
      if (chain.exhaustedAt && now - chain.exhaustedAt < CHAIN_COOLDOWN_MS) {
        // 链走完后的冷却期：改播普通身体反应
        play(byPattern(/^touch_body$/) ?? byPattern(/^touch_/));
        return;
      }
      if (chainGroups().length > 0) {
        const idleList = chainGroups();
        play(idleList[chain.index % idleList.length]);
        chain.index++;
        chain.lastAt = now;
        if (chain.index >= idleList.length) {
          chain.exhaustedAt = now; // 走完一轮，进入冷却
          chain.index = 0;
        }
        return;
      }
      // 没有 touch_idle 链：普通身体反应
      play(
        byPattern(/^touch_body$/) ??
          byPattern(/^touch_drag\d*$/) ??
          byPattern(/^touch_/),
      );
    };
  }

  activeRenderer
    .load(modelInfo)
    .then(() => {
      // 换模型/换渲染器实例后重申开关状态（新实例的叠加层默认关闭）
      renderer.setTouchDebug?.(touchDebugOn);
      renderer.setDebugPanel?.(debugPanelOn);
      ui.setStatus(`已连接 · ${String(data.conf_name ?? modelInfo.name)}`);
      ui.setLive2DModelEnabled(true);
      currentLive2DModelName = modelInfo.name; // 加载成功才视为当前模型
      // 任何角色切换/模型切换/重连后刷新列表与 current（本 handler 不回发 WS，无循环）
      ws.send({ type: 'fetch-live2d-models' });
    })
    .catch((e) => {
      console.error('Model load failed:', e);
      const msg = e instanceof Error ? `${e.message}` : String(e);
      ui.setStatus(`模型加载失败：${modelInfo.name} · ${msg}`, true);
      ui.setLive2DModelEnabled(true); // 让用户能重试选择
      currentLive2DModelName = ''; // 旧模型已被销毁、舞台为空：如实清空，重选任何模型都会重新走 switch
    });
});

ws.register('control', (data) => {
  const text = String(data.text ?? '');
  if (text === 'conversation-chain-start') {
    turnActive = true;
    ui.setStatus('思考中…');
    ui.setBusy(true);
  } else if (text === 'conversation-chain-end') {
    turnActive = false;
    ui.setStatus('就绪');
    ui.setBusy(false);
    renderer.resetExpression();
  }
  // start-mic 等与极简前端无关，忽略
});

ws.register('audio', (data) => {
  audioQueue.enqueue(data as unknown as AudioMessage);
});

// 全部音频合成完毕：播完最后一句后由 AudioQueue 回 frontend-playback-complete
ws.register('backend-synth-complete', () => {
  audioQueue.markSynthComplete();
});

ws.register('error', (data) => {
  ui.setStatus(`错误：${String(data.message ?? '未知错误')}`, true);
});

// 角色列表（下拉数据源）；conf_name 与列表项 name 同源（均为 character_name）
let currentConfName = '';
ws.register('config-files', (data) => {
  const configs = (data.configs as { filename: string; name: string }[]) ?? [];
  ui.setCharacters(configs, currentConfName);
});

// 可切换的 Live2D 模型列表（不含 Spine）；本 handler 不发任何 WS，避免循环
ws.register('live2d-models', (data) => {
  const models = (data.models as { name: string }[]) ?? [];
  const current = String(data.current ?? currentLive2DModelName);
  ui.setLive2DModels(models, current);
});

// ---- 交互 ----

// 本轮对话是否进行中（服务端被打断后不补发 chain-end，必须本地维护此状态）
let turnActive = false;

ui.onSend = (text) => {
  if (audioCtx.state === 'suspended') void audioCtx.resume();
  // 上一轮还在进行时先打断（服务端同一 client 不支持并发对话）
  if (turnActive || audioQueue.busy) {
    audioQueue.interrupt();
    ws.send({ type: 'interrupt-signal', text: '' });
  }
  ui.appendUserMessage(text);
  turnActive = true;
  ui.setBusy(true);
  ws.send({ type: 'text-input', text });
};

ui.onInterrupt = () => {
  audioQueue.interrupt();
  renderer.resetExpression();
  turnActive = false;
  ui.setBusy(false);
  ui.setStatus('已打断');
  ws.send({ type: 'interrupt-signal', text: '' });
};

ui.onSwitchCharacter = (filename) => {
  // 切换角色：清掉当前轮次的残留（音频/状态），服务端会推新的 set-model-and-conf
  audioQueue.interrupt();
  turnActive = false;
  ui.setBusy(false);
  ui.clearSubtitles();
  ui.setStatus('切换角色…');
  ws.send({ type: 'switch-config', file: filename });
};

ui.onNewChat = () => {
  audioQueue.interrupt();
  turnActive = false;
  ui.setBusy(false);
  renderer.resetExpression();
  history.newChat();
};

ui.onToggleHistory = (enabled) => {
  audioQueue.interrupt();
  turnActive = false;
  ui.setBusy(false);
  history.setEnabled(enabled);
};

ui.onToggleTouchDebug = (on) => {
  touchDebugOn = on;
  ui.setTouchDebugEnabled(on);
  renderer.setTouchDebug?.(on);
};

ui.onToggleDebugPanel = (on) => {
  debugPanelOn = on;
  ui.setDebugPanelEnabled(on);
  renderer.setDebugPanel?.(on);
};

// 仅视觉复位：不发 interrupt-signal，避免取消角色正在生成的对话
ui.onResetModel = () => {
  audioQueue.interrupt();
  turnActive = false;
  ui.setBusy(false);
  if (!renderer.resetToInitialMotion) {
    ui.setResetStatus(false);
    return;
  }
  renderer.resetToInitialMotion();
  ui.setResetStatus(true);
};

// 切模型必须走后端：后端切 Live2dModel 并重建 emotionMap/系统提示，前端只加载回推的模型
ui.onSwitchLive2DModel = (modelName) => {
  if (!modelName || modelName === currentLive2DModelName) return;
  audioQueue.interrupt();
  turnActive = false;
  ui.setBusy(false);
  ui.setLive2DModelEnabled(false);
  ui.setStatus(`切换模型 ${modelName}…`);
  ws.send({ type: 'switch-live2d-model', model_name: modelName });
};

// ---- 连接 ----

ws.onOpen = () => {
  ui.setConnected(true);
  ui.setStatus('已连接，等待模型…');
  ws.send({ type: 'fetch-configs' });
  ws.send({ type: 'fetch-live2d-models' });
};
ws.onClose = () => {
  ui.setConnected(false);
};
ws.connect();

// 调试句柄（控制台可用：切换配置、手动触发表情等）
Object.assign(window, {
  __vtuber: {
    get renderer() {
      return renderer;
    },
    ws,
    audioQueue,
  },
});
