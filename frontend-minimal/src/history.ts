import type { WSClient } from './ws';
import type { UI } from './ui';

/**
 * 聊天历史持久化。
 *
 * 每次连接就绪（收到 set-model-and-conf）后调用 initHistory()：
 * 拉取当前角色的历史列表 → 自动载入最新一份（服务端会同步切换 LLM 记忆）
 * → 还原气泡。「新对话」按钮发 create-new-history，服务端切到空历史。
 *
 * 注意：每个新 WS 连接服务端都克隆默认上下文（history_uid 为空），
 * 所以恢复逻辑必须每次连接都跑。
 */
export class HistoryManager {
  private pendingFetch = false;
  /** 历史功能开关：关闭时不拉取/还原历史（长历史会拖慢 LLM 与语音合成），状态存 localStorage */
  enabled: boolean = localStorage.getItem('history_enabled') === 'on';

  constructor(
    private ws: WSClient,
    private ui: UI,
  ) {
    ws.register('history-list', (data) => this.onHistoryList(data));
    ws.register('history-data', (data) => this.onHistoryData(data));
    ws.register('new-history-created', () => {
      this.ui.clearSubtitles();
      this.ui.setStatus('已开启新对话');
    });
    this.ui.setHistoryEnabled(this.enabled);
  }

  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    localStorage.setItem('history_enabled', enabled ? 'on' : 'off');
    this.ui.setHistoryEnabled(enabled);
    if (enabled) {
      this.init(); // 立即恢复当前对话
    } else {
      this.ui.clearSubtitles();
      this.ui.setStatus('历史功能已关闭');
    }
  }

  newChat(): void {
    this.ws.send({ type: 'create-new-history' });
  }

  /** 连接/切角色就绪后调用：找最新历史并载入（功能关闭时跳过） */
  init(): void {
    if (!this.enabled) return;
    this.pendingFetch = true;
    this.ws.send({ type: 'fetch-history-list' });
  }

  private onHistoryList(data: Record<string, unknown>): void {
    if (!this.pendingFetch) return;
    this.pendingFetch = false;
    const histories = (data.histories as { uid: string }[]) ?? [];
    // 列表已按 timestamp 倒序，取最新
    if (histories.length === 0) return;
    this.ws.send({ type: 'fetch-and-set-history', history_uid: histories[0].uid });
  }

  private onHistoryData(data: Record<string, unknown>): void {
    const messages = (data.messages as { role: string; content: string }[]) ?? [];
    this.ui.restoreBubbles(messages.filter((m) => m.role === 'human' || m.role === 'ai'));
    if (messages.length > 0) {
      this.ui.setStatus('已恢复上次对话');
    }
  }
}
