# 聊天增强 (chatenhance)

聊天增强模块：基于 `on_message` 事件自动处理消息，并提供服务器级的功能开关指令。

- **配置键**：`chatenhance`
- **指令**：`/enhance enable` `/enhance disable` `/enhance list`
- **源文件**：`cogs/chatenhance.py`

::: tip 启用条件
`chatenhance.enabled: true` 时模块才会加载。功能默认对每个服务器**禁用**，需由服务器管理员通过 `/enhance enable` 显式启用。
:::

## 功能开关指令

| 指令 | 权限 | 说明 |
| --- | --- | --- |
| `/enhance enable <function>` | Admin | 为当前服务器启用功能 |
| `/enhance disable <function>` | Admin | 为当前服务器禁用功能 |
| `/enhance list` | Admin | 查看当前服务器各功能的状态 |

当前可用功能：

| 功能 | 配置键 | 说明 |
| --- | --- | --- |
| `autofixupx` | `chatenhance.autofixupx` | 自动转换 X / Twitter 推文链接 |

功能开关按服务器存储于 `enhance_settings.yaml`（位于[数据目录](/guide/getting-started#数据目录)）。指令权限要求为服务器管理员（拥有 `administrator` 权限）或配置中的 `admins` 名单。

## autofixupx — 自动转换推文链接

当服务器中有人发送 `x.com` / `twitter.com` 的推文链接（`/status/<id>` 格式）时，机器人自动回复转换后的内容。

- `fixupx` 模式：回复 `fixupx.com` 链接，Discord 即可在聊天内预览推文。
- `x-to-img` 模式：调用 [x-to-img](https://github.com/recloudstudio/x-to-img) API 将推文渲染为图片并发送（需要配置 `x_to_img_url`）。
- `both` 模式：同时发送图片与 fixupx 链接；未配置 `x_to_img_url` 时仅发送 fixupx 链接，并在消息末尾附带警告。
- `limit` 限制单条消息最多转换几个链接（默认 `2`）。
- 模式为 `fixupx` / `both` 时，若消息中已包含 `fixupx.com` / `fxtwitter.com` 链接（说明已转换过），则不再触发。
- 机器人自身消息与 Webhook 消息不会触发。

### 配置

```yaml
chatenhance:
  enabled: false
  slash: true
  prefix: true
  autofixupx:
    mode: "fixupx"
    x_to_img_url: null
    theme: "light"
    api_token: null
    limit: 2
```

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enabled` | `bool` | `false` | 是否启用模块 |
| `slash` | `bool` | `true` | 是否注册斜杠指令 |
| `prefix` | `bool` | `true` | 是否注册前缀指令 |
| `autofixupx.mode` | 枚举 | `fixupx` | 转换方式：`fixupx` / `x-to-img` / `both` |
| `autofixupx.x_to_img_url` | `str \| null` | `null` | x-to-img API 地址（末尾不带 `/`，调用其 `/api/convert`） |
| `autofixupx.theme` | 枚举 | `light` | x-to-img 图片主题：`light` / `dim` / `dark` |
| `autofixupx.api_token` | `str \| null` | `null` | x-to-img 可选 Bearer token（服务端启用了 `API_TOKEN` 时需要） |
| `autofixupx.limit` | `int` | `2` | 一条消息最多转换的链接数 |

### x-to-img 服务

[x-to-img](https://github.com/recloudstudio/x-to-img) 是独立的开源服务，支持部署到 Cloudflare Workers / Deno Deploy。部署后将其根地址填入 `x_to_img_url` 即可。若服务端启用了 `API_TOKEN`，需在 `api_token` 中配置对应的 Bearer token。
