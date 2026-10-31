# Lang Cog

- 文件：`cogs/lang.py`
- 相关：`i18n.py`、`lang_store.py`、`lang/*.yaml`
- 配置键：无（始终启用）
- 指令：`/lang`

## 行为

- `scope=user`：设置 / 查看个人语言。
- `scope=server`：设置 / 查看服务器语言，需要管理服务器权限或 config admin。
- 语言优先级：用户 > 服务器 > `zh`。

## 注意

- 新增语言时必须同步 `SUPPORTED_LANGS`、locale 映射与语言文件。
- 服务器 scope 修改需要审计 `lang-server`；用户 scope 不审计。
