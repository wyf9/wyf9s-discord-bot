# 模块总览

机器人由多个模块组成，均通过 `config.yaml` 中的 `enabled` 开关**按需启用**（默认全部关闭）。模块分为三类：

- **指令模块**：注册斜杠 / 前缀命令供用户调用（使用 discord.py Cog 架构）。
- **事件模块**：无指令，监听 Discord 事件（如 `on_message`）自动执行。
- **服务模块**：无指令，为其他模块提供共享能力（如审计日志）。

## 模块清单

| 模块 | 配置键 | 类型 | 指令 | 文档 |
| --- | --- | --- | --- | --- |
| 工具 / 管理 | `tools` | 指令 | `random` `uuid` `to-file` `delete` `clear-message` `move-channel` | [查看](/modules/tools) |
| 表情 | `emoji` | 指令 | `/e` `/emoji info` `/emoji update` | [查看](/modules/emoji) |
| 频道锁定 | `lock` | 指令 | `/lock now` `/lock unlock` `/lock plan` `/lock unplan` | [查看](/modules/lock) |
| 语音频道 | `voicechannel` | 指令 | `/vc join` `/vc leave` | [查看](/modules/voice) |
| 管理指令 | — | 指令 | `/sync` `/reload` | [查看](/modules/admin) |
| 动态权限 | `perm` | 指令 | `/perm add` `/perm rm` `/perm show` | [查看](/modules/perm) |
| 公告推送 | `announce` | 指令 | `/subscribe` | [查看](/modules/announce) |
| 聊天增强 | `chatenhance` | 指令 / 事件 | `/enhance enable` `/enhance disable` `/enhance list` | [查看](/modules/chatenhance) |
| 多语言 | —（始终启用） | 指令 | `/lang` | [查看](/modules/lang) |
| 自动管理 | `rmmsg` / `rmtodo` | 事件 | 无 | [查看](/modules/manage) |
| 反垃圾 | `antispam` | 事件 | 无 | [查看](/modules/antispam) |
| 审计日志 | `audit` | 服务 | 无 | [查看](/modules/audit) |

## 指令速查表

| 指令 | 模块 | 权限 | 限速 | 说明 |
| --- | --- | --- | --- | --- |
| `/random` | tools | 所有人 | ✅ | 生成范围随机数 |
| `/uuid` | tools | 所有人 | ✅ | 生成 UUID（私密消息） |
| `/to-file` | tools | 所有人 | ✅ | 文本转文件发送 |
| `/delete` | tools | Mod | — | 删除单条消息 |
| `/clear-message` | tools | Mod | — | 按条件批量清理消息 |
| `/move-channel` | tools | Mod | — | 移动频道位置 / 分类 |
| `/e` | emoji | 所有人 | — | 发送库中表情包 |
| `/emoji info` | emoji | 所有人 | — | 查看表情库信息 |
| `/emoji update` | emoji | Admin | — | 更新表情库数据 |
| `/lock now` | lock | Mod | — | 锁定频道 |
| `/lock unlock` | lock | Mod | — | 解锁频道 |
| `/lock plan` | lock | Mod | — | 计划锁定 / 解锁 |
| `/lock unplan` | lock | Mod | — | 取消计划 |
| `/vc join` | voice | 白名单 / Mod | — | 机器人加入语音频道 |
| `/vc leave` | voice | 白名单 / Mod | — | 机器人离开语音频道 |
| `/sync` | admin | 配置管理员 | — | 同步斜杠指令列表 |
| `/reload` | admin | Admin | 15s CD | 热重载模块 |
| `/perm add` | perm | Admin | — | 添加权限规则 |
| `/perm rm` | perm | Admin | — | 删除权限规则 |
| `/perm show` | perm | Admin | — | 查看权限规则 |
| `/subscribe` | announce | Mod | — | 关注公告频道 |
| `/enhance enable` | chatenhance | Admin | — | 启用聊天增强功能 |
| `/enhance disable` | chatenhance | Admin | — | 禁用聊天增强功能 |
| `/enhance list` | chatenhance | Admin | — | 查看聊天增强功能状态 |
| `/lang` | lang | 所有人（server 范围需管理权限） | ✅ | 切换 / 查看语言偏好 |

> 权限体系详见[权限系统](/guide/permissions)，限速详见[限速与 Rate Limit](/guide/rate-limit)。

## 双命令模式

所有指令模块均可通过 `slash` / `prefix` 开关分别控制斜杠命令与前缀命令的注册。前缀命令的前缀由顶层 `command_prefix` 决定（示例配置为 `//`）。

- 斜杠命令示例：`/random 1 100`
- 前缀命令示例：`//random 1 100`

复杂指令（`clear-message`、`lock plan`）的前缀形式使用 `--key=value` flag 传参，例如：

```text
//lock plan --channel=#公告 --lock-time=22-00 --unlock-time=08-00 --cycle=daily
```
