# Chat Enhance (chatenhance)

Chat enhance module: automatically processes messages via the `on_message` event and provides server-level feature toggles.

- **Config key**: `chatenhance`
- **Commands**: `/enhance enable` `/enhance disable` `/enhance list`
- **Source file**: `cogs/chatenhance.py`

::: tip Enable conditions
The module only loads when `chatenhance.enabled: true`. Features are **disabled** per server by default; a server admin must explicitly enable them via `/enhance enable`.
:::

## Feature toggle commands

| Command | Permission | Description |
| --- | --- | --- |
| `/enhance enable <function>` | Admin | Enable a function for the current server |
| `/enhance disable <function>` | Admin | Disable a function for the current server |
| `/enhance list` | Admin | List the status of each function in the current server |

Available functions:

| Function | Config key | Description |
| --- | --- | --- |
| `autofixupx` | `chatenhance.autofixupx` | Automatically convert X / Twitter tweet links |

Function toggles are stored per server in `enhance_settings.yaml` (in the [data directory](/en/guide/getting-started#data-directory)). The commands require server admin (`administrator` permission) or membership in the config `admins` list.

## autofixupx — auto-convert tweet links

When someone in the server sends an `x.com` / `twitter.com` tweet link (in `/status/<id>` format), the bot automatically replies with the converted form.

- `fixupx` mode: replies with a `fixupx.com` link so Discord can preview the tweet in chat.
- `x-to-img` mode: calls the [x-to-img](https://github.com/recloudstudio/x-to-img) API to render the tweet as an image and sends it (requires `x_to_img_url`).
- `both` mode: sends both the image and the fixupx link; without `x_to_img_url` only the fixupx link is sent, with a warning appended at the end of the message.
- `limit` caps how many links are converted per message (default `2`).
- In `fixupx` / `both` mode, messages that already contain `fixupx.com` / `fxtwitter.com` links (already converted) do not trigger.
- Bot messages and webhook messages never trigger.

### Configuration

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

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `enabled` | `bool` | `false` | Whether to enable the module |
| `slash` | `bool` | `true` | Whether to register slash commands |
| `prefix` | `bool` | `true` | Whether to register prefix commands |
| `autofixupx.mode` | enum | `fixupx` | Conversion mode: `fixupx` / `x-to-img` / `both` |
| `autofixupx.x_to_img_url` | `str \| null` | `null` | x-to-img API base URL (no trailing `/`; its `/api/convert` is called) |
| `autofixupx.theme` | enum | `light` | x-to-img image theme: `light` / `dim` / `dark` |
| `autofixupx.api_token` | `str \| null` | `null` | Optional Bearer token for x-to-img (needed if the server enables `API_TOKEN`) |
| `autofixupx.limit` | `int` | `2` | Max links converted per message |

### x-to-img service

[x-to-img](https://github.com/recloudstudio/x-to-img) is a separate open-source service that can be deployed to Cloudflare Workers / Deno Deploy. After deploying, put its root URL in `x_to_img_url`. If the server enables `API_TOKEN`, configure the matching Bearer token in `api_token`.
