# GPT-SoVITS API 启动适配器

本项目为 GPT-SoVITS 整合包自制的启动适配器，基于 GPT-SoVITS（MIT License）**v2pro-20250604** 版整合包布局自制，仅做启动封装，不包含 GPT-SoVITS 源码与任何权重。

## 用途

`start_gsv_api.py`：以指定权重启动 GPT-SoVITS API 服务（api_v2.py，127.0.0.1:9880）。以 UTF-8 生成临时配置（不改整合包原有 tts_infer.yaml，用后即删）。

## 用法

```bash
python scripts/gpt_sovits/start_gsv_api.py --root <GSV整合包根目录> [--version v4] [--gpt <权重>] [--sovits <权重>]
```

- GUI 用户无需手动调用：启动器「一键启动」会直接调用本脚本并传入所选声音模型权重。
- 显式权重缺省时，取 `GPT_weights_<version>/` 与 `SoVITS_weights_<version>/` 中修改时间最新的一对。

## 说明

- 前置：整合包内已自行放好权重；本仓库不提供权重与参考音频。
- 9880 端口被占用时会直接报错退出（先关闭旧实例）。
- 目标整合包版本：v2pro-20250604；其他版本可尝试 `--version` 传对应目录后缀。
- 错误即打印即退出（无交互暂停）——GUI 启动器以 Popen 调用本脚本，无控制台交互依赖。

## 历史注

本适配器由原收录件升格而来：最初的「拷贝脚本进整合包根目录 + bat 双击」用法已随适配器化退役（2026-09-30），现统一走上述 CLI（GUI 自动调或手动传 `--root`）。
