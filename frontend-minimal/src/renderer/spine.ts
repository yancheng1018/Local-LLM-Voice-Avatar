import {
  AtlasAttachmentLoader,
  AssetManager,
  ManagedWebGLRenderingContext,
  SceneRenderer,
  Skeleton,
  SkeletonBinary,
  TextureAtlas,
  AnimationState,
  AnimationStateData,
} from '@esotericsoftware/spine-webgl';
import type { ModelInfo, CharacterRenderer } from './types';

/**
 * Spine 渲染器（spine-webgl 4.1.x，与模型 skel 格式版本匹配）。
 *
 * 独立 canvas + WebGL 上下文，与 L2DRenderer 的 pixi 完全隔离，零依赖冲突。
 * emotionMap 的值约定为 Spine 动画名（复用后端关键词->值管线，
 * setExpression 收到的 expressions[0] 在这里作为动画播放）。
 */

export class SpineRenderer implements CharacterRenderer {
  private context: ManagedWebGLRenderingContext | null = null;
  private renderer: SceneRenderer | null = null;
  private skeleton: Skeleton | null = null;
  private state: AnimationState | null = null;
  private rafId = 0;
  private disposed = false;
  private lastTime = 0;
  private idleAnimation = '';
  private bounds: { x: number; y: number; width: number; height: number } | null = null;

  constructor(private container: HTMLElement) {}

  async load(modelInfo: ModelInfo): Promise<void> {
    this.disposeRuntime();

    const skelUrl = modelInfo.url;
    const atlasUrl = skelUrl.replace(/\.skel$/, '.atlas');

    const canvas = document.createElement('canvas');
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.display = 'block';
    this.container.appendChild(canvas);

    this.context = new ManagedWebGLRenderingContext(canvas, { alpha: true });
    const gl = this.context.gl;

    // AssetManagerBase 是回调式 API，这里包成 Promise。
    // pathPrefix 留空、传完整 URL（其内部对 atlas 各页贴图按 atlas 所在目录拼相对路径）
    const assets = new AssetManager(this.context, '');
    const full = (u: string) => new URL(u, location.href).href;
    await Promise.all([
      new Promise<void>((resolve, reject) =>
        assets.loadTextureAtlas(full(atlasUrl), () => resolve(), (_p, msg) => reject(new Error(`atlas 加载失败: ${msg}`))),
      ),
      new Promise<Uint8Array>((resolve, reject) =>
        assets.loadBinary(full(skelUrl), (_p, bin) => resolve(bin), (_p, msg) => reject(new Error(`skel 加载失败: ${msg}`))),
      ),
    ]);
    if (this.disposed) return;

    const atlas = assets.get(full(atlasUrl)) as TextureAtlas;
    const attachmentLoader = new AtlasAttachmentLoader(atlas);
    const skeletonData = new SkeletonBinary(attachmentLoader).readSkeletonData(
      assets.get(full(skelUrl)) as Uint8Array,
    );

    const skeleton = new Skeleton(skeletonData);
    const state = new AnimationState(new AnimationStateData(skeletonData));

    // 待机动画：优先名含 loop 的，否则取第一个
    const anims = skeletonData.animations.map((a) => a.name);
    this.idleAnimation = anims.find((n) => n.toLowerCase().includes('loop')) ?? anims[0] ?? '';
    if (this.idleAnimation) state.setAnimation(0, this.idleAnimation, true);
    console.info(`[Spine] ${modelInfo.name} 动画列表:`, anims);

    this.renderer = new SceneRenderer(canvas, this.context);
    this.skeleton = skeleton;
    this.state = state;

    // 用「待机动画首帧」的实际网格顶点算包围盒：setup pose 会包含
    // 未显示的场景件（背景/特效网格），导致包围盒远大于人物本体
    state.update(0);
    state.apply(skeleton);
    skeleton.updateWorldTransform();
    this.bounds = this.computeBounds();

    this.fitCamera(this.bounds);
    gl.clearColor(0, 0, 0, 0);
    this.lastTime = performance.now();
    this.loop();
  }

