# Configuration

The configuration file is `config.yaml` in the project root (ignored by `.gitignore`); see `config.example.yaml` for reference. The configuration is validated by a Pydantic model at startup, and the **source of truth** for the fields is `config.example.yaml` and `config.py`.

## Top-level fields

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `token` | `str` | **required** | Bot token (can be overridden by a token file or the `--token` argument, see below) |
| `proxy` | `str \| null` | `null` | Proxy address (e.g. `http://localhost:11451`) |
| `command_prefix` | `str` | `\` | Prefix for prefix commands (the example config uses `//`) |
| `secret_message_delay` | `int` | `600` | Delay (seconds) before deleting private messages, used by `uuid` and others |

## Sources for config and token

At startup, you can specify the source of the configuration file and token via command-line arguments or environment variables (command-line arguments take precedence over environment variables):

- `--config` / `-c` (`W9DCBOT_CONFIG`) — specifies the configuration file path (default `config.yaml`)
- `--token-file` (`W9DCBOT_TOKEN_FILE`) — specifies the token file path (default `tk.yaml`, a YAML containing `token: xxx`)
- `--token` (`W9DCBOT_TOKEN`) — directly specifies the bot token
- `--data-dir` (`W9DCBOT_DATA_DIR`) — directory for runtime data files (default `./data/`)

The token priority is: **`--token` / `W9DCBOT_TOKEN` > token file (`tk.yaml`) > `token` in `config.yaml`**. This lets you split the sensitive token out into a separate `tk.yaml` (already ignored by `.gitignore`), or inject it via arguments / environment variables at deployment time. See [CLI arguments](/en/guide/getting-started) for details.

## Data directory

Mutable runtime data files (`perm.yaml`, `lang_settings.yaml`, `schedules.yaml`) and the log file (`log.file`) are stored in `./data/` by default (which can be changed with `--data-dir` / `W9DCBOT_DATA_DIR`). Writes always target the data directory; on read, if a file does not exist in the data directory, it falls back to the main program directory (for compatibility with old data locations). For multi-instance deployments, you should assign each instance its own separate data directory to avoid data interfering with each other. See [Data directory](/en/guide/getting-started) for details.

## Logging `log`

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `level` | enum | `INFO` | Console log level: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `file` | `str \| null` | `logs/{time:YYYY-MM-DD}.log` | Log file path (Loguru format, `null` disables it; resolved relative to the [data directory](#data-directory)) |
| `file_level` | enum \| `null` | `INFO` | File log level (`null` follows `level`) |
| `rotation` | `str \| int` | `1 days` | Loguru rotation period |
| `retention` | `str \| int` | `3 days` | Loguru retention time |

## Module switches

Every command module has the following common switches:

| Field | Default | Description |
| --- | --- | --- |
| `enabled` | `false` | Whether to enable the module (all disabled by default) |
| `slash` | `true` | Whether to register slash commands |
| `prefix` | `true` | Whether to register prefix commands |

Module-specific configuration:

- [Tools / Management `tools`](/en/modules/tools) — includes rate-limit configuration
- [Emoji `emoji`](/en/modules/emoji)
- [Channel Lock `lock`](/en/modules/lock)
- [Voice Channel `voicechannel`](/en/modules/voice)
- [Auto Management `rmmsg` / `rmtodo`](/en/modules/manage)
- [Anti-Spam `antispam`](/en/modules/antispam)
- [Chat Enhance `chatenhance`](/en/modules/chatenhance)
- [Audit Log `audit`](/en/modules/audit)

## Permission lists

```yaml
admins:
  users: []              # List of config admin user IDs / usernames (have permission for all commands)

mods:
  users: []              # Global mod list
  guilds: {}             # Per-server mod list { guild_id: [user...] }
```

- List entries can be a **user ID** (a number) or a **username** (a string); either will match.
- The keys of `mods.guilds` are server IDs (either a number or a string).

See [Permission system](/en/guide/permissions) for details.

## Full example

The following is the full content of `config.example.yaml`:

```yaml
token: "YOUR_BOT_TOKEN"
command_prefix: "//"

# Proxy address (optional)
# proxy: "http://localhost:11451"

# Logging config
log:
  level: "INFO"
  file: "logs/{time:YYYY-MM-DD}.log"
  file_level: "INFO"
  rotation: "1 days"
  retention: "3 days"
  discord_level: "INFO"       # discord.py library's own log level (independent of level)

# Audit log (no commands, service module)
# Only logs [ADMIN]/[MOD] commands, server-scope changes, anti-spam auto actions and errors
audit:
  enabled: false
  global_channel: null        # Global log channel (null to disable)
  guilds: {}

# Emoji module
emoji:
  enabled: false
  slash: true
  prefix: true
  base_url: "https://ghimg.siiway.top/emoji"
  max_results: 25

# Tools / admin commands module
tools:
  enabled: false
  slash: true
  prefix: true
  ratelimit:
    enabled: true
    window: 60
    mod_multiplier: 3
    random: 10
    uuid: 10
    "2file": 10               # YAML key name for to-file (legacy-compatible)

# Channel lock module
lock:
  enabled: false
  slash: true
  prefix: true

# Auto-delete todo bot messages (no commands, event-based)
rmtodo:
  enabled: false
  todo_channels: []
  author_id: 782105629572464652
  remove_delay: 3

# Auto-delete messages (no commands, event-based)
rmmsg:
  enabled: false
  nicks: []

# Voice channel control module
voicechannel:
  enabled: false
  slash: true
  prefix: true
  allowed_users: []
  allowed_guilds: {}
  reconnect: true
  reconnect_max_delay: 300

# Anti-spam module (no commands, event-based)
antispam:
  enabled: false
  spam_catcher: {}

# Chat enhance module (server scope, features disabled by default)
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

# Admin and permission config
admins:
  users: []

mods:
  users: []
  guilds: {}
```
