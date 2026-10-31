# Audit Logger

- 文件：`modules/audit.py`
- 配置：`audit.enabled`、`audit.global_channel`、`audit.guilds`
- 无指令，作为 `bot.audit` 共享服务。

## 入口

- `AuditLogger.log(action=..., user=..., guild=..., channel=..., detail=...)`
- 仅发送到全局频道 + 对应服务器频道（两者独立）。
- 每个语言只构建一次 embed 并缓存。

## 记录范围

- `[ADMIN]` / `[MOD]` 指令。
- 服务器 scope 的变更。
- 自动处置与错误。
- 不记录用户 scope 的普通指令（`/random`、`/uuid`、`/to-file`、用户 `/lang`）。

## 注意

- 审计失败必须静默忽略，不能影响主流程。
- 批量操作只记汇总，逐条失败用 `l.warning()`。
- 反垃圾撤销视图也在这里，改动时注意与 `cogs/antispam.py` 的标签格式保持一致。
