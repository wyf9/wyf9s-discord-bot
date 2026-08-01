# region import

import asyncio
import logging
import signal
from sys import stderr

# Initialize loguru BEFORE importing any modules that use logging
from loguru import logger as l

# Initialize loguru handler immediately
l.remove()  # remove default handler


def log_format(record):
    """Custom log format for Discord bot"""
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>\n"
        "<red>{exception}</red>"
    )


# Create a temporary stderr handler for config loading
l.add(
    stderr,
    level="DEBUG",
    format=log_format,
    backtrace=True,
    diagnose=True,
)


# Intercept standard logging to loguru - MUST be done before importing config
class InterceptHandler(logging.Handler):
    """Intercept standard logging and forward to loguru"""

    def emit(self, record):
        # get loguru logger at correct depth
        logger_opt = l.opt(depth=6, exception=record.exc_info)
        logger_opt.log(record.levelname, record.getMessage())


# Set InterceptHandler for all loggers immediately
logging.root.handlers = [InterceptHandler()]
logging.root.setLevel("DEBUG")

# Now import modules that use logging
import discord
from discord.ext import commands

import utils as u
from config import Config
from i18n import I18nTranslator
from lang_store import LangStore
from modules.audit import AuditLogger
from perm import PermStore

# endregion import

# region init


def parse_args():
    """
    解析命令行启动参数

    每个参数也可通过对应的环境变量指定; 命令行参数优先级高于环境变量:
    - --config      -> W9DCBOT_CONFIG
    - --token-file  -> W9DCBOT_TOKEN_FILE
    - --token       -> W9DCBOT_TOKEN
    - --data-dir    -> W9DCBOT_DATA_DIR
    """
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="wyf9's Discord Bot",
    )
    parser.add_argument(
        "--config",
        "-c",
        dest="config",
        default=os.environ.get("W9DCBOT_CONFIG"),
        metavar="PATH",
        help=(
            "Path to the config file (default: config.yaml in the program directory). "
            "Env: W9DCBOT_CONFIG"
        ),
    )
    parser.add_argument(
        "--token-file",
        dest="token_file",
        default=os.environ.get("W9DCBOT_TOKEN_FILE"),
        metavar="PATH",
        help=(
            "Path to the token file (default: tk.yaml in the program directory). "
            "Env: W9DCBOT_TOKEN_FILE"
        ),
    )
    parser.add_argument(
        "--token",
        dest="token",
        default=os.environ.get("W9DCBOT_TOKEN"),
        metavar="TOKEN",
        help=(
            "Bot Token specified directly (highest priority, overrides config file "
            "and token file). Env: W9DCBOT_TOKEN"
        ),
    )
    parser.add_argument(
        "--data-dir",
        dest="data_dir",
        default=os.environ.get("W9DCBOT_DATA_DIR"),
        metavar="PATH",
        help=(
            "Directory for runtime data files (perm.yaml, lang_settings.yaml, "
            "schedules.yaml) and logs. Reads fall back to the program directory if "
            "not found here. Default: ./data/. Env: W9DCBOT_DATA_DIR"
        ),
    )
    # 忽略未知参数, 避免与其他工具 (如 debugger) 传入的参数冲突
    args, _ = parser.parse_known_args()
    return args


async def _reload_sighup():
    """Reload config and all cogs upon SIGHUP."""
    l.info("SIGHUP received, reloading config and cogs...")
    try:
        new_config = Config(
            config_path=_args.config,
            token_file=_args.token_file,
            token=_args.token,
        ).config
        client.config = new_config  # ty:ignore[unresolved-attribute]
        audit = getattr(client, "audit", None)
        if audit:
            audit.c = new_config

        succeeded = 0
        failures: list[str] = []
        for ext_name in list(client.extensions):
            try:
                await client.reload_extension(ext_name)
                succeeded += 1
            except Exception as e:
                failures.append(str(e))
                l.error(f"Failed to reload {ext_name}: {e}")

        perm_store = getattr(client, "perm_store", None)
        if perm_store:
            perm_store._load()

        l.info(
            f"Reloaded config + {succeeded} cogs from SIGHUP ({len(failures)} failed)"
        )
    except Exception as e:
        l.opt(exception=e).error("SIGHUP config reload failed")


_args = parse_args()

# 设置数据目录 (须在创建各数据 store 之前)
u.set_data_dir(_args.data_dir)

# init config
_cfg = Config(
    config_path=_args.config,
    token_file=_args.token_file,
    token=_args.token,
)
c = _cfg.config

# reconfigure loggers now that we have config
l.remove()

l.add(
    stderr,
    level=c.log.level,
    format=log_format,
    backtrace=True,
    diagnose=True,
)

