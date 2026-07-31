# Getting Started

## Prerequisites

- **Python 3.13** (`pyproject.toml` requires `>=3.10`, `.python-version` specifies `3.13`)
- The **[uv](https://docs.astral.sh/uv/)** package manager
- A Discord bot token (create an application and obtain it on the [Discord Developer Portal](https://discord.com/developers/applications))

## Deployment Steps

```bash
# 1. Clone the repository
git clone https://github.com/wyf9/wyf9s-discord-bot.git --depth 1
cd wyf9s-discord-bot

# 2. Copy the example config
cp config.example.yaml config.yaml

# 3. Edit the config (at least fill in the token)
nano config.yaml

# 4. Run (uv automatically creates a virtualenv and installs dependencies)
uv run main.py
```

`update.sh` can be used to update:

```bash
sh update.sh
```

## Startup Arguments

`main.py` supports the following command-line arguments to specify the source of the config / token. Each argument can also be specified via a corresponding **environment variable**; command-line arguments take priority over environment variables:

| Argument | Environment variable | Description |
| --- | --- | --- |
| `--config`, `-c <PATH>` | `W9DCBOT_CONFIG` | Specify the config file path (default: look up the data directory first, then fall back to `config.yaml` in the program directory) |
| `--token-file <PATH>` | `W9DCBOT_TOKEN_FILE` | Specify the token file path (default: look up the data directory first, then fall back to `tk.yaml` in the program directory, a YAML containing `token: xxx`) |
| `--token <TOKEN>` | `W9DCBOT_TOKEN` | Specify the bot token directly |
| `--data-dir <PATH>` | `W9DCBOT_DATA_DIR` | Runtime data file directory (default: `./data/`), see [Data Directory](#data-directory) |

```bash
# Use a custom config file
uv run main.py --config /path/to/my-config.yaml

# Read the token from a separate token file
uv run main.py --token-file /path/to/tk.yaml

# Pass the token directly via argument
uv run main.py --token "YOUR_BOT_TOKEN"

# Specify a separate data directory (multi-instance isolation)
uv run main.py --data-dir /path/to/instance-a/data

# Pass via environment variables (suitable for containers / CI)
export W9DCBOT_TOKEN="YOUR_BOT_TOKEN"
uv run main.py
```

::: tip Token Priority
The `--token` argument / `W9DCBOT_TOKEN` environment variable > token file (`--token-file` / `tk.yaml`) > the `token` field in the config file (`config.yaml`).

For the same setting, command-line arguments take priority over environment variables. This makes it easy to separate the sensitive token from the main config file (for example, `tk.yaml` is already ignored by `.gitignore`), or to inject it via arguments / environment variables in a container / CI environment.

Custom `--config` / `--token-file` paths are resolved relative to the current working directory; if the specified file does not exist, the program will error out and exit.
:::

### Data Directory

Runtime-mutable data files (`perm.yaml`, `lang_settings.yaml`, `schedules.yaml`) as well as **log files** (`log.file`) are by default stored in the directory specified by `--data-dir` (default `./data/`, resolved relative to the current working directory).

- **Writes**: Always written to the data directory, so specifying a different `--data-dir` for each instance (or starting from a different working directory) achieves data isolation and prevents instances from overwriting each other's data.
- **Read fallback**: If a data file does not exist in the data directory, it falls back to reading the file of the same name in the main program directory (compatible with the data location of older versions); subsequent writes are still saved to the data directory, thereby automatically completing the migration.
- **Logging**: The `log.file` path in the config is resolved relative to the data directory (for example, the default `logs/{time}.log` is written to `<data-dir>/logs/`), so each instance's logs are also isolated along with the data directory.

::: tip Multi-instance Deployment
If you run multiple bot instances from the same code directory, specify a separate `--data-dir` (or `W9DCBOT_DATA_DIR`) for each instance; otherwise they will share data files such as `perm.yaml` and interfere with each other.
:::

### (Optional) Systemd — Background Running, Process Guardian, Auto Restart, and Boot Startup

If you want the bot to run in the background with process guarding, automatic restart on crash, and auto-start on boot, it is recommended to use `systemd` to manage it.

1. **Create the service file**:

```bash
sudo nano /etc/systemd/system/wyf9s-bot.service
```

2. **Paste the following (modify according to your environment)**:

```
[Unit]
Description=wyf9s Discord Bot Service
After=network.target

[Service]
Type=simple
ExecStart=/root/.local/bin/uv run /root/wyf9s-discord-bot/main.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target  
```

Then press `ctrl + x`, enter `y` and press `enter`.

3. **Run sequentially**:

```bash
sudo systemctl daemon-reload
sudo systemctl start wyf9s-bot
sudo systemctl enable wyf9s-bot
```

::: tip ExecReload
Running `systemctl reload wyf9s-bot` (or `systemctl reload-or-restart`) sends a `SIGHUP` signal to the bot, triggering a hot reload of the config file and all modules without interrupting the service. A failed reload does not affect the currently running process.
:::

<details>
<summary>Systemd Common Commands</summary>
<br>

|**Action**|**Command**|
|:---|:---:|
|Check status|`sudo systemctl status wyf9s-bot`|
|Start service|`sudo systemctl start wyf9s-bot`|
|Stop service|`sudo systemctl stop wyf9s-bot`|
|Restart service|`sudo systemctl restart wyf9s-bot`|
|Reload config|`sudo systemctl reload wyf9s-bot`|
|View logs|`sudo journalctl -u wyf9s-bot -f`|
|View recent 50 lines of logs|`sudo journalctl -u wyf9s-bot -n 50 --no-pager`|
|Disable auto-start|`sudo systemctl disable wyf9s-bot`|

</details>

#### If you need to run multiple bot instances:

1. **First create the second service file**:

```bash
sudo nano /etc/systemd/system/wyf9s-bot-2.service
```

2. **Paste the following**:

* Note: change `YOUR_TOKEN` to your Discord Bot Token.

```
[Unit]
Description=wyf9s Discord Bot Service 2
After=network.target

[Service]
Type=simple
ExecStart=/root/.local/bin/uv run /root/wyf9s-discord-bot/main.py --token "YOUR_TOKEN"
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. **Run sequentially**:

```bash
sudo systemctl daemon-reload
sudo systemctl start wyf9s-bot-2
sudo systemctl enable wyf9s-bot-2
```

## Docker Deployment (Optional)

You can also deploy using a pre-built Docker image, without installing Python / uv on the host.

### Using Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/wyf9/wyf9s-discord-bot.git --depth 1
cd wyf9s-discord-bot

# 2. Copy the example config and Compose file
cp config.example.yaml config.yaml
cp docker-compose.example.yaml docker-compose.yaml

# 3. Edit the config (at least fill in the token)
nano config.yaml

# 4. Start / view logs
docker compose up -d
docker compose logs -f
```

To update the image:

```bash
docker compose pull && docker compose up -d
```

### Using Docker CLI

```bash
docker run -d --name wyf9s-discord-bot --restart unless-stopped \
  -v "$(pwd)/config.yaml:/app/data/config.yaml:ro" \
  -v "$(pwd)/tk.yaml:/app/data/tk.yaml:ro" \
  -v "$(pwd)/data:/app/data" \
  ghcr.io/wyf9/wyf9s-discord-bot:latest
```

The config file / token file and runtime data (`perm.yaml`, `lang_settings.yaml`, `schedules.yaml`, logs) are all persisted in host directories, following the same resolution rules as the [Data Directory](#data-directory). You can also inject the token directly via the `W9DCBOT_TOKEN` environment variable (highest priority).

# =============================================================================
# Bot Presence (global)
# =============================================================================
# presence configuration allows setting a custom global Bot status.
# In `activity` you may use {servers} and {members} placeholders which are replaced
# at runtime with the current server and member counts.
# `status` is one of: online, idle, dnd, invisible.
presence:
  enabled: true                # Enable custom presence
  activity: "Serving {servers} Servers with {members} Members"
  status: online               # online | idle | dnd | invisible

## Bot Permissions and Intents

### Gateway Intents

The bot enables the **Message Content Intent** in code (`intents.message_content = True`). You need to enable **Message Content Intent** in the application settings on the Discord Developer Portal (`Bot` → `Privileged Gateway Intents`), otherwise prefix commands and some event features will not work properly.

### Permissions Required to Invite the Bot

Depending on the modules you enable, the bot needs at least the following permissions in a server:

| Permission | Used for |
| --- | --- |
| View Channels / Send Messages / Embed Links / Attach Files | Basic functionality, sending embeds / files |
| Manage Messages | `delete` / `clear-message` / auto-delete |
| Manage Channels | `move-channel` |
| Manage Roles / Manage Channels | `/lock now` `/lock unlock` `/lock plan` (modifying channel permission overwrites) |
| Connect / Speak | `vc join` / `vc leave` |
| Kick Members | Anti-spam `kick` |
| Ban Members | Anti-spam `ban` |
| Moderate Members / Timeout | Anti-spam `mute` |

::: warning Role Hierarchy
When performing operations such as kicking / banning / timing out / modifying permissions, the **bot's role must be higher than the target's highest role**, otherwise Discord will reject it even if the bot has the permission (the anti-spam module explicitly notes this in the audit log).
:::

## Minimal Config Example

```yaml
token: "YOUR_BOT_TOKEN"
command_prefix: "//"

# Enable only the tools module as an example
tools:
  enabled: true
  slash: true
  prefix: true

# Your own user ID / username, granted config admin permission
admins:
  users:
    - 123456789012345678
```

For more config options, see [Configuration](/en/guide/configuration).

## Code Quality (Development)

After modifying code, please run:

```bash
uvx ruff check --fix && uvx ruff format && uvx ty check --fix
```

- `ruff check --fix` — lint and auto-fix
- `ruff format` — format
- `ty check --fix` — type check and auto-fix
