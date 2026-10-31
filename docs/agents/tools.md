# Tools Cog

- 文件：`cogs/tools.py`
- 清理服务：`modules/clear_message.py`
- 配置：`tools.enabled`、`tools.clear_single_delete_max`
- 指令：`random`、`uuid`、`to-file`（所有人）；`delete`、`clear-message`、`move-channel`（Mod）
- 限速：全局 `ratelimit`，模块名 `tools`，指令 `random` / `uuid` / `to-file`

## 关键入口

- `_handle_random` / `_handle_uuid` / `_handle_to_file`
- `_handle_delete`
- `_handle_clear_message`（实际逻辑在 `ClearMessageService`）
- `_handle_move_channel`
- `_check_rate_limit` 统一调用 `u.resolve_rate_limit()`

## 注意

- `clear-message` 的斜杠参数与前缀 flag 要同步维护（`_parse_flags`）。
- 批量清理不要逐条审计，服务层只写汇总。
- 结果消息带 `[clear-message]` 标记，清理时应跳过，避免误删。
- 新增指令时接入限速、审计、lang 文案和用户文档。
