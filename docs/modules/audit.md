# 审计日志 (audit)

一个**共享服务模块**，将**需要审计的操作**以嵌入（embed）形式记录到指定频道。**无指令**，被其他模块调用。

- **配置键**：`audit`
- **源文件**：`modules/audit.py`

## 记录范围

只记录**有意义的管理 / 服务器级操作**，避免无用日志占用空间：

- 带 **[ADMIN]** / **[MOD]** 标识的指令（如 `/delete`、`/lock`、`/reload`、`/perm`…）。
- **服务器 scope** 的修改 / 操作（如 `/lang scope:server`、`/vc join/leave`、`/move-channel`）。
- 自动化处置与错误（反垃圾自动踢 / ban / 禁言、斜杠命令错误）。

用户 scope 的普通指令（如 `/random`、`/uuid`、`/to-file`、`/lang`（用户范围））**不记录**。

## 日志发送位置

- **全局频道**：`global_channel`，所有服务器的操作都发送到这里。
- **按服务器频道**：`guilds` 中为对应服务器单独配置的频道。

两者**互不影响**：若同时配置，两个频道都会收到日志。机器人需要对日志频道拥有**发送消息 / 嵌入链接**权限。

## 日志内容

每条日志是一个 embed，包含（按配置语言显示）：

- **标题**：区分手动 / 自动操作、成功 / 失败（✅ / ❌ / 🚨 / ⚠️）。
- **操作（Action）**：如 `/delete`、`clear-message`、`antispam-auto-catch`。
- **执行者（Actor）**：提及 + 用户名 + ID。
- **服务器（Server）**、**频道（Channel）**（若有）。
- **详情（Detail）**：操作说明（上限 1024 字符）。
- **时间戳**（UTC）。

## 记录的操作

| 来源模块 | 操作名 |
| --- | --- |
| tools | `delete`、`clear-message`、`move-channel` |
| admin | `sync`、`reload`、`reload-all`、`reload-config` |
| emoji | `emoji-update` |
| lock | `lock`、`unlock`、`plan-lock`、`unplan-lock` |
| voice | `joinvc`、`leavevc` |
| perm | `perm-add`、`perm-rm` |
| announce | `subscribe` |
| lang | `lang-server`（仅服务器 scope 修改） |
| antispam | `antispam-auto-catch`（自动操作，含失败记录） |
| （全局错误处理） | `slash-error/<cmd>` |

## 多语言

支持中英双语。语言通过 `/lang` 命令设置（优先级：用户设置 > 服务器设置 > 默认 `zh`），详见 [lang 模块文档](lang.md)。

| 语言值 | 说明 |
| --- | --- |
| `zh` | 中文（默认） |
| `en` | English |

## 配置

```yaml
audit:
  enabled: false
  global_channel: null    # 全局日志频道 ID (null 禁用)
  guilds: {}              # 按服务器配置的日志频道
  # 示例 (仅频道 ID):
  #   123456789:  987654321
```

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enabled` | `bool` | `false` | 是否启用审计日志 |
| `global_channel` | `int \| null` | `null` | 全局日志频道 ID（`null` 禁用全局日志） |
| `guilds` | `dict` | `{}` | 按服务器配置，见下 |

### `guilds` 写法

key 为服务器 ID（数字或字符串），value 为频道 ID（数字）或对象 `{ channel: 频道ID }`。

```yaml
audit:
  enabled: true
  global_channel: 111111111111111111
  guilds:
    222222222222222222: 333333333333333333      # 简写: 仅频道 ID
    444444444444444444:
      channel: 555555555555555555
```

::: tip
若某模块启用但 `audit.enabled` 为 `false`，相关操作不会记录日志（模块仍正常工作）。
:::
