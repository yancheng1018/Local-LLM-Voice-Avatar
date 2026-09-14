/** 极简 UI：全屏模型舞台 + 顶部状态行 + 底部字幕/输入区 */

export class UI {
  private statusText: HTMLElement;
  private connDot: HTMLElement;
  private subtitles: HTMLElement;
  private input: HTMLInputElement;
  private sendBtn: HTMLButtonElement;
  private interruptBtn: HTMLButtonElement;
  private charSelect: HTMLSelectElement;

  onSend: ((text: string) => void) | null = null;
  onInterrupt: (() => void) | null = null;
  onSwitchCharacter: ((filename: string) => void) | null = null;
  onNewChat: (() => void) | null = null;
  onToggleHistory: ((enabled: boolean) => void) | null = null;
  onToggleTouchDebug: ((enabled: boolean) => void) | null = null;
  onToggleDebugPanel: ((enabled: boolean) => void) | null = null;

  constructor() {
    this.statusText = document.getElementById('status-text')!;
    this.connDot = document.getElementById('conn-dot')!;
    this.subtitles = document.getElementById('subtitles')!;
    this.input = document.getElementById('text-input') as HTMLInputElement;
    this.sendBtn = document.getElementById('send-btn') as HTMLButtonElement;
    this.interruptBtn = document.getElementById('interrupt-btn') as HTMLButtonElement;
    this.charSelect = document.getElementById('char-select') as HTMLSelectElement;

    this.sendBtn.addEventListener('click', () => this.submit());
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.submit();
    });
    this.interruptBtn.addEventListener('click', () => this.onInterrupt?.());
    this.charSelect.addEventListener('change', () => {
      const filename = this.charSelect.value;
      if (filename) this.onSwitchCharacter?.(filename);
    });
    const newChatBtn = document.getElementById('new-chat-btn') as HTMLButtonElement;
    newChatBtn.addEventListener('click', () => this.onNewChat?.());
    const historyBtn = document.getElementById('history-toggle-btn') as HTMLButtonElement;
    historyBtn.addEventListener('click', () => this.onToggleHistory?.(historyBtn.textContent!.includes('关')));
    const touchDebugBtn = document.getElementById('touch-debug-btn') as HTMLButtonElement;
    touchDebugBtn.addEventListener('click', () => this.onToggleTouchDebug?.(touchDebugBtn.textContent!.includes('关')));
    const debugPanelBtn = document.getElementById('debug-panel-btn') as HTMLButtonElement;
    debugPanelBtn.addEventListener('click', () => this.onToggleDebugPanel?.(debugPanelBtn.textContent!.includes('关')));
  }

  /** 历史功能开关状态（按钮文案 + 新对话按钮可用性） */
  setHistoryEnabled(enabled: boolean): void {
    const historyBtn = document.getElementById('history-toggle-btn') as HTMLButtonElement;
    historyBtn.textContent = enabled ? '🕘 历史：开' : '🕘 历史：关';
    (document.getElementById('new-chat-btn') as HTMLButtonElement).disabled = !enabled;
  }

  /** 热区可视化开关状态（按钮文案 开/关） */
  setTouchDebugEnabled(enabled: boolean): void {
    const btn = document.getElementById('touch-debug-btn') as HTMLButtonElement;
    btn.textContent = enabled ? '🔍 热区：开' : '🔍 热区：关';
  }

  /** 调试栏开关状态（按钮文案 开/关） */
  setDebugPanelEnabled(enabled: boolean): void {
    const btn = document.getElementById('debug-panel-btn') as HTMLButtonElement;
    btn.textContent = enabled ? '🧪 调试栏：开' : '🧪 调试栏：关';
  }

  /** 填充角色下拉；currentName 传当前角色显示名用于选中 */
  setCharacters(configs: { filename: string; name: string }[], currentName: string): void {
    this.charSelect.replaceChildren();
    for (const c of configs) {
      const opt = document.createElement('option');
      opt.value = c.filename;
      opt.textContent = c.name;
      if (c.name === currentName) opt.selected = true;
      this.charSelect.appendChild(opt);
    }
  }

  private submit(): void {
    const text = this.input.value.trim();
    if (!text) return;
    this.input.value = '';
    this.onSend?.(text);
  }

  setConnected(ok: boolean): void {
    this.connDot.classList.toggle('off', !ok);
    this.connDot.classList.toggle('on', ok);
    if (!ok) this.setStatus('连接断开，2 秒后重连…');
  }

  setStatus(text: string, isError = false): void {
    this.statusText.textContent = text;
    this.statusText.classList.toggle('error', isError);
  }

  /** 一句开始播放时调用：加入字幕区并高亮为当前句 */
  appendSubtitle(text: string): void {
    this.appendBubble(text, 'current');
  }

  /** 用户自己发送的消息：右侧气泡 */
  appendUserMessage(text: string): void {
    this.appendBubble(text, 'mine');
  }

  /** 还原历史记录（不受实时 8 条上限约束，无当前句高亮） */
  restoreBubbles(messages: { role: string; content: string }[]): void {
    this.subtitles.replaceChildren();
    for (const m of messages) {
      if (!m.content) continue;
      const el = document.createElement('div');
      el.className = 'sentence' + (m.role === 'human' ? ' mine' : '');
      el.textContent = m.content;
      this.subtitles.appendChild(el);
    }
    this.subtitles.scrollTop = this.subtitles.scrollHeight;
  }

  private appendBubble(text: string, cls: string): void {
    if (!text) return;
    if (cls !== 'current') {
      this.subtitles.querySelector('.current')?.classList.remove('current');
    }
    const el = document.createElement('div');
    el.className = 'sentence' + (cls ? ` ${cls}` : '');
    el.textContent = text;
    this.subtitles.appendChild(el);
    while (this.subtitles.children.length > 8) {
      this.subtitles.firstChild?.remove();
    }
    el.scrollIntoView({ block: 'end' });
  }

  clearSubtitles(): void {
    this.subtitles.replaceChildren();
  }

  setBusy(busy: boolean): void {
    this.interruptBtn.disabled = !busy;
  }
}