if c.log.file:
    # 日志文件位置相对于数据目录 (随 --data-dir 隔离)
    log_file_path = u.get_data_path(c.log.file)
    l.add(
        log_file_path,
        level=c.log.file_level or c.log.level,
        format=log_format,
        colorize=False,
        rotation=c.log.rotation,
        retention=c.log.retention,
        enqueue=True,
    )
    l.info(f"Saving logs to {log_file_path}")


# Route ALL stdlib logging (including discord.py) through loguru via a single
# InterceptHandler on the root logger. Child loggers keep no handlers of their
# own and propagate up to root, so each record is emitted exactly once.
logging.root.handlers = [InterceptHandler()]
logging.root.setLevel(c.log.level)

# discord.py's own loggers are tuned independently so that running the app at
# DEBUG doesn't flood the output with low-level gateway/event payloads.
for _name in ("discord", "discord.http", "discord.gateway", "discord.client"):
    _dlog = logging.getLogger(_name)
    _dlog.handlers.clear()
    _dlog.propagate = True
    _dlog.setLevel(c.log.discord_level)

# endregion init

# region setup

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix=c.command_prefix, intents=intents, proxy=c.proxy)

# Store config and shared state on bot instance
client.config = c  # ty:ignore[unresolved-attribute]
client._config_instance = _cfg  # ty:ignore[unresolved-attribute]

client.lang_store = LangStore()  # ty:ignore[unresolved-attribute]

if c.audit.enabled:
    client.audit = AuditLogger(config=c, client=client, lang_store=client.lang_store)  # ty:ignore[unresolved-attribute]
else:
    client.audit = None  # ty:ignore[unresolved-attribute]

# Shared state that persists across cog reloads
client.rate_limiter = u.RateLimiter()  # ty:ignore[unresolved-attribute]
client.perm_store = PermStore()  # ty:ignore[unresolved-attribute]
u.set_perm_store(client.perm_store)  # ty:ignore[unresolved-attribute]

# endregion setup

# region modules

COG_LIST = [
    "cogs.emoji",
    "cogs.tools",
    "cogs.lock",
    "cogs.voice",
    "cogs.antispam",
    "cogs.manage",
    "cogs.admin",
    "cogs.perm",
    "cogs.announce",
    "cogs.lang",
]

# Map cog class name → config key for per-module slash/prefix toggles.
# Cogs not listed here are only controlled by the global switches.
COG_TO_CONFIG = {
    "EmojiCog": "emoji",
    "ToolsCog": "tools",
    "LockCog": "lock",
    "VoiceCog": "voicechannel",
    "PermCog": "perm",
    "AdminCog": "admin",
    "LangCog": "lang",
    "AnnounceCog": "announce",
}


async def load_cogs():
    for ext in COG_LIST:
        try:
            await client.load_extension(ext)
            l.info(f"Loaded extension: {ext}")
        except commands.ExtensionError as e:
            l.error(f"Failed to load extension {ext}: {e}")
        except Exception as e:
            l.error(f"Unexpected error loading {ext}: {e}")


def _apply_command_toggles():
    """Apply per-module and global slash/prefix toggles after cogs are loaded."""
    global_slash = getattr(c, "slash", True)
    global_prefix = getattr(c, "prefix", True)

    for cog_name, cog in client.cogs.items():
        config_key = COG_TO_CONFIG.get(cog_name)
        module_cfg = getattr(c, config_key, None) if config_key else None

        slash_enabled = global_slash
        prefix_enabled = global_prefix

        if module_cfg is not None and hasattr(module_cfg, "slash"):
            slash_enabled = global_slash and module_cfg.slash
        if module_cfg is not None and hasattr(module_cfg, "prefix"):
            prefix_enabled = global_prefix and module_cfg.prefix

        if not slash_enabled:
            for cmd in list(getattr(cog, "__cog_app_commands__", [])):
                try:
                    client.tree.remove_command(cmd.name)
                except Exception as e:
                    l.debug(
                        f"Failed to remove slash command {cmd.name} from {cog_name}: {e}"
                    )
            l.info(f"Removed slash commands for {cog_name} (disabled)")

        if not prefix_enabled:
            for cmd in list(getattr(cog, "__cog_commands__", [])):
                try:
                    client.remove_command(cmd.name)
                except Exception as e:
                    l.debug(
                        f"Failed to remove prefix command {cmd.name} from {cog_name}: {e}"
                    )
            l.info(f"Removed prefix commands for {cog_name} (disabled)")


# endregion modules

# region error-handling


