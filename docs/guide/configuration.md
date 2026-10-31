# 配置说明

配置文件为项目根目录下的 `config.yaml`（被 `.gitignore` 忽略），可参考 `config.example.yaml`。配置在启动时由 Pydantic 模型校验，字段的**事实来源**是 `config.example.yaml` 与 `config.py`。

## 顶层字段

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `token` | `str` | **必填** | 机器人 Token（可被 token 文件或 `--token` 参数覆盖，见下文） |
| `proxy` | `str \| null` | `null` | 代理地址（如 `http://localhost:11451`） |
| `command_prefix` | `str` | `\` | 前缀命令的前缀（示例配置为 `//`） |
| `secret_message_delay` | `int` | `600` | 私密消息删除延迟（秒），用于 `uuid` 等 |

## 配置与 token 的来源

启动时可通过命令行参数或环境变量指定配置文件与 token 的来源（命令行参数优先级高于环境变量）：

- `--config` / `-c`（`W9DCBOT_CONFIG`）— 指定配置文件路径（默认 `config.yaml`）
- `--token-file`（`W9DCBOT_TOKEN_FILE`）— 指定 token 文件路径（默认 `tk.yaml`，一个含 `token: xxx` 的 YAML）
- `--token`（`W9DCBOT_TOKEN`）— 直接指定 Bot Token
- `--data-dir`（`W9DCBOT_DATA_DIR`）— 运行时数据文件目录（默认 `./data/`）

Token 的优先级为：**`--token` / `W9DCBOT_TOKEN` > token 文件（`tk.yaml`）> `config.yaml` 中的 `token`**。因此可将敏感的 token 拆分到单独的 `tk.yaml`（已被 `.gitignore` 忽略），或在部署时通过参数 / 环境变量注入。详见[启动参数](/guide/getting-started#启动参数)。

## 数据目录

运行时可变的数据文件（`perm.yaml`、`lang_settings.yaml`、`schedules.yaml`）以及日志文件（`log.file`）默认存放在 `./data/`（可用 `--data-dir` / `W9DCBOT_DATA_DIR` 修改）。写入始终指向数据目录，读取时若数据目录中不存在则回退到主程序目录（兼容旧数据位置）。多实例部署时应为各实例指定独立的数据目录以避免数据互相干扰，详见[数据目录](/guide/getting-started#数据目录)。

## 日志 `log`

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `level` | 枚举 | `INFO` | 控制台日志级别：`DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `file` | `str \| null` | `logs/{time:YYYY-MM-DD}.log` | 日志文件路径（Loguru 格式，`null` 禁用；相对[数据目录](#数据目录)解析） |
| `file_level` | 枚举 \| `null` | `INFO` | 文件日志级别（`null` 则跟随 `level`） |
| `rotation` | `str \| int` | `1 days` | Loguru 轮转周期 |
| `retention` | `str \| int` | `3 days` | Loguru 保留时间 |

## 模块开关

每个指令模块都有以下通用开关：

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `enabled` | `false` | 是否启用该模块（默认全部关闭） |
| `slash` | `true` | 是否注册斜杠命令 |
| `prefix` | `true` | 是否注册前缀命令 |

各模块的专属配置：

- [工具 / 管理 `tools`](/modules/tools#配置) — 含限速配置
- [表情 `emoji`](/modules/emoji#配置)
- [频道锁定 `lock`](/modules/lock#配置)
- [语音频道 `voicechannel`](/modules/voice#配置)
- [自动管理 `rmmsg` / `rmtodo`](/modules/manage#配置)
- [反垃圾 `antispam`](/modules/antispam#配置)
- [聊天增强 `chatenhance`](/modules/chatenhance#配置)
- [审计日志 `audit`](/modules/audit#配置)

## 权限名单

```yaml
admins:
  users: []              # 配置管理员用户 ID / 用户名列表 (拥有所有指令权限)

mods:
  users: []              # 全局 mod 列表
  guilds: {}             # 按服务器 mod 配置
  # 示例:
  # guilds:
  #   123456789012345678:
  #     roles: ["Moderator", 987654321098765432]  # 身份组 ID / 名称
  #     users: ["wyf9", 12345]                    # 用户 ID / 用户名
  # 兼容旧格式: guilds: { 123456789012345678: ["wyf9", 12345] }
```

- 名单项可以是**用户 ID**（数字）或**用户名**（字符串），两者皆可匹配。
- `mods.guilds` 的 key 为服务器 ID（数字或字符串均可）。
- `mods.guilds.<server>.roles` 支持**身份组 ID / 名称**，拥有任一配置身份组的成员即为该服务器的 mod。
- 旧格式（直接写用户列表，如 `guilds: { 123: ["wyf9"] }`）仍然兼容，等同于只配置 `users`。

详见[权限系统](/guide/permissions)。

## 参考配置

<<< @/../config.example.yaml
