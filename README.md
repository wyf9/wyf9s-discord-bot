# wyf9s-discord-bot

多功能 Discord 机器人，基于 discord.py 构建，使用 YAML + Pydantic 配置验证。模块使用 discord.py Cog 架构，支持热重载。内置多语言（i18n）支持，可按用户 / 服务器切换语言。

## 功能模块

| 模块 | 说明 |
| --- | --- |
| 工具 (`tools`) | 随机数 / UUID 生成、消息删除、批量清理消息、频道移动、内容导出为文件 |
| 表情 (`emoji`) | 远程表情包浏览 / 搜索 / 发送、表情源构建信息、表情库更新 |
| 频道锁定 (`lock`) | 锁定 / 解锁频道，支持单次 / 每日 / 每周 / 每月计划锁定 |
| 语音频道 (`voice`) | 机器人加入 / 离开语音频道，支持 DAVE 加密 |
| 自动管理 (`manage`) | 按昵称模式自动删消息、自动删除指定频道中特定 bot 的无嵌入消息 |
| 反垃圾 (`antispam`) | 频道级反垃圾规则、自动处置、消息清理与审计日志 |
| 审计日志 (`audit`) | 管理操作、自动处置与错误的全局 / 按服务器审计记录 |
| 管理 (`admin`) | 指令同步、模块 / 配置热重载 |
| 动态权限 (`perm`) | 基于 `perm.yaml` 的动态权限管理，`config.yaml` 始终优先 |
| 公告推送 (`announce`) | 关注公告频道并由 Discord 自动转发消息 |
| 聊天增强 (`chatenhance`) | 服务器级功能开关指令；自动将 X/Twitter 链接转为可预览形式 (fixupx / x-to-img) |
| 多语言 (`lang`) | 按用户 / 服务器切换语言偏好 |

## 文档

- 项目介绍：[文档首页](https://dc-bot.wyf9.top/) / [项目介绍](https://dc-bot.wyf9.top/guide/introduction)
- 快速开始与部署：[快速开始](https://dc-bot.wyf9.top/guide/getting-started)
- 配置说明：[配置指南](https://dc-bot.wyf9.top/guide/configuration)
- 权限系统：[权限系统](https://dc-bot.wyf9.top/guide/permissions)
- 限速机制：[限速与 Rate Limit](https://dc-bot.wyf9.top/guide/rate-limit)
- 模块与指令：[模块总览](https://dc-bot.wyf9.top/modules/)
- 服务条款：[服务条款](https://dc-bot.wyf9.top/legal/tos)
- 隐私政策：[隐私政策](https://dc-bot.wyf9.top/legal/privacy)

## 许可

[MIT](https://github.com/wyf9/wyf9s-discord-bot/blob/main/LICENSE)