  /** 依据当前姿势所有可见 attachment 顶点的 AABB 适配相机 */
  private computeBounds(): { x: number; y: number; width: number; height: number } {
    const skeleton = this.skeleton!;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const slot of skeleton.slots) {
      const att = slot.attachment as unknown as {
        worldVerticesLength?: number;
        bone?: unknown;
        bones?: unknown;
        endSlot?: unknown;
        computeWorldVertices?: (...args: unknown[]) => void;
      } | null;
      // 跳过无顶点的附件与不参与渲染的 ClippingAttachment（顶点范围巨大，会污染包围盒）
      if (!att?.computeWorldVertices || !att.worldVerticesLength || att.endSlot !== undefined) continue;
      const n = att.worldVerticesLength;
      const arr = new Float32Array(n);
      try {
        // RegionAttachment 挂在 bone 上，VertexAttachment（Mesh）挂在 slot 上
        if (att.bones === undefined) {
          att.computeWorldVertices(slot.bone, 0, n, arr, 0, 2);
        } else {
          att.computeWorldVertices(slot, 0, n, arr, 0, 2);
        }
      } catch {
        continue;
      }
      for (let i = 0; i + 1 < arr.length; i += 2) {
        if (!Number.isFinite(arr[i]) || !Number.isFinite(arr[i + 1])) continue;
        minX = Math.min(minX, arr[i]);
        maxX = Math.max(maxX, arr[i]);
        minY = Math.min(minY, arr[i + 1]);
        maxY = Math.max(maxY, arr[i + 1]);
      }
    }
    if (!Number.isFinite(minX) || maxX - minX <= 0 || maxY - minY <= 0) {
      // 兜底：编辑器设置的骨架尺寸
      const d = skeleton.data;
      return { x: d.x, y: d.y, width: d.width, height: d.height };
    }
    return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
  }

  /** 依据包围盒适配相机（spine OrthoCamera：可见世界尺寸 = viewport × zoom） */
  private fitCamera(bounds: { x: number; y: number; width: number; height: number }): void {
    if (!this.renderer) return;
    const canvas = this.renderer.canvas;
    const w = canvas.clientWidth || canvas.width;
    const h = canvas.clientHeight || canvas.height;

    const camera = this.renderer.camera;
    if (bounds.width > 0 && bounds.height > 0) {
      const zoom = Math.max(bounds.width / w, bounds.height / h) / 0.9;
      camera.zoom = zoom;
      camera.position.set(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2, 0);
    }
    camera.setViewport(w, h);
    camera.update();
  }

  private loop = (): void => {
    if (this.disposed) return;
    this.rafId = requestAnimationFrame(this.loop);

    const now = performance.now();
    const delta = Math.min((now - this.lastTime) / 1000, 0.1);
    this.lastTime = now;

    const { skeleton, state, renderer, context } = this;
    if (!skeleton || !state || !renderer || !context) return;

    const canvas = renderer.canvas;
    const cw = canvas.clientWidth || canvas.width;
    const ch = canvas.clientHeight || canvas.height;
    if (canvas.width !== cw || canvas.height !== ch) {
      canvas.width = cw;
      canvas.height = ch;
      if (this.bounds) this.fitCamera(this.bounds);
    }
    // WebGL 上下文创建时 viewport 固定为 canvas 的默认尺寸（300×150），
    // spine 运行时不会主动更新，必须随 canvas 尺寸同步
    const gl = context.gl;
    gl.viewport(0, 0, canvas.width, canvas.height);

    state.update(delta);
    state.apply(skeleton);
    skeleton.updateWorldTransform();

    gl.clear(gl.COLOR_BUFFER_BIT);
    renderer.begin();
    renderer.drawSkeleton(skeleton);
    renderer.end();
  };

  setExpression(value: number | string): void {
    if (!this.state || typeof value !== 'string') return;
    const names = this.skeleton?.data.animations.map((a) => a.name) ?? [];
    if (!names.includes(value)) {
      console.warn(`[Spine] 未知动画: ${value}`);
      return;
    }
    const track = this.state.setAnimation(0, value, false);
    // 表情动画播完回待机
    track.listener = {
      complete: () => {
        if (this.idleAnimation && !this.disposed) {
          this.state?.setAnimation(0, this.idleAnimation, true);
        }
      },
    };
  }

  setAnimation(group: string, _priority?: number): void {
    // Talk 等组名：模型有同名动画才播，否则忽略（cutscene 模型通常没有）
    if (!this.state) return;
    const names = this.skeleton?.data.animations.map((a) => a.name) ?? [];
    const target = names.find((n) => n.toLowerCase() === group.toLowerCase());
    if (target) this.state.setAnimation(0, target, false);
  }

  getMotionGroups(): string[] {
    return this.skeleton?.data.animations.map((a) => a.name) ?? [];
  }

  get hasTouchRules(): boolean {
    return false; // Spine 模型无 touch.json 规则数据
  }

  resetExpression(): void {
    if (this.idleAnimation) this.state?.setAnimation(0, this.idleAnimation, true);
  }

  dispose(): void {
    this.disposed = true;
    cancelAnimationFrame(this.rafId);
    this.disposeRuntime();
    this.container.replaceChildren();
  }

  private disposeRuntime(): void {
    this.renderer?.dispose();
    this.renderer = null;
    this.skeleton = null;
    this.state = null;
    // ManagedWebGLRenderingContext 无 dispose：换模型时直接丢弃旧 canvas，
    // 由 GC 回收丢失的 WebGL 上下文（浏览器上限 8~16 个，正常使用足够）
    this.context = null;
  }
}
