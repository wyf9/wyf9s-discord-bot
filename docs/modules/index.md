# 模块总览

机器人由多个模块组成，均通过 `config.yaml` 中的 `enabled` 开关**按需启用**（默认全部关闭）。模块分为三类：

- **指令模块**：注册斜杠 / 前缀命令供用户调用（使用 discord.py Cog 架构）。
- **事件模块**：无指令，监听 Discord 事件（如 `on_message`）自动执行。
- **服务模块**：无指令，为其他模块提供共享能力（如审计日志）。

## 模块清单

| 模块 | 配置键 | 类型 | 指令 |
| --- | --- | --- | --- |
| [工具 / 管理](/modules/tools) | `tools` | 指令 | `random` `uuid` `to-file` `delete` `clear-message` `move-channel` |
| [表情](/modules/emoji) | `emoji` | 指令 | `/e` `/emoji info` `/emoji update` |
| [频道锁定](/modules/lock) | `lock` | 指令 | `/lock now` `/lock unlock` `/lock plan` `/lock unplan` |
| [语音频道](/modules/voice) | `voicechannel` | 指令 | `/vc join` `/vc leave` |
| [管理指令](/modules/admin) | — | 指令 | `/sync` `/reload` |
| [动态权限](/modules/perm) | `perm` | 指令 | `/perm add` `/perm rm` `/perm show` |
| [公告推送](/modules/announce) | `announce` | 指令 | `/subscribe` |
| [聊天增强](/modules/chatenhance) | `chatenhance` | 指令 / 事件 | `/enhance enable` `/enhance disable` `/enhance list` |
| [多语言](/modules/lang) | —（始终启用） | 指令 | `/lang` |
| [自动管理](/modules/manage) | `rmmsg` / `rmtodo` | 事件 | 无 |
| [反垃圾](/modules/antispam) | `antispam` | 事件 | 无 |
| [审计日志](/modules/audit) | `audit` | 服务 | 无 |

## 指令速查表

| 指令 | 权限 | 限速 | 说明 |
| --- | --- | --- | --- |
| `/random` | 所有人 | 按指令额度 | 生成范围随机数 |
| `/uuid` | 所有人 | 按指令额度 | 生成 UUID（私密消息） |
| `/to-file` | 所有人 | 按指令额度 | 文本转文件发送 |
| `/delete` | Mod | — | 删除单条消息 |
| `/clear-message` | Mod | — | 按条件批量清理消息 |
| `/move-channel` | Mod | — | 移动频道位置 / 分类 |
| `/e` | 所有人 | 按模块额度 | 发送库中表情包 |
| `/emoji info` | 所有人 | 按指令额度 | 查看表情库信息 |
| `/emoji update` | Admin | 按指令额度 | 更新表情库数据 |
| `/lock now` | Mod | — | 锁定频道 |
| `/lock unlock` | Mod | — | 解锁频道 |
| `/lock plan` | Mod | — | 计划锁定 / 解锁 |
| `/lock unplan` | Mod | — | 取消计划 |
| `/vc join` | 白名单 / Mod | 按指令额度 | 机器人加入语音频道 |
| `/vc leave` | 白名单 / Mod | 按指令额度 | 机器人离开语音频道 |
| `/sync` | Admin | — | 同步斜杠指令列表 |
| `/reload` | Admin | 15s CD | 热重载模块 |
| `/perm add` | Admin | — | 添加权限规则 |
| `/perm rm` | Admin | — | 删除权限规则 |
| `/perm show` | Admin | — | 查看权限规则 |
| `/subscribe` | Mod | — | 关注公告频道 |
| `/enhance enable` | Admin | — | 启用聊天增强功能 |
| `/enhance disable` | Admin | — | 禁用聊天增强功能 |
| `/enhance list` | Admin | — | 查看聊天增强功能状态 |
| `/lang` | 所有人（server 范围需管理权限） | — | 切换 / 查看语言偏好 |

> 限速额度在 `config.yaml` 的 `ratelimit` 中配置，详见[限速](/guide/rate-limit)；权限体系详见[权限系统](/guide/permissions)。

## 双命令模式

所有指令模块均可通过 `slash` / `prefix` 开关分别控制斜杠命令与前缀命令的注册。前缀命令的前缀由顶层 `command_prefix` 决定（示例配置为 `//`）。

- 斜杠命令示例：`/random 1 100`
- 前缀命令示例：`//random 1 100`

复杂指令（`clear-message`、`lock plan`）的前缀形式使用 `--key=value` flag 传参，例如：

```text
//lock plan --channel=#公告 --lock-time=22-00 --unlock-time=08-00 --cycle=daily
```
