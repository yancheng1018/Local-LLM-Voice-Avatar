# GPT-SoVITS 一键启动脚本（配套）

本项目为 GPT-SoVITS 整合包自制的启动脚本，基于 GPT-SoVITS（MIT License）v2pro-20250604 版使用，仅做启动封装，不包含 GPT-SoVITS 源码与任何权重。

## 用途
`start_v4_dpo.bat` / `start_v4_dpo.py`：以 V4 DPO 微调权重一键启动 GPT-SoVITS
API 服务（api_v2.py，127.0.0.1:9880）。自动在 `GPT_weights_v4/` 与
`SoVITS_weights_v4/` 中查找 `*v4dpo*.ckpt` / `*v4dpo*.pth`（不写死权重文件名，
多个时取修改时间最新），以 UTF-8 生成临时配置，不改动整合包原有 tts_infer.yaml。

## 用法
1. 将本目录两个文件复制到 GPT-SoVITS 整合包根目录（与 runtime/python.exe、api_v2.py 同级）。
2. 双击 `start_v4_dpo.bat`，保持窗口打开；9880 被占用时会提示先关闭旧实例。

## 说明
- 前置：整合包内已自行放好 V4 DPO 权重；本仓库不提供权重与参考音频。
- 收录版相对本地原版仅差 lint 修正（删除未使用 import）与格式化，无逻辑改动。
