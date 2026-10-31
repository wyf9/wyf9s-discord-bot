# ChatEnhance Cog

- 文件：`cogs/chatenhance.py`
- 配置：`chatenhance.enabled` + `chatenhance.autofixupx`
- 存储：`enhance_store.py` / `enhance_settings.yaml`
- 指令：`/enhance enable|disable|list`
- 权限：服务器管理员或 config admin（`_enhance_admin_permission`）

## 行为

- `on_message` 监听 X / Twitter 链接并自动转换。
- `mode`：`fixupx` / `x-to-img` / `both`。
- 已包含 `fixupx.com` / `fxtwitter.com` 时不再处理。
- 忽略 bot 消息与 Webhook 消息。

## 注意

- 功能按服务器存储，模块启用 ≠ 所有服务器启用。
- 远程 x-to-img 请求要处理失败与超时，不要阻塞消息处理。
- 修改功能名时要同步 `enhance_store` 与 `/enhance` choices / lang。