@client.tree.error
async def on_tree_error(
    interaction: discord.Interaction, error: discord.app_commands.AppCommandError
):
    cmd_name = interaction.command.name if interaction.command else "?"
    user_tag = f"{interaction.user} ({interaction.user.id})"
    l.opt(exception=error).error(f"[tree] Command '{cmd_name}' from {user_tag}")

    # Notify user
    from i18n import lang_of
    from i18n import t as _t

    lang = lang_of(interaction, getattr(client, "lang_store", None))
    err_msg = _t("common.internal_error", lang, error=error)
    if not interaction.response.is_done():
        await interaction.response.send_message(err_msg, ephemeral=True)
    else:
        await interaction.followup.send(err_msg, ephemeral=True)

    # Log to audit (silently ignore if audit fails)
    audit = getattr(client, "audit", None)
    if audit:
        try:
            await audit.log(
                action=f"slash-error/{cmd_name}",
                user=interaction.user,
                guild=interaction.guild,
                channel=interaction.channel,
                detail=f"```\n{type(error).__name__}: {str(error)[:900]}\n```",
                success=False,
                auto=False,
            )
        except Exception as e:
            l.debug(f"[main] Failed to log slash error to audit: {e}")


# endregion error-handling

# region login


async def update_presence():
    """
    刷新机器人的全局状态为 "Serving X Servers with X Members".

    Discord 机器人的 presence 是全局的 (无法按服务器单独设置), 因此这里统计
    所有服务器数量与成员总数, 展示为一条固定格式的状态.
    """

    if not client.config.presence.enabled:  # ty:ignore[unresolved-attribute]
        return
    guild_count = len(client.guilds)
    member_count = sum((g.member_count or 0) for g in client.guilds)
    activity_str = client.config.presence.activity.format(  # ty:ignore[unresolved-attribute]
        servers=guild_count, members=member_count
    )
    await client.change_presence(
        activity=discord.CustomActivity(name=activity_str),
        status=getattr(discord.Status, client.config.presence.status),  # ty:ignore[unresolved-attribute]
    )


@client.event
async def on_guild_join(guild: discord.Guild):
    await update_presence()


@client.event
async def on_guild_remove(guild: discord.Guild):
    await update_presence()


@client.event
async def on_ready():
    l.info(
        f"Logged in as {client.user} ({client.user.id if client.user else 'unknown'})"
    )

    cmds = client.tree.get_commands()
    if cmds:
        cmd_names = sorted(c.name for c in cmds)
        l.info(f"Syncing {len(cmds)} slash command(s): {', '.join(cmd_names)}")
        await client.tree.sync()
        l.info("Slash commands synced.")
    else:
        l.info("No slash commands registered, skipping tree sync.")

    await update_presence()

    # Restore persisted voice sessions if any
    try:
        import json
        import os

        persist_path = u.get_data_path("voice.yaml")
        if os.path.exists(persist_path):
            with open(persist_path, "r", encoding="utf-8") as f:  # noqa: ASYNC230  # startup restore, event loop idle
                persisted = json.load(f)
            for gid_str, ch_id in persisted.items():
                guild = client.get_guild(int(gid_str))
                if not guild:
                    continue
                if guild.voice_client:
                    continue
                channel = client.get_channel(ch_id) or await client.fetch_channel(ch_id)
                if isinstance(channel, discord.VoiceChannel):
                    try:
                        await channel.connect(self_deaf=True, self_mute=True)
                        l.info(f"[voice] Restored persisted voice for guild {guild.id}")
                    except Exception as e:
                        l.warning(
                            f"[voice] Failed to restore voice for guild {guild.id}: {e}"
                        )
    except Exception as e:
        l.warning(f"[voice] Failed to load persisted voice file: {e}")

    # Initialize emoji data on startup
    if c.emoji.enabled:
        from cogs.emoji import EmojiModel

        if not getattr(client, "emoji_data", None):
            client.emoji_data = EmojiModel()  # ty:ignore[unresolved-attribute]
        emoji_cog = client.get_cog("EmojiCog")
        if emoji_cog:
            succ, err = await emoji_cog.update_emoji_list()  # ty:ignore[unresolved-attribute]
            if succ:
                l.info("Emoji list synced.")
            else:
                l.warning(f"Emoji list sync failed: {err}")


async def main():
    async with client:
        # Register SIGHUP handler for config reload (Unix only)
        _sighup = getattr(signal, "SIGHUP", None)
        if _sighup is not None:
            asyncio.get_running_loop().add_signal_handler(
                _sighup, lambda: asyncio.create_task(_reload_sighup())
            )
            l.info("Registered SIGHUP handler for config reload")

        await client.tree.set_translator(I18nTranslator())
        await load_cogs()
        _apply_command_toggles()
        await client.start(c.token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        l.info("Received shutdown signal, exiting gracefully.")
    except Exception as e:
        l.opt(exception=e).critical("Fatal error, shutting down.")
    finally:
        l.info("Bye!")

# endregion login
