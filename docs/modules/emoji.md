# 表情 (emoji)

从远程表情源浏览、搜索并发送表情包（以文件 / 贴纸形式），并可查看表情源的构建信息。

- **配置键**：`emoji`
- **源文件**：`cogs/emoji.py`

## 指令

### `/e` — 发送表情包

从表情库中选择并发送一个表情包。

| 项目 | 说明 |
| --- | --- |
| 权限 | 所有人 |
| 参数 | `name`（表情名称，斜杠命令带**自动补全**） |

- 斜杠命令输入时会根据当前输入模糊匹配，最多返回 `max_results` 个候选。
- 若名称不在库中会提示「Invalid emoji name」。

### `/emoji info` — 表情库信息

查看表情源的构建信息。

| 项目 | 说明 |
| --- | --- |
| 权限 | 所有人 |

返回信息包括：构建时间、是否在 CF Pages 构建、Commit ID / 分支、表情数量、表情源 `emoji.json` 链接。

### `/emoji update` — 更新表情库

重新从远程拉取表情清单并刷新缓存。

| 项目 | 说明 |
| --- | --- |
| 权限 | **Admin** |
| 审计 | ✅ 记录（`emoji-update`） |

成功后返回构建时间、Commit、表情数量。

## 配置

```yaml
emoji:
  enabled: false
  slash: true
  prefix: true
  base_url: "https://ghimg.siiway.top/emoji"
  max_results: 25
```

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enabled` | `bool` | `false` | 是否启用表情模块 |
| `slash` | `bool` | `true` | 是否注册斜杠指令 |
| `prefix` | `bool` | `true` | 是否注册前缀指令 |
| `base_url` | `str` | `https://ghimg.siiway.top/emoji` | 表情源基础 URL（末尾不加 `/`，目录需含 `emoji.json`） |
| `max_results` | `int` | `25` | 搜索 / 自动补全最大结果数（过大可能导致调用失败） |

::: tip
表情图片请求会使用顶层 `proxy` 配置。若远程源不可达，发送表情会返回 fetch 错误。
:::
