/**
 * model_dict.json 条目中原样透传的字段（set-model-and-conf 的 model_info）。
 * 阶段二 Spine 模型会带 animationMap 等新字段，这里保持开放索引签名。
 */
export interface ModelInfo {
  name: string;
  url: string;
  kScale?: number;
  initialXshift?: number;
  initialYshift?: number;
  emotionMap?: Record<string, number | string>;
  [key: string]: unknown;
}

/**
 * 角色渲染器抽象：阶段一 L2DRenderer（pixi-live2d-display），
 * 阶段二 SpineRenderer（spine-pixi）实现同一接口，按模型 url 后缀分流。
 */
export interface CharacterRenderer {
  /** 加载模型并显示；同一 renderer 实例可重复调用以切换模型 */
  load(modelInfo: ModelInfo): Promise<void>;
  /** 应用表情。数字 = model3.json Expressions 的索引，字符串 = 表情名 */
  setExpression(value: number | string): void;
  /** 播放指定动作组（如 Talk / Idle）中的一个动作。
   *  priority：2=NORMAL（说话等常规触发），3=FORCE（点击动作盖过待机） */
  setAnimation(group: string, priority?: number): void;
  /** 模型可用的动作组名列表（L2D=Motion 组，Spine=动画名） */
  getMotionGroups(): string[];
  /** 是否加载了触摸规则数据（有规则时区域外点击不触发兜底） */
  readonly hasTouchRules: boolean;
  /** 触摸热区可视化开关（仅 L2D 实现；Spine 渲染器无此功能，故为可选方法） */
  setTouchDebug?(enabled: boolean): void;
  /** 仿 l2d.su 左侧调试栏开关（仅 L2D 实现） */
  setDebugPanel?(enabled: boolean): void;
  /** 停止当前动作并回到模型的初始待机动作（仅 L2D 实现） */
  resetToInitialMotion?(): void;
  /** 回到默认表情 */
  resetExpression(): void;
  dispose(): void;
}
