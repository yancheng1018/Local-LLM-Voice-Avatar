/**
 * 顺序播放队列。
 *
 * 后端逐句下发 `audio` 消息（base64 WAV；audio 为 null 表示纯字幕句），
 * 本队列保证按到达顺序播放；每句开始播放时回调 onSentenceStart
 * （由 main.ts 同步字幕与表情）。服务端在全部合成完后发 `backend-synth-complete`，
 * 播完最后一句后必须回 `frontend-playback-complete`，否则服务端会等超时
 * （conversation_utils.finalize_conversation_turn）。
 */

export interface AudioMessage {
  type: 'audio';
  audio: string | null;
  volumes: number[];
  slice_length: number;
  display_text?: { text?: string; name?: string; avatar?: string } | null;
  actions?: { expressions?: (number | string)[] } | null;
}

export interface AudioQueueHooks {
  /** 某句开始播放（或纯字幕句开始显示） */
  onSentenceStart(msg: AudioMessage): void;
  /** 本轮全部播放完成（已发送 frontend-playback-complete） */
  onPlaybackComplete(): void;
}

/** 纯字幕句（audio:null）的停留时长 */
const SILENT_DISPLAY_MS = 800;

export class AudioQueue {
  private queue: AudioMessage[] = [];
  private currentSource: AudioBufferSourceNode | null = null;
  private playing = false;
  private synthComplete = false;
  // 代际计数：interrupt() 自增，使在途的旧播放循环自行退出，
  // 且旧循环退出时不覆盖新一轮的 playing 状态
  private generation = 0;
  // 口型同步数据源：当前句的音量包络（后端按 20ms 切片的归一化 RMS）
  private currentVolumes: number[] = [];
  private currentSliceMs = 20;
  private startedAtCtx = 0;
  private smoothedVol = 0;
  private lastVolCall = 0;

  constructor(
    private ctx: AudioContext,
    private send: (msg: Record<string, unknown>) => void,
    private hooks: AudioQueueHooks,
  ) {}

  enqueue(msg: AudioMessage): void {
    this.queue.push(msg);
    if (!this.playing) void this.playLoop();
  }

  markSynthComplete(): void {
    this.synthComplete = true;
    this.maybeFinish();
  }

  /** 打断：清空队列、停止当前音频。后续轮次可继续 enqueue 复用 */
  interrupt(): void {
    this.generation++;
    this.queue = [];
    this.currentSource?.stop();
    this.currentSource = null;
    this.playing = false;
    this.currentVolumes = [];
    // 被打断的轮次不再等待播放完成；重置标志以开始下一轮
    this.synthComplete = false;
  }

  get busy(): boolean {
    return this.playing || this.queue.length > 0;
  }

  /** 当前音量 0~1（按播放位置取 20ms RMS 包络 + 平滑），供口型同步每帧读取 */
  get volumeLevel(): number {
    let target = 0;
    if (this.currentSource && this.currentVolumes.length > 0) {
      const elapsedMs = (this.ctx.currentTime - this.startedAtCtx) * 1000;
      const idx = Math.floor(elapsedMs / this.currentSliceMs);
      target = this.currentVolumes[idx] ?? 0;
    }
    const now = performance.now();
    const dt = Math.min((now - this.lastVolCall) / 1000, 0.1);
    this.lastVolCall = now;
    if (target >= this.smoothedVol) {
      this.smoothedVol = target; // 起音即时
    } else {
      // 释放衰减（时间常数 ~70ms），避免嘴型抖动
      this.smoothedVol = target + (this.smoothedVol - target) * Math.exp(-dt / 0.07);
    }
    if (this.smoothedVol < 0.01) this.smoothedVol = 0;
    return this.smoothedVol;
  }

  private async playLoop(): Promise<void> {
    const gen = this.generation;
    this.playing = true;
    try {
      while (this.queue.length > 0 && gen === this.generation) {
        const msg = this.queue.shift()!;
        await this.playOne(msg, gen);
        this.maybeFinish();
      }
    } finally {
      // 旧代际的循环退出时不覆盖新一代的状态（interrupt 后立刻 enqueue 的场景）
      if (gen === this.generation) {
        this.playing = false;
        this.maybeFinish();
      }
    }
  }

  private async playOne(msg: AudioMessage, gen: number): Promise<void> {
    this.hooks.onSentenceStart(msg);

    if (!msg.audio) {
      this.currentVolumes = [];
      await sleep(SILENT_DISPLAY_MS);
      return;
    }

    this.currentVolumes = msg.volumes ?? [];
    this.currentSliceMs = msg.slice_length || 20;
    const buffer = await this.decode(msg.audio);
    if (gen !== this.generation) return; // 播放期间被 interrupt
    await this.playBuffer(buffer);
  }

  private decode(base64: string): Promise<AudioBuffer> {
    const bin = atob(base64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return this.ctx.decodeAudioData(bytes.buffer);
  }

  private playBuffer(buffer: AudioBuffer): Promise<void> {
    return new Promise((resolve) => {
      const source = this.ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(this.ctx.destination);
      source.onended = () => {
        if (this.currentSource === source) {
          this.currentSource = null;
          this.currentVolumes = [];
        }
        resolve();
      };
      this.currentSource = source;
      this.startedAtCtx = this.ctx.currentTime + 0.005; // start() 到出声的微小延迟
      source.start();
    });
  }

  private maybeFinish(): void {
    if (!this.synthComplete || this.playing || this.queue.length > 0) return;
    this.synthComplete = false;
    this.send({ type: 'frontend-playback-complete', text: '' });
    this.hooks.onPlaybackComplete();
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
