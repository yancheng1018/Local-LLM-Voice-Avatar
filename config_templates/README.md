
# Config Template

本目录存放默认配置模板。**模板不会自动复制** —— git_stage2 已移除上游的
`sync_user_config()`，服务器启动时不再创建、备份或合并 `conf.yaml`。

首次使用（或 `conf.yaml` 丢失）时，手工复制其一到项目根目录并改名为 `conf.yaml`：

```powershell
copy config_templates\conf.ZH.default.yaml conf.yaml    # 中文版（推荐）
copy config_templates\conf.default.yaml conf.yaml       # 英文版
```

缺少 `conf.yaml` 时服务器会直接退出，并在日志中给出同样的指引。

修改模板内容前请确认你清楚后果：模板是"出厂默认值"，重装或重置配置时会被再次复制使用。
