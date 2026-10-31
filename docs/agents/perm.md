# Perm Cog / Store

- 文件：`cogs/perm.py`、`perm.py`
- 配置：`perm.enabled`
- 数据：`perm.yaml`（`PermStore`，挂在 `bot.perm_store`）
- 指令：`/perm add|rm|show`
- 权限：`_perm_permission`（config admin 或服务器管理员）、`_perm_show_permission`

## 规则模型

`PermRule`：

- `users`、`roles`、`module`、`command`、`global_scope`、`guild_id`。
- `module` 与 `command` 都为空 → mod 授权。

## 注意

- `config.yaml` 的 `admins` / `mods` 始终优先，`/perm` 只能补充。
- `cogs/perm.py` 初始化时通过 `u.set_perm_store()` / `u.set_bot_guild_lookup()` 注册全局引用。
- `module` 自动补全来自 `u.list_cog_names()`。
- 规则文件由 `PermStore._save()` 写入，避免手动编辑格式。
