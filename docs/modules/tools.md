# 工具 / 管理 (tools)

提供常用工具与管理指令：随机数 / UUID 生成、消息删除、批量清理消息、频道移动、文本转文件、指令同步。

- **配置键**：`tools`
- **源文件**：`cogs/tools.py`（批量清理逻辑在 `modules/clear_message.py`）

## 指令

### `random` — 生成随机数

生成指定范围内的随机整数。

| 项目 | 说明 |
| --- | --- |
| 权限 | 所有人 |
| 限速 | ✅ 受限 |
| 参数 | `min_num`（默认 `1`）、`max_num`（默认 `114514`） |

- 若 `min_num > max_num` 会自动交换。
- 斜杠：`/random min_num:1 max_num:100`；前缀：`//random 1 100`

### `uuid` — 生成 UUID

生成一个随机 UUID，以 **私密消息（ephemeral）** 发送，并在延迟后自动删除。

| 项目 | 说明 |
| --- | --- |
| 权限 | 所有人 |
| 限速 | ✅ 受限 |
| 参数 | `delete_after`（删除延迟秒数，默认 `secret_message_delay` = 600） |

- 前缀命令中 `delete_after <= 0` 时使用默认值。

### `to-file` — 文本转文件

将文本内容以文件形式发送。

| 项目 | 说明 |
| --- | --- |
| 权限 | 所有人 |
| 参数 | `name`（文件名）、`content`（文件内容） |
| 限速 | ✅ 受限 |
| 审计 | ✅ 记录（`to-file`） |

- 前缀：`//to-file 文件名.txt 剩余内容作为文件正文`（`content` 为剩余全部文本）。

### `delete` — 删除消息

删除**当前频道**中指定 ID 的单条消息。

| 项目 | 说明 |
| --- | --- |
| 权限 | Mod |
| 参数 | `message_id`（消息 ID）、`show_to_public`（是否公开显示结果，默认 `false`） |
| 机器人权限 | 管理消息（Manage Messages） |
| 审计 | ✅ 记录（`delete`） |

- 错误处理：权限不足 / 找不到消息 / ID 非整数等都会返回明确提示。

### `clear-message` — 批量清除消息

按多种过滤条件批量清除消息，支持单频道或整个服务器。

| 项目 | 说明 |
| --- | --- |
| 权限 | Mod |
| 机器人权限 | 管理消息（Manage Messages）；读取历史消息 |
| 审计 | ✅ 记录（`clear-message`） |

#### 参数

| 参数 | 说明 |
| --- | --- |
| `user` | 目标用户（单个，选择器） |
| `user_ids` | 目标用户 ID 列表（逗号分隔） |
| `webhook_ids` | 目标 Webhook ID 列表（逗号分隔） |
| `nick_pattern` | 昵称通配符（fnmatch，如 `*bot*`） |
| `content_pattern` | 消息内容通配符（fnmatch，如 `*error*`） |
| `message_count` | 每个频道最多检查多少条消息（不填 / 0 = 不限制但较慢） |
| `within_minutes` | 仅清除最近几分钟内的消息（不填 / 0 = 不限制） |
| `scope` | 范围：`channel`（单频道，默认）或 `server`（整个服务器） |
| `channel` | 指定频道（仅 `scope=channel` 时生效，默认当前频道；**可指定论坛频道**） |
| `start` | 起始范围：消息 ID / **帖子 ID** 或时间（`30m` / `2h` / `1d` / ISO 时间） |
| `end` | 结束范围：消息 ID / **帖子 ID** 或时间 |
| `delete_threads` | 是否直接删除由目标用户所作的**整个帖子**（默认 `false`） |
| `forum_scan_count` | 每个论坛频道扫描多少帖子（按最近活跃排序；不填则继承消息数 / 时间限制） |

#### 论坛 / 帖子清理

