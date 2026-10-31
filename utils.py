import enum
import functools
import os
import re
import time
import typing as t
from collections import defaultdict, deque
from pathlib import Path

import aiohttp
import discord
from discord.ext import commands
from loguru import logger as l

if t.TYPE_CHECKING:
    from config import ConfigModel


def perf_counter():
    """
    获取一个性能计数器, 执行返回函数来结束计时, 并返回保留两位小数的毫秒值
    """
    start = time.perf_counter()
    return lambda: round((time.perf_counter() - start) * 1000, 2)


def get_path(path: str, create_dirs: bool = True, is_dir: bool = False) -> str:
    """
    相对路径 (基于主程序目录) -> 绝对路径

    :param path: 相对路径
    :param create_dirs: 是否自动创建目录（如果不存在）
    :param is_dir: 目标是否为目录
    :return: 绝对路径
    """
    full_path = str(Path(__file__).parent.joinpath(path))
    if create_dirs:
        # 自动创建目录
        if is_dir:
            os.makedirs(full_path, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
    return full_path


# 数据目录: 用于存放运行时可变数据文件 (perm.yaml / lang_settings.yaml / schedules.yaml 等)
# 通过 set_data_dir 配置 (--data-dir / W9DCBOT_DATA_DIR), 默认为当前工作目录下的 ./data/
_DATA_DIR: str = str(Path("data"))


def set_data_dir(path: str | None):
    """
    设置数据目录

    :param path: 数据目录路径 (None 则使用默认 ./data/); 相对路径按当前工作目录解析
    """
    global _DATA_DIR
    _DATA_DIR = str(Path(path).expanduser()) if path else str(Path("data"))
    l.debug(f"[data] Data directory set to: {_DATA_DIR}")


def get_data_dir() -> str:
    """获取当前配置的数据目录 (绝对/相对均可, 由 set_data_dir 决定)"""
    return _DATA_DIR


def get_data_path(path: str, create_dirs: bool = True, for_read: bool = False) -> str:
    """
    数据文件相对路径 -> 绝对路径 (基于数据目录)

    写入 (for_read=False): 始终指向数据目录, 保证多实例之间数据隔离。
    读取 (for_read=True): 若数据目录中不存在该文件, 则回退到主程序目录下的同名文件
                          (兼容旧版本的数据位置); 都不存在时仍返回数据目录路径。

    :param path: 相对路径 (如 perm.yaml)
    :param create_dirs: 写入模式下是否自动创建数据目录
    :param for_read: 是否为读取模式 (启用回退)
    :return: 绝对路径
    """
    data_file = Path(_DATA_DIR).joinpath(path)

    if for_read:
        if data_file.exists():
            return str(data_file)
        # 回退到主程序目录 (旧数据位置)
        legacy = Path(get_path(path, create_dirs=False))
        if legacy.exists():
            l.debug(f"[data] Falling back to legacy path for '{path}': {legacy}")
            return str(legacy)
        return str(data_file)

    # 写入模式: 始终使用数据目录
    if create_dirs:
        parent = data_file.parent
        os.makedirs(parent, exist_ok=True)
    return str(data_file)


def relative_path(path: str) -> str:
    """
    绝对路径 -> 相对路径
    """
    return os.path.relpath(path)


async def get_json(url: str, **params) -> tuple[bool, dict, str]:
    """
    使用 aiohttp 异步请求 json 资源

    :param url: 请求的 url
    :param params: 其他传递给 `session.get` 的参数
    :return bool: success
    :return dict: response
    :return str: error
    """
    try:
        async with (
            aiohttp.ClientSession() as sess,
            sess.get(url, **params) as resp,
        ):
            if resp.status == 200:
                return True, await resp.json(), ""
            else:
                raise aiohttp.ClientResponseError(
                    request_info=resp.request_info,
                    history=resp.history,
                    status=resp.status,
                    message=f"Status code isn't 200: {resp.status}",
                )
    except Exception as e:
        l.warning(f"[get_json] Request {url} error: {e}")
        return False, {}, str(e)


async def send_msg(
    source: discord.Interaction | commands.Context,
    content: str | None = None,
    *,
    ephemeral: bool = False,
    delete_after: float | None = None,
    **kwargs,
) -> discord.Message | None:
    """
    统一发送消息: 支持 Interaction (followup) 和 Context (reply to original message)

    prefix 模式下自动回复原消息, 失败则 fallback 到直接发送
    """
    if isinstance(source, discord.Interaction):
        if source.response.is_done():
            return await source.followup.send(content, ephemeral=ephemeral, **kwargs)  # type: ignore
        else:
            await source.response.send_message(
                content, ephemeral=ephemeral, delete_after=delete_after, **kwargs
            )
            return None
    else:
        try:
            return await source.send(
                content=content,
                reference=source.message,
                delete_after=delete_after,
                **kwargs,
            )  # ty:ignore[no-matching-overload]
        except (discord.HTTPException, discord.NotFound):
            return await source.send(
                content=content, delete_after=delete_after, **kwargs
            )  # ty:ignore[no-matching-overload]


# ========== Permission Helpers (shared) ==========


def matches_identity(
    user: discord.User | discord.Member, values: "list[int | str]"
) -> bool:
    """检查用户是否匹配 ID / 用户名列表中的任意一项"""
    for value in values:
        if user.id == value or user.name == value:
            return True
        if isinstance(value, str) and value.isdigit() and user.id == int(value):
            return True
    return False


def matches_role(member: discord.Member, values: "list[int | str]") -> bool:
    """检查用户是否拥有 ID / 名称列表中的任意身份组"""
    for value in values:
        for role in member.roles:
            if role.id == value or role.name == value:
                return True
            if isinstance(value, str) and value.isdigit() and role.id == int(value):
                return True
    return False


def is_server_admin(user: discord.User | discord.Member) -> bool:
    """是否为服务器管理员 (拥有 administrator 权限)"""
    return isinstance(user, discord.Member) and user.guild_permissions.administrator


def is_config_admin(user: discord.User | discord.Member, config: "ConfigModel") -> bool:
    """是否在配置的 admins 名单中"""
    return matches_identity(user, config.admins.users)


def is_admin(user: discord.User | discord.Member, config: "ConfigModel") -> bool:
    """是否为管理员 (仅限 config.yaml > admins.users 名单)"""
    return is_config_admin(user, config)


# Optional dynamic permission store (perm.yaml); registered at startup so that
# a "mod grant" rule (no module/command) can make is_mod() return True.
_perm_store: t.Any = None
_bot_guild_lookup: t.Callable[[int, int | str], discord.Member | None] | None = None


def set_perm_store(store: t.Any) -> None:
    """注册全局 PermStore 引用, 供 is_mod 查询动态 mod 授权"""
    global _perm_store
    _perm_store = store


def set_bot_guild_lookup(
    lookup: t.Callable[[int, int | str], discord.Member | None] | None,
) -> None:
    global _bot_guild_lookup
    _bot_guild_lookup = lookup


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y", "t"}:
        return True
    if normalized in {"false", "0", "no", "n", "f"}:
        return False
    raise ValueError(value)


def is_mod(
    user: discord.User | discord.Member,
    config: "ConfigModel",
    guild: discord.Guild | None = None,
) -> bool:
    """是否为 mod (服务器管理员 / 配置 admin / mod 名单 / perm.yaml 动态 mod 授权)"""
    if is_admin(user, config):
        return True
    if is_server_admin(user):
        return True
    if isinstance(user, discord.Member):
        if matches_identity(user, config.mods.users):
            return True
        if guild is not None:
            guild_mods = config.mods.guilds.get(
                guild.id, config.mods.guilds.get(str(guild.id))
            )
            if guild_mods is not None:
                if matches_identity(user, guild_mods.users):
                    return True
                if matches_role(user, guild_mods.roles):
                    return True
    # 动态 mod 授权: perm.yaml 中 module/command 均为空的规则
    return bool(
        _perm_store is not None
        and _perm_store.grants_mod(user.id, guild.id if guild is not None else None)
    )


def slash_commands_enabled(config: object) -> bool:
    """全局斜杠指令是否启用"""
    return bool(getattr(config, "slash", True))


def resolve_rate_limit(
    config: "ConfigModel",
    user: discord.User | discord.Member,
    guild: discord.Guild | None,
    module: str,
    command: str | None = None,
) -> tuple[int, float] | None:
    """
    根据全局限速配置计算额度

    :return: (窗口内最大次数, 窗口秒数), None 表示不限速
    """
    rl = config.ratelimit
    if not rl.enabled or is_admin(user, config):
        return None
    base = rl.resolve(module, command)
    if base is None:
        return None
    limit = base * rl.mod_multiplier if is_mod(user, config, guild) else base
    return limit, rl.window


async def check_rate_limit(
    source,
    *,
    config: "ConfigModel",
    rate_limiter: "RateLimiter",
    module: str,
    command: str,
) -> bool:
    """
    按全局限速配置检查并记录一次调用

    :return: True 表示允许执行, False 表示已回复限速提示
    """
    user = source.user if isinstance(source, discord.Interaction) else source.author
    guild = getattr(source, "guild", None)
    params = resolve_rate_limit(config, user, guild, module, command)
    if params is None:
        return True
    limit, window = params
    allowed, retry_after = rate_limiter.hit(
        (f"{module}:{command}", user.id), limit, window
    )
    if not allowed:
        import i18n

        await send_msg(
            source,
            i18n.t(
                "common.rate_limited",
                _resolve_lang(source),
                retry=f"{retry_after:.0f}",
            ),
            ephemeral=True,
            delete_after=10,
        )
        return False
    return True


# ========== Declarative Permission Control ==========


class Permission(enum.Enum):
    """指令所需的权限等级 (声明式)"""

    EVERYONE = "everyone"
    """所有人可用"""

    MOD = "mod"
    """需要 mod (含 admin)"""

    ADMIN = "admin"
    """需要 admin (服务器管理员 / 配置 admin)"""


# 自定义权限判定: (module, user, guild) -> bool
PermissionCheck = t.Callable[
    [t.Any, "discord.User | discord.Member", "discord.Guild | None"], bool
]


def _resolve_lang(source) -> str:
    """从 source 解析语言 (延迟导入以避免与 i18n 循环依赖)"""
    import i18n

    lang_store = None
    bot = getattr(source, "client", None) or getattr(source, "bot", None)
    if bot is not None:
        lang_store = getattr(bot, "lang_store", None)
    return i18n.lang_of(source, lang_store)


# Sentinel: use the localized default deny message at runtime.
DEFAULT_DENY_MESSAGE = None


def has_permission(
    perm: "Permission | PermissionCheck",
    module: t.Any,
    user: discord.User | discord.Member,
    guild: discord.Guild | None,
) -> bool:
    """
    统一权限判定

    :param perm: Permission 等级 或 自定义判定函数
    :param module: 指令所属模块实例 (需含 `.c` 配置)
    :param user: 触发用户
    :param guild: 触发所在服务器
    """
    if callable(perm):
        return perm(module, user, guild)
    config = module.c
    if perm is Permission.EVERYONE:
        return True
    if perm is Permission.MOD:
        return is_mod(user, config, guild)
    if perm is Permission.ADMIN:
        return is_admin(user, config)
    return False


def requires(
    perm: "Permission | PermissionCheck",
    *,
    deny: "str | t.Callable[[discord.User | discord.Member], str] | None" = DEFAULT_DENY_MESSAGE,
    perm_module: str | None = None,
    perm_command: str | None = None,
):
    """
    声明式权限控制装饰器, 用于模块的 `_handle_*` 方法

    - 自动从 `source` (Interaction / Context) 解析用户与服务器
    - 统一走 `has_permission` 判定, 不通过则回复拒绝消息并中止
    - 若 config 权限未通过, 回退到 perm.yaml 动态权限检查
    - 内置全局限速: 每用户每指令 10reqs/10s

    用法::

        @u.requires(u.Permission.MOD)
        async def _handle_xxx(self, source, ...):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, source, *args, **kwargs):
            user = (
                source.user
                if isinstance(source, discord.Interaction)
                else source.author
            )
            guild = getattr(source, "guild", None)

            # Global rate limit: 10 requests per 10 seconds per command per user
            bot = getattr(self, "bot", None)
            if bot:
                rl = getattr(bot, "rate_limiter", None)
                if rl:
                    cmd_key = func.__name__.removeprefix("_handle_")
                    allowed, retry = rl.hit((f"global:{cmd_key}", user.id), 10, 10)
                    if not allowed:
                        import i18n

                        await send_msg(
                            source,
                            i18n.t(
                                "common.rate_limited",
                                _resolve_lang(source),
                                retry=f"{retry:.0f}",
                            ),
                            ephemeral=True,
                            delete_after=10,
                        )
                        return None

            if has_permission(perm, self, user, guild):
                return await func(self, source, *args, **kwargs)

            # Fallback: check perm.yaml dynamic permissions
            perm_store = getattr(bot, "perm_store", None) if bot else None
            if perm_store:
                mod_name = perm_module
                cmd_name = perm_command
                if mod_name is None and cmd_name is None:
                    cmd_name = func.__name__.removeprefix("_handle_")
                if perm_store.check(
                    str(user.id),
                    guild.id if guild else None,
                    module=mod_name,
                    command=cmd_name,
                ):
                    return await func(self, source, *args, **kwargs)

            if deny is None:
                import i18n

                deny_msg = i18n.t("common.no_permission", _resolve_lang(source))
            elif isinstance(deny, str):
                deny_msg = deny
            else:
                deny_msg = deny(user)
            await send_msg(source, deny_msg, ephemeral=True, delete_after=10)
            return None

        return wrapper

    return decorator


# ========== Rate Limiter ==========


class RateLimiter:
    """
    基于滑动窗口的简单限速器

    以 (指令, 用户) 为 key 记录调用时间戳, 判断是否超出窗口内的次数上限
    """

    def __init__(self):
        self._hits: dict[t.Hashable, deque[float]] = defaultdict(deque)

    def hit(self, key: t.Hashable, limit: int, window: float) -> tuple[bool, float]:
        """
        记录一次调用并判断是否允许

        :param key: 限速 key (通常为 (command, user_id))
        :param limit: 窗口内允许的最大次数
        :param window: 窗口时长 (秒)
        :return: (是否允许, 若被限则需等待的秒数)
        """
        now = time.monotonic()
        dq = self._hits[key]
        # 清理过期记录
        while dq and dq[0] <= now - window:
            dq.popleft()
        if len(dq) >= limit:
            retry_after = window - (now - dq[0])
            return False, max(retry_after, 0.0)
        dq.append(now)
        return True, 0.0


_cog_names_cache: list[str] = []
_cog_names_at: float = 0.0


def list_cog_names(cache_seconds: float = 1.0) -> list[str]:
    """
    列出 cogs/ 目录下的模块名, 结果缓存 `cache_seconds` 秒

    用于 /reload 与 /perm 的模块参数自动补全
    """
    global _cog_names_cache, _cog_names_at
    now = time.monotonic()
    if _cog_names_cache and now - _cog_names_at < cache_seconds:
        return _cog_names_cache
    cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
    try:
        names = sorted(
            f[:-3]
            for f in os.listdir(cogs_dir)
            if f.endswith(".py") and not f.startswith("_")
        )
    except OSError:
        names = []
    _cog_names_cache = names
    _cog_names_at = now
    return names


def parse_flags(content: str) -> dict[str, str]:
    """
    从消息内容中解析 --key=value 格式的标志
    """
    flags: dict[str, str] = {}
    for match in re.finditer(r'--([\w-]+)=(?:"([^"]*)"|(\S+))', content):
        key = match.group(1)
        value = match.group(2) if match.group(2) is not None else match.group(3)
        flags[key] = value
    return flags
