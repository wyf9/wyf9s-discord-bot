# Lock Cog

- 文件：`cogs/lock.py`
- 配置：`lock.enabled`
- 数据：`schedules.yaml`（`ScheduleStore`，存放在数据目录）
- 指令：`/lock now|unlock|plan|unplan`
- 权限：`u.Permission.MOD`

## 关键实现

- 锁 / 解锁通过 `channel.set_permissions(default_role, overwrite=...)`。
- 计划支持单次、每日、每周、每月；时间按 UTC+8 解析。
- `_check_schedules` 是 `tasks.loop` 每分钟检查，已在 `cog_load` 启动。
- 计划数据持久化在 `schedules.yaml`；`lock now` 会清除该频道已有计划。

## 注意

- 修改调度逻辑时同时检查 `cycle_start` / `cycle_end` / 循环清理。
- 重载 Cog 不要丢 `bot.schedule_store`。
- 新增参数要同步斜杠命令、前缀 flag 解析、lang 文案与用户文档。
