# AntiSpam Cog

- 文件：`cogs/antispam.py`
- 清理实现：`modules/clear_message.py`
- 配置：`antispam.enabled` + `antispam.spam_catcher[channel_id]`
- 权限：无指令；靠 bot 的 Kick / Ban / Timeout 权限

## 规则

- `spammer`：无身份组，或全部身份组都属于 `stranger_roles`。
- `hacked`：其余账号，疑似被盗。
- `ignored_roles` 命中则跳过。
- `clear_message`（分钟）、`public_log`、`unban_link`。
- 角色列表支持身份组 ID / 名称，用 `_parse_role_ids()` 解析。

## 审计 / 撤销

- 审计日志和 `AntispamActionView` 在 `modules/audit.py`。
- 撤销通过标签搜索定位历史日志，不依赖数据库。
- 批量处理不要逐条写审计，统一写汇总或由 audit 服务合并。

## 注意

- 身份组层级不足会导致操作失败；失败要记录原因。
- 清理原消息前必须先完成审计转发 / snapshot。
- 新增自动操作时同步 audit action 与 lang 文案。
