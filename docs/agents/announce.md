# Announce Cog

- 文件：`cogs/announce.py`
- 配置：`announce.source_channel`（News Channel ID）
- 权限：`u.Permission.MOD`

## 指令

- `/subscribe [target]`：让目标频道关注 `source_channel`。
- 前缀同名命令复用同一 `_handle_subscribe()`。

## 注意

- 依赖 Discord Channel Following：机器人需要目标频道 **Manage Webhooks**。
- 未配置 `source_channel` 时应给出明确错误，不要静默失败。
- 审计 action：`subscribe`。
