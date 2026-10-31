# 反垃圾 (antispam)

基于 `on_message` 事件的频道级反垃圾模块，**无指令**。为指定频道配置捕获规则，自动对触发者执行踢出 / 封禁 / 超时，并可清理其近期消息、公开通知、写入审计日志。

- **配置键**：`antispam`
- **源文件**：`cogs/antispam.py`（复用 `modules/clear_message.py` 的清理能力）

## 判定规则

对配置了规则的频道内的每条用户消息：

- 作者拥有 `ignored_roles` 中任一身份组时**跳过**。
- **陌生账号**：没有任何身份组，或其全部身份组都属于 `stranger_roles`。
- **疑似被盗账号**：其余情况。

两类账号分别执行 `spammer` / `hacked` 配置的动作，并可按 `clear_message` 清理其近期消息、按 `public_log` 在频道公开通知，结果写入[审计日志](/modules/audit)。

## 动作与所需权限

| 动作 | 含义 | 机器人所需 Discord 权限 |
| --- | --- | --- |
| `kick` | 踢出成员 | 踢出成员（Kick Members） |
| `ban` | 封禁成员 | 封禁成员（Ban Members） |
| `mute` / 分钟数 | 超时（默认 60 分钟，或指定分钟数） | 超时成员（Moderate Members / Timeout） |

::: warning 身份组层级
若机器人已拥有对应权限但操作仍被拒绝，几乎可以确定是**身份组层级问题**：目标的最高身份组不低于机器人最高身份组。此时需将机器人身份组拖到目标之上。这类失败会以「自动操作失败」记录到审计日志并说明原因。
:::

## 处理结果通知

- **疑似被盗（mute）**：会 @ 该用户，提示账号疑似被盗、已临时禁言、请联系管理员（中英双语）。
- **陌生账号（kick/ban）**：公开记录触发的 antispam 动作（中英双语）。由于成员被踢出 / 封禁后 @ 提及会随时间显示为「未知用户」，通知中会在提及后附上 `` (`用户名`) `` 以便日后辨认。
- 是否公开通知由 `public_log` 控制。
- 通知末尾会附带一条形如 `-# *(antispam-action/{user_id}/{action})*` 的标签，用于后续定位和撤销操作。

写入审计日志的触发消息会以转发形式保留消息副本（原消息被清理后图片 / 附件仍可访问），并附带撤销按钮与形如 `-# *(antispam-action/{user_id}/{action})*` 的标签。

## 撤销操作（解封 / 解禁）

审计日志卡片的按钮上，Mod/Admin 可以一键撤销 antispam 动作。撤销后，所有审计频道中含相同标签的卡片都会同步标记为已完成。

### 封禁 / 禁言的解除

- 点击 **取消封禁** / **解除禁言** 按钮：若已过期或已被手动解除，按钮变为 **已过期**（禁用）；否则执行解封 / 解除超时，按钮标记为 **已由 {mod} 处理**。
- 若 `public_log` 启用，公开通知会同步更新为：

```
🚨 Antispam triggered: <@user> (`name`) -> ~~Spammer/ban~~ -> **[Unban by moderator](audit-log-link)**
-# *(antispam-action/xxx/ban)*
```

- 公开日志中的 `**Unban by moderator**` 不显示具体是哪位 mod 操作的。
- 若 `unban_link` 启用且服务器配置了审计频道，挂载到审计消息的跳转链接；否则仅显示文本。

### 注意

- **踢出 (kick)** 动作无法撤销，其审计卡片不显示撤销按钮。
- 跨频道同步时会静默跳过权限不足 / 频道不存在的异常。

## 消息清理

`clear_message` 指定分钟数时，会清理该用户在**服务器范围**内最近 N 分钟的消息（含论坛帖子内消息与由该用户所作的整个帖子）。设为 `null` / `false` 则禁用。

## 配置

```yaml
antispam:
  enabled: false
  spam_catcher: {}        # 按频道配置的捕获规则
  # 示例:
  # 1514685631316496615:
  #   spammer: ban              # 陌生人处理: kick | ban
  #   hacked: mute              # 疑似被盗处理: kick | ban | mute | 分钟数
  #   clear_message: 3          # 自动清理窗口 (分钟, null/false 禁用)
  #   public_log: true          # 是否在频道公开通知
  #   unban_link: false         # 公开日志撤销时是否附加审计日志链接（需配置服务器审计频道）
  #   stranger_roles: [1318980288046698506, "新成员"]
  #   ignored_roles: ["管理员", "成员"]
```

### 顶层字段

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enabled` | `bool` | `false` | 是否启用反垃圾模块 |
| `spam_catcher` | `dict[频道ID, 规则]` | `{}` | 按频道配置的捕获规则 |

### 每条规则字段

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `spammer` | `kick` / `ban` | `ban` | 陌生账号处理方式 |
| `hacked` | `kick` / `ban` / `mute` / 分钟数(int) | `mute` | 疑似被盗账号处理方式 |
| `clear_message` | `int` / `null` / `false` | `3` | 清理消息窗口（分钟），`null`/`false` 禁用 |
| `public_log` | `bool` | `true` | 是否在频道公开通知处理结果 |
| `unban_link` | `bool` | `false` | 公开日志撤销时是否附加审计日志消息链接（需要服务器配置了审计频道） |
| `stranger_roles` | `list[int \| str]` | `[]` | 视为陌生账号的角色列表（身份组 ID 或名称） |
| `ignored_roles` | `list[int \| str]` | `[]` | 忽略处理的角色列表（拥有任一即跳过） |

- `spam_catcher` 的 key 为频道 ID（数字或字符串均可）。
- 角色列表项支持**身份组 ID** 或**身份组名称**（同名身份组会全部匹配）。
