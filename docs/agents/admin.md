# Admin Cog

- 文件：`cogs/admin.py`
- 配置键：无（始终加载；受全局 `slash` / `prefix` 控制）
- 权限：`u.Permission.ADMIN`（仅 `admins.users`）

## 指令

- `/sync`：`tree.sync()`。
- `/reload [module]`：重载单个 Cog、全部 Cog 或配置（`config`）。
- 前缀别名：`sync`、`sync-commands`、`reload`。

## 关键实现

- 重载冷却 15s / 用户，状态在 Cog 实例上。
- `module` 自动补全来自 `u.list_cog_names()`。
- `config` 重载会重新读取配置并调整已加载模块；不会自动加载从禁用变为启用的新模块。
- 审计 action：`sync`、`reload`、`reload-all`、`reload-config`。

## 注意

- 全局 `slash: false` 时，`main.py` 注册的 `tree.interaction_check` 会直接忽略所有斜杠交互，避免同 token 多实例互相抢答；前缀指令不受影响。
- 修改后确认 `main.COG_LIST` / `COG_TO_CONFIG` 同步。
- 重载相关逻辑不要清理 bot 上的共享状态，否则会丢语音连接 / 限速 / 计划数据。
