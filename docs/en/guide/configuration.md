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
  guilds: {}             # Per-server mod config
  # Example:
  # guilds:
  #   123456789012345678:
  #     roles: ["Moderator", 987654321098765432]  # Role IDs / names
  #     users: ["wyf9", 12345]                    # User IDs / usernames
  # Legacy format is still supported: guilds: { 123456789012345678: ["wyf9", 12345] }
```

- List entries can be a **user ID** (a number) or a **username** (a string); either will match.
- The keys of `mods.guilds` are server IDs (either a number or a string).
- `mods.guilds.<server>.roles` accepts **role IDs / names**; members with any configured role are mods of that server.
- The legacy format (a plain user list, e.g. `guilds: { 123: ["wyf9"] }`) is still supported and is equivalent to configuring only `users`.

See [Permission system](/en/guide/permissions) for details.

## Reference configuration

<<< @/../config.example.yaml
