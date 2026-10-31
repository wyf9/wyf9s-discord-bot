# 语音频道 (voice)

让机器人加入 / 离开语音频道，支持 DAVE 加密与断线自动重连。

- **配置键**：`voicechannel`
- **源文件**：`cogs/voice.py`

## 权限判定（特殊）

语音指令使用**自定义权限判定**，而非普通的 Mod / Admin 等级：

- 若 `allowed_users` **为空**：仅 Mod（含 Admin）可用。
- 若 `allowed_users` **非空**：白名单用户**或** Mod 均可用。

白名单项可以是用户 ID 或用户名。还支持通过 `allowed_guilds` 按服务器配置白名单。

## 指令

### `vc join` — 加入语音频道

让机器人加入你当前所在的语音频道，或指定频道。

| 项目 | 说明 |
| --- | --- |
| 权限 | 白名单用户 / Mod |
| 参数 | `channel`（可选，留空则使用你当前所在语音频道）、`persist`（可选，持久化会话） |
| 机器人权限 | 连接（Connect） |
| 限速 | ✅ 受限 |
| 审计 | ✅ 记录（`joinvc`） |

行为细节：

- 加入时机器人自动 **self-deaf + self-mute**（自闭麦 / 自静音）。
- 若机器人已在其他频道，会先断开再加入目标频道（提示「已移动到」）。
- 若已在目标频道，提示「已经在里面了」。
- 若频道要求 **DAVE 加密** 但连接失败（错误码 4017），会提示相应错误。
- 不支持讲堂频道（StageChannel）作为「你当前所在频道」自动加入。

### `vc leave` — 离开语音频道

让机器人离开当前所在语音频道。

| 项目 | 说明 |
| --- | --- |
| 权限 | 白名单用户 / Mod |
| 限速 | ✅ 受限 |
| 审计 | ✅ 记录（`leavevc`） |

- 若机器人未在任何语音频道会提示。

## 断线重连

当机器人意外断开语音连接时（如网络波动、Discord 服务端异常、被管理员移除等），会自动尝试重新连接。

### 重连策略

- 采用**指数退避**：初始 5 秒，每次失败后翻倍，上限为 `reconnect_max_delay`（默认 300 秒）。
- 每次重连前会检查频道是否存在、机器人是否有 Connect 权限。
- 若频道已被删除或不再是语音频道，停止重连。
- 若机器人已通过其他方式重新连接到同一频道，停止重连。

### 持久化模式 (`persist`)

`vc join` 的 `persist` 参数控制断线后的行为：

| 场景 | `persist=false`（默认） | `persist=true` |
| --- | --- | --- |
| 网络 / Discord 异常断连 | 自动重连 | 自动重连 |
| 被管理员断开 | **不**重连 | 自动重连，并在语音频道发送提示 |
| 使用 `/vc leave` 离开 | **不**重连 | **不**重连 |
| 缺少 Connect 权限 | 指数退避重试 | 指数退避重试 |

当 `persist=true` 且被管理员断开时，重连后会在语音频道发送提示消息，告知管理员使用 `/vc leave` 或 `{前缀}vc leave` 指令来让机器人离开。

::: tip 持久化数据
`persist=true` 的会话信息保存在数据目录的 `voice.yaml` 中，机器人重启后会自动恢复连接。
:::

## 配置

```yaml
voicechannel:
  enabled: false
  slash: true
  prefix: true
  allowed_users: []           # 留空: 仅 mod 可用; 非空: 白名单用户 + mod 可用
  allowed_guilds: {}           # 按服务器白名单 { guild_id: [user...] }
  reconnect: true             # 断线后是否自动重连
  reconnect_max_delay: 300    # 指数退避最大间隔 (秒)
```

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enabled` | `bool` | `false` | 是否启用语音模块 |
| `slash` | `bool` | `true` | 是否注册斜杠指令 |
| `prefix` | `bool` | `true` | 是否注册前缀指令 |
| `allowed_users` | `list[int \| str]` | `[]` | 语音指令白名单（用户 ID / 用户名） |
| `allowed_guilds` | `dict[int \| str, list[int \| str]]` | `{}` | 按服务器配置的白名单 |
| `reconnect` | `bool` | `true` | 断线后是否自动重连（含 Discord 内部重连失败后的主动重连） |
| `reconnect_max_delay` | `int` | `300` | 断线重连指数退避最大间隔（秒） |

::: tip DAVE 加密
DAVE（Discord Audio & Video End-to-End Encryption）依赖 `davey` 与 `PyNaCl`，已包含在项目依赖中（`discord-py[voice]`）。
:::
