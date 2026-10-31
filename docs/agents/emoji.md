# Emoji Cog

- 文件：`cogs/emoji.py`
- 配置：`emoji.enabled` + `emoji.base_url` / `emoji.max_results`
- 指令：`/e`、`/emoji info`、`/emoji update`
- 限速：全局 `ratelimit`，模块名 `emoji`，指令 `e` / `emoji info` / `emoji update`

## 实现

- `on_ready` 拉取 `base_url/emoji.json`，缓存名称用于搜索 / 自动补全。
- 发送时下载 `base_url/<name>` 并作为文件发送，走顶层 `proxy`。
- `/emoji update` 需要 `u.Permission.ADMIN`，审计 `emoji-update`。

## 注意

- 远程源不可达时返回明确错误，不要让自动补全抛异常。
- `max_results` 过大会导致 Discord autocomplete 调用失败。
- 新增指令时在 `_check_rate_limit()` 传入 `emoji` 模块与完整指令名。
