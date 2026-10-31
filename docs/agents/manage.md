# Manage Cog

- 文件：`cogs/manage.py`
- 配置：`rmmsg`、`rmtodo`（任一启用即加载）
- 无指令，监听 `on_message`。

## 功能

- `rmmsg`：作者用户名匹配 `nicks`（`fnmatch` 通配符）时延迟删除消息。
- `rmtodo`：在 `todo_channels` 中删除指定 `author_id` 发送的无 embed 消息，延迟 `remove_delay` 秒。

## 注意

- 需要 **Manage Messages**。
- 删除失败用日志记录，不要刷屏审计。
- 新增配置必须同步 `config.py` / `config.example.yaml` / 用户文档。
