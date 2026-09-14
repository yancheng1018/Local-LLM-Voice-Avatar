/** 调试栏的结构化类型（规格书 §2/§3.1）。单独成文件以满足单模块 ≤200 行约束。
 *  Live2DModel / CubismModel 的窄接口——main/l2d 传入的 this.model 由面板自行 cast。 */

/** coreModel 的结构化子集（规格书 §2 的 8 个方法） */
export interface DebugCoreModel {
  getParameterCount(): number;
  getParameterMinimumValue(i: number): number;
  getParameterMaximumValue(i: number): number;
  getParameterValueById(id: string): number;
  setParameterValueById(id: string, value: number): void;
  getPartCount(): number;
  getPartOpacityById(id: string): number;
  setPartOpacityById(id: string, opacity: number): void;
}

/** 核心 Live2DCubismCore.Model 的最小取形：经框架 getModel() 取，parameters.ids / parts.ids */
export interface DebugCoreSource {
  getModel?(): Record<string, { ids?: string[] }>;
}

/** Live2DModel 的结构化子集 */
export interface DebugPanelModel {
  visible: boolean;
  alpha: number;
  motion(group: string, index?: number, priority?: number): Promise<boolean>;
  internalModel: {
    coreModel?: DebugCoreModel | null;
    settings?: { motions?: Record<string, unknown[]> } & Record<string, unknown>;
  } & Record<string, unknown>;
}

/** 一行滑条（label + range + 数值 span），注册进 rows 供 RAF 回写 */
export interface Row {
  key: string;
  input: HTMLInputElement;
  val: HTMLSpanElement;
  get: () => number;
}
