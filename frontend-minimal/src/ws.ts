/**
 * WebSocket 客户端：按消息 type 可插拔注册 handler。
 * 协议零假设 —— 后端（websocket_handler.py）对未知 type 只记日志，前端可自由增减处理。
 */
type Handler = (data: Record<string, unknown>) => void;

export class WSClient {
  private ws: WebSocket | null = null;
  private handlers = new Map<string, Set<Handler>>();
  private reconnectTimer: number | null = null;
  private closedByUser = false;
  // 心跳保活：防止空闲连接被网络中间设备掐断
  private heartbeatTimer: number | null = null;
  private lastAlive = 0;

  constructor(private url: string) {}

  onOpen: (() => void) | null = null;
  onClose: (() => void) | null = null;

  connect(): void {
    this.closedByUser = false;
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.lastAlive = Date.now();
      this.startHeartbeat();
      this.onOpen?.();
    };
    this.ws.onclose = () => {
      this.stopHeartbeat();
      this.onClose?.();
      // 服务重启/网络闪断后自动重连；服务端会重新推送初始消息（含模型）
      if (!this.closedByUser) {
        this.reconnectTimer = window.setTimeout(() => this.connect(), 2000);
      }
    };
    this.ws.onmessage = (event) => {
      let data: Record<string, unknown>;
      try {
        data = JSON.parse(event.data);
      } catch {
        console.error('Invalid JSON from server:', event.data);
        return;
      }
      if (data.type === 'heartbeat-ack') {
        this.lastAlive = Date.now();
        return;
      }
      const type = data.type as string | undefined;
      if (!type) return;
      this.handlers.get(type)?.forEach((h) => {
        try {
          h(data);
        } catch (e) {
          console.error(`Handler for "${type}" threw:`, e);
        }
      });
    };
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    // 30s 一跳；90s 没有任何服务端消息则认定死链，主动断开触发重连
    this.heartbeatTimer = window.setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        if (Date.now() - this.lastAlive > 90_000) {
          console.warn('WS heartbeat timeout, reconnecting…');
          this.ws.close();
          return;
        }
        this.ws.send(JSON.stringify({ type: 'heartbeat' }));
      }
    }, 30_000);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer !== null) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /** 注册某 type 的处理器，返回解注册函数 */
  register(type: string, handler: Handler): () => void {
    let set = this.handlers.get(type);
    if (!set) {
      set = new Set();
      this.handlers.set(type, set);
    }
    set.add(handler);
    return () => set!.delete(handler);
  }

  send(msg: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    } else {
      console.warn('WS not open, dropped message:', msg);
    }
  }

  close(): void {
    this.closedByUser = true;
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.stopHeartbeat();
    this.ws?.close();
  }
}

/** ws://host:port/client-ws —— dev 下经 Vite 代理转发到后端 */
export function defaultWsUrl(): string {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${location.host}/client-ws`;
}