- **清理帖子内消息**：目标频道为论坛（或 `scope=server`）时，会扫描论坛帖子并删除其中匹配的消息，用 `forum_scan_count` 控制每个论坛扫描多少帖子。
- **删除整个帖子**：`delete_threads=true` 时，由目标用户所作且匹配过滤条件的整个帖子会被删除，**连带删除帖子内的所有消息**，因此默认关闭。
- **用帖子 ID 指定范围**：`start` / `end` 也接受帖子 ID，按帖子创建时间筛选，需同时设置 `delete_threads=true`。

#### 约束

- `start`/`end` 不能与 `within_minutes`/`message_count` **同时使用**。
- 若不使用时间范围，`message_count` 与 `within_minutes` 至少设置一个。
  - **特例**：`delete_threads=true` 且指定了 `forum_scan_count` 时，`forum_scan_count` 本身即作为限制，无需再设置 `message_count`/`within_minutes`。此时**只扫描论坛帖子、不扫描普通频道消息**：显式指定论坛频道则只处理该论坛，否则处理服务器内所有论坛。
- 若无任何范围限制，则必须至少提供一种匹配过滤条件。
- **超过 14 天的消息无法批量删除**（Discord 限制）。当这类消息数量不超过 `tools.clear_single_delete_max`（默认 `20`，`0` 禁用）时，会自动回退为逐条删除；超出阈值则单独计为「因超过 14 天不可删」。
- 机器人自己发出的、带 `[clear-message]` 标记的结果消息会被自动跳过，避免误删。

#### 前缀命令 flag

前缀模式用 `--key=value` 传参：

```text
//clear-message --user=@某人 --within=30m
//clear-message --nick="*bot*" --scope=server --count=500
//clear-message --content="*spam*" --start=1d --end=2h
//clear-message --user=@某人 --channel=<论坛频道> --within=7d --delete-threads=true --forum-scan-count=100
//clear-message --user=@某人 --delete-threads=true --forum-scan-count=100   # 扫描服务器内所有论坛
//clear-message --user=@某人 --start=<帖子ID> --end=<帖子ID> --delete-threads=true
```

- 支持别名：`--user-ids` / `--webhook-ids` / `--nick`(=`--nick-pattern`) / `--content`(=`--content-pattern`) / `--count` / `--within` / `--scope` / `--channel` / `--start` / `--end` / `--delete-threads` / `--forum-scan-count`(=`--forum-scan`)
- `--within` 支持 `30m` / `2h` / `1d` 或纯分钟数。
- `--delete-threads=true` 才会删除整个帖子（需显式开启）。

#### 结果消息 OK 按钮

清理结果消息附带一个 **OK 按钮**，点击可删除该结果消息（点击者需与指令相同的 Mod 权限）。

### `move-channel` — 移动频道

将当前或指定频道移动到某分类，或某频道之前 / 之后。

| 项目 | 说明 |
| --- | --- |
| 权限 | Mod |
| 机器人权限 | 管理频道（Manage Channels），且身份组层级足够 |
| 审计 | ✅ 记录（`move-channel`） |

#### 参数

| 参数 | 说明 |
| --- | --- |
| `target_channel` | 要操作的频道（默认当前频道） |
| `category` | 目标分类 |
| `before` | 移动到此频道之前 |
| `after` | 移动到此频道之后 |
| `sync_perm` | 是否同步目标分类权限（默认 `true`） |

- 必须至少提供 `category` / `before` / `after` 之一。
- `before` 与 `after` 不能同时指定。
- 前缀命令仅支持 `target_channel` 与 `category` 两个位置参数。

::: tip `/sync` 已迁移至 [管理指令](/modules/admin)
指令同步 `/sync` 和热重载 `/reload` 现在由 `cogs/admin.py` 提供。
:::

## 配置

```yaml
tools:
  enabled: false
  slash: true
  prefix: true
```

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enabled` | `bool` | `false` | 是否启用工具模块 |
| `slash` | `bool` | `true` | 是否注册斜杠指令 |
| `prefix` | `bool` | `true` | 是否注册前缀指令 |
