# 快速开始

## 前置要求

- **Python 3.13**（`pyproject.toml` 要求 `>=3.10`，`.python-version` 指定 `3.13`）
- **[uv](https://docs.astral.sh/uv/)** 包管理器
- 一个 Discord 机器人 Token（在 [Discord Developer Portal](https://discord.com/developers/applications) 创建应用并获取）

## 部署步骤

```bash
# 1. 克隆仓库
git clone https://github.com/wyf9/wyf9s-discord-bot.git --depth 1
cd wyf9s-discord-bot

# 2. 复制示例配置
cp config.example.yaml config.yaml

# 3. 编辑配置 (至少填入 token)
nano config.yaml

# 4. 运行 (uv 会自动创建虚拟环境并安装依赖)
uv run main.py
```

`update.sh` 可用于更新：

```bash
sh update.sh
```

## 启动参数

`main.py` 支持以下命令行参数，用于指定配置 / token 的来源。每个参数也可通过对应的**环境变量**指定，命令行参数优先级高于环境变量：

| 参数 | 环境变量 | 说明 |
| --- | --- | --- |
| `--config`, `-c <PATH>` | `W9DCBOT_CONFIG` | 指定配置文件路径（默认：优先查找数据目录，未找到再回退到主程序目录下的 `config.yaml`） |
| `--token-file <PATH>` | `W9DCBOT_TOKEN_FILE` | 指定 token 文件路径（默认：优先查找数据目录，未找到再回退到主程序目录下的 `tk.yaml`，一个含 `token: xxx` 的 YAML） |
| `--token <TOKEN>` | `W9DCBOT_TOKEN` | 直接指定 Bot Token |
| `--data-dir <PATH>` | `W9DCBOT_DATA_DIR` | 运行时数据文件目录（默认：`./data/`），见[数据目录](#数据目录) |

```bash
# 使用自定义配置文件
uv run main.py --config /path/to/my-config.yaml

# 从单独的 token 文件读取 token
uv run main.py --token-file /path/to/tk.yaml

# 直接通过参数传入 token
uv run main.py --token "YOUR_BOT_TOKEN"

# 指定独立的数据目录 (多实例隔离)
uv run main.py --data-dir /path/to/instance-a/data

# 通过环境变量传入 (适合容器 / CI)
export W9DCBOT_TOKEN="YOUR_BOT_TOKEN"
uv run main.py
```

::: tip Token 优先级
`--token` 参数 / `W9DCBOT_TOKEN` 环境变量 > token 文件（`--token-file` / `tk.yaml`）> 配置文件（`config.yaml`）中的 `token` 字段。

其中对于同一项配置，命令行参数优先级高于环境变量。这样便于将敏感的 token 从主配置文件中分离出来（例如 `tk.yaml` 已被 `.gitignore` 忽略），或在容器 / CI 环境中通过参数 / 环境变量注入。

自定义的 `--config` / `--token-file` 路径按当前工作目录解析；若指定的文件不存在，程序会报错退出。
:::

### （可选）Systemd — 后台运行、进程守护、自动重启与开机自启动

若您希望该 Bot 在后台运行，具备进程守护、崩溃自动重启以及开机自启动能力，推荐使用 `systemd` 来管理。

1. **创建服务文件**：

```bash
sudo nano /etc/systemd/system/wyf9s-bot.service
```

2. **粘贴以下内容（请根据实际情况修改）**：

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

::: tip ExecReload
通过 `systemctl reload wyf9s-bot`（或 `systemctl reload-or-restart`）可向 Bot 发送 `SIGHUP` 信号，触发配置文件与所有模块的热重载，无需中断服务。重载失败不影响当前运行的进程。
:::

并 `ctrl + x` 输入 `y` 并使用 `enter` 键。

3. **并依次执行**：

```bash
sudo systemctl daemon-reload
sudo systemctl start wyf9s-bot
sudo systemctl enable wyf9s-bot
```

<details>
<summary>Systemd 常用命令</summary>
<br>

|**操作**|**命令**|
|:---|:---:|
|查看状态|`sudo systemctl status wyf9s-bot`|
|启动服务|`sudo systemctl start wyf9s-bot`|
|停止服务|`sudo systemctl stop wyf9s-bot`|
|重启服务|`sudo systemctl restart wyf9s-bot`|
|重载配置|`sudo systemctl reload wyf9s-bot`|
|查看日志|`sudo journalctl -u wyf9s-bot -f`|
|查看最近 50 行日志|`sudo journalctl -u wyf9s-bot -n 50 --no-pager`|
|禁用开机自启|`sudo systemctl disable wyf9s-bot`|

</details>

#### 如果需要运行多个 Bot 实例：

1. **首先创建第二个服务文件**：

```bash
sudo nano /etc/systemd/system/wyf9s-bot-2.service
```

2. **粘贴以下内容**：

* 请注意修改 `YOUR_TOKEN` 至您的Discord Bot Token。

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

3. **并依次执行**：

```bash
sudo systemctl daemon-reload
sudo systemctl start wyf9s-bot-2
sudo systemctl enable wyf9s-bot-2
```

## Docker 部署（可选）

也可通过预构建的 Docker 镜像部署，无需在宿主机安装 Python / uv。

### 使用 Docker Compose（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/wyf9/wyf9s-discord-bot.git --depth 1
cd wyf9s-discord-bot

# 2. 复制示例配置与 Compose 文件
cp config.example.yaml config.yaml
cp docker-compose.example.yaml docker-compose.yaml

# 3. 编辑配置 (至少填入 token)
nano config.yaml

# 4. 启动 / 查看日志
docker compose up -d
docker compose logs -f
```

更新镜像：

```bash
docker compose pull && docker compose up -d
```

### 使用 Docker CLI

```bash
docker run -d --name wyf9s-discord-bot --restart unless-stopped \
  -v "$(pwd)/config.yaml:/app/data/config.yaml:ro" \
  -v "$(pwd)/tk.yaml:/app/data/tk.yaml:ro" \
  -v "$(pwd)/data:/app/data" \
  ghcr.io/wyf9/wyf9s-discord-bot:latest
```

配置文件 / token 文件与运行时数据（`perm.yaml`、`lang_settings.yaml`、`schedules.yaml`、日志）均持久化在宿主机目录，路径解析规则同[数据目录](#数据目录)。也可用 `W9DCBOT_TOKEN` 环境变量直接注入 token（优先级最高）。

# =============================================================================
# Bot Presence (全局)
# =============================================================================
# presence 配置用于设置自定义全局 Bot 状态。
# activity 中可使用 {servers} 与 {members} 占位符，在运行时会替换为当前服务器数量和成员总数。
# status 为 Discord 的在线状态，可选: online, idle, dnd, invisible。
presence:
  enabled: true                # 是否启用自定义 Presence
  activity: "Serving {servers} Servers with {members} Members"
  status: online               # online | idle | dnd | invisible

### 数据目录

运行时可变的数据文件（`perm.yaml`、`lang_settings.yaml`、`schedules.yaml`）以及**日志文件**（`log.file`）默认存放在 `--data-dir` 指定的目录（默认 `./data/`，按当前工作目录解析）。

- **写入**：始终写入数据目录，因此为不同实例指定不同的 `--data-dir`（或从不同工作目录启动）即可实现数据隔离，避免多实例之间数据互相覆盖。
- **读取回退**：若数据目录中不存在某个数据文件，则回退读取主程序目录下的同名文件（兼容旧版本的数据位置）；之后的写入仍会保存到数据目录，从而自动完成迁移。
- **日志**：配置中的 `log.file` 路径相对于数据目录解析（如默认 `logs/{time}.log` 会写入 `<data-dir>/logs/`），因此各实例的日志也会随数据目录隔离。

::: tip 多实例部署
若在同一份代码目录下运行多个机器人实例，请为每个实例指定独立的 `--data-dir`（或 `W9DCBOT_DATA_DIR`），否则它们会共享 `perm.yaml` 等数据文件而互相干扰。
:::

## 机器人权限与 Intents

### Gateway Intents

机器人在代码中启用了 **Message Content Intent**（`intents.message_content = True`）。你需要在 Discord Developer Portal 的应用设置中打开 **Message Content Intent**（`Bot` → `Privileged Gateway Intents`），否则前缀命令与部分事件功能无法正常工作。

### 邀请机器人所需权限

根据你启用的模块，机器人在服务器中至少需要以下权限：

| 权限 | 用于 |
| --- | --- |
| 查看频道 / 发送消息 / 嵌入链接 / 附加文件 | 基础功能、发送嵌入 / 文件 |
| 管理消息（Manage Messages） | `delete` / `clear-message` / 自动删除 |
| 管理频道（Manage Channels） | `move-channel` |
| 管理身份组 / 管理频道 | `/lock now` `/lock unlock` `/lock plan`（修改频道权限覆盖） |
| 连接 / 使用语音（Connect / Speak） | `vc join` / `vc leave` |
| 踢出成员（Kick Members） | 反垃圾 `kick` |
| 封禁成员（Ban Members） | 反垃圾 `ban` |
| 超时成员（Moderate Members / Timeout） | 反垃圾 `mute` |

::: warning 身份组层级
执行踢出 / 封禁 / 超时 / 修改权限等操作时，**机器人身份组必须高于被操作对象的最高身份组**，否则即使拥有权限也会被 Discord 拒绝（反垃圾模块会在审计日志中明确提示这一点）。
:::

## 最小配置示例

```yaml
token: "YOUR_BOT_TOKEN"
command_prefix: "//"

# 只启用工具模块作为示例
tools:
  enabled: true
  slash: true
  prefix: true

# 你自己的用户 ID / 用户名，赋予配置管理员权限
admins:
  users:
    - 123456789012345678
```

更多配置项见[配置说明](/guide/configuration)。

## 代码质量（开发）

修改代码后请运行：

```bash
uvx ruff check --fix && uvx ruff format && uvx ty check --fix
```

- `ruff check --fix` — lint 并自动修复
- `ruff format` — 格式化
- `ty check --fix` — 类型检查并自动修复
