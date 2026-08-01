import sys
import typing as t
from pathlib import Path

from loguru import logger as l
from pydantic import BaseModel, ConfigDict, Field, field_validator
from yaml import safe_load

import utils as u


class _LoggingConfigModel(BaseModel):
    """
    日志配置 Model
    """

    level: t.Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    """
    日志等级
    - DEBUG
    - INFO
    - WARNING
    - ERROR
    - CRITICAL
    """

    file: str | None = "logs/{time:YYYY-MM-DD}.log"
    """
    日志文件保存格式 (for Loguru)
    - 设置为 None 以禁用
    """

    file_level: t.Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | None = (
        "INFO"
    )
    """
    单独设置日志文件中的日志等级, 如设置为 None 则使用 level 设置
    - DEBUG
    - INFO
    - WARNING
    - ERROR
    - CRITICAL
    """

    discord_level: t.Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    """
    discord.py 库自身的日志等级 (独立于 level, 避免 DEBUG 下大量底层网关日志)
    - 默认 INFO; 如需排查连接问题可设为 DEBUG
    """

    rotation: str | int = "1 days"
    """
    配置 Loguru 的 rotation (轮转周期) 设置
    """

    retention: str | int = "3 days"
    """
    配置 Loguru 的 retention (轮转保留) 设置
    """

    @field_validator("level", "file_level", "discord_level", mode="before")
    def normalize_level(cls, v):
        if v is None:
            return v
        if not isinstance(v, str):
            raise TypeError(f"Invalid log level: {v}")
        upper = v.strip().upper()
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if upper not in valid:
            raise ValueError(f"Invalid log level: {v}")
        return upper


class _ToolsRateLimitConfigModel(BaseModel):
    """
    限速配置
    - admin (配置 admins) 不受限速
    - mod 的额度为普通用户的 mod_multiplier 倍
    """

    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = True
    """是否启用限速"""

    window: int = 60
    """时间窗口 (秒)"""

    mod_multiplier: int = 3
    """mod 的额度倍数 (相对普通用户)"""

    random: int = 10
    """random 指令: 窗口内普通用户最大次数"""

    uuid: int = 10
    """uuid 指令: 窗口内普通用户最大次数"""

    to_file: int = Field(default=10, alias="2file")
    """to-file 指令: 窗口内普通用户最大次数 (YAML 键: "2file")"""

    e: int = 10
    """e 指令: 窗口内普通用户最大次数"""

    emoji_info: int = 10
    """emoji info 指令: 窗口内普通用户最大次数"""

    def limit_for(self, command: str) -> int | None:
        """获取指定指令的基础限速额度, 未配置则返回 None (不限速)"""
        return {
            "random": self.random,
            "uuid": self.uuid,
            "to-file": self.to_file,
            "e": self.e,
            "emoji-info": self.emoji_info,
        }.get(command)


class _EmojiConfigModel(BaseModel):
    """
    Emoji 模块配置
    指令: /e, /emoji info, /emoji update
    """

    enabled: bool = False
    """是否启用 Emoji 模块"""

    slash: bool = True
    """是否注册斜杠指令"""

    prefix: bool = True
    """是否注册前缀指令"""

    base_url: str = "https://ghimg.siiway.top/emoji"
    """基础 url (末尾不加 `/`, 目录需包含 `emoji.json`)"""

    max_results: int = 25
    """表情搜索的最大结果数 (设置过大可能导致调用失败)"""

    ratelimit: _ToolsRateLimitConfigModel = _ToolsRateLimitConfigModel()
    """限速配置 (/e / /emoji info)"""


class _AutoRemoveTodoConfigModel(BaseModel):
    """
    自动删除 todo bot 消息配置
    `rmtodo` (无指令, 基于事件)
    """

    enabled: bool = False
    """是否启用 AutoRemoveTodo 模块"""

    todo_channels: list[int] = []
    """todo 频道列表 (频道中 To-Do List Bot 发送的带 embeds 的消息会被自动删除)"""

    author_id: int = 782105629572464652
    """todo bot 的用户 id"""

    remove_delay: int = 3
    """移除前等待秒数"""


class _AutoRemoveMessageConfigModel(BaseModel):
    """
    自动删除消息配置
    `rmmsg` (无指令, 基于事件)
    """

    enabled: bool = False
    """是否启用"""

    nicks: list[str] = []
    """
    要自动删除的昵称列表
    - 比如 `[DC] @system`
    - 支持通配符
    """


class _VoiceChannelConfigModel(BaseModel):
    """
    语音频道控制模块配置
    指令: vc join, vc leave
    """

    enabled: bool = False
    """是否启用语音频道控制模块"""

    slash: bool = True
    """是否注册斜杠指令"""

    prefix: bool = True
    """是否注册前缀指令"""

    allowed_users: list[int | str] = []
    """
    全局允许使用 voice 命令的用户 ID / 用户名列表 (白名单)
    """

    allowed_guilds: dict[int | str, list[int | str]] = {}
    """
    按服务器配置的 voice 允许列表, key 为 guild id
    """

    reconnect: bool = True
    """
    断线后是否自动重连 (包括 Discord 内部重连失败后的主动重连)
    - persist=True 时, 即使被管理员断开也会重连 (需使用 /vc leave 离开)
    - persist=False 时, 仅在非管理员断连时重连
    """

    reconnect_max_delay: int = 300
    """断线重连指数退避最大间隔 (秒)"""


class _AuditGuildConfigModel(BaseModel):
    """Per-server audit log config"""

    model_config = ConfigDict(populate_by_name=True)

    channel: int
    """Log target channel ID"""

    @field_validator("channel", mode="before")
    def normalize_channel(cls, v):
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v


class _AuditLogConfigModel(BaseModel):
    """Audit log config (no commands, service module)"""

    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = False
    """Whether audit logging is enabled"""

    global_channel: int | None = None
    """
    Global audit log channel ID
    - All audited operations will be sent here
    - Set to None to disable global logging
    """

    guilds: dict[int | str, _AuditGuildConfigModel] = {}
    """
    Per-server log channel config
    - key is guild id (can be int or str)
    - value can be:
      - channel ID (int), or
      - { channel: channel_id }
    - 与全局日志互不影响: 若两者都配置, 则两个频道都会收到日志
    """

    @field_validator("guilds", mode="before")
    def normalize_guilds(cls, v):
        if not isinstance(v, dict):
            return v
        result: dict = {}
        for key, value in v.items():
            # 直接写频道 ID
            if isinstance(value, (int, str)):
                result[key] = {"channel": value}
            else:
                result[key] = value
        return result


class _PermissionListConfigModel(BaseModel):
    """
    通用权限名单配置
    """

    users: list[int | str] = []
    """
    允许的用户 ID / 用户名列表
    """


class _ScopedPermissionListConfigModel(BaseModel):
    """
    支持全局和按服务器配置的权限名单
    """

    users: list[int | str] = []
    """全局允许的用户 ID / 用户名列表"""

    guilds: dict[int | str, list[int | str]] = {}
    """按服务器配置的允许列表，key 为 guild id，可写数字或字符串"""


class _ToolsConfigModel(BaseModel):
    """
    工具/管理指令模块配置
    指令: random, uuid, delete, clear-message, move-channel, sync
    """

    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = False
    """是否启用工具模块"""

    slash: bool = True
    """是否注册斜杠指令"""

    prefix: bool = True
    """是否注册前缀指令"""

    ratelimit: _ToolsRateLimitConfigModel = _ToolsRateLimitConfigModel()
    """限速配置 (random / uuid / 2file)"""

    clear_single_delete_max: int = 20
    """clear-message 批量清理时, 若超过 14 天不可批量删除的消息数不超过此值,
    则回退为逐条删除以规避 bulk delete 的 14 天限制; 设为 0 表示禁用回退"""

    @field_validator("clear_single_delete_max", mode="before")
    def normalize_clear_single_delete_max(cls, v):
        if v in (None, False):
            return 0
        return v


class _LockConfigModel(BaseModel):
    """
    频道锁定模块配置
    指令: lock, unlock, plan-lock
    """

    enabled: bool = False
    """是否启用锁定模块"""

    slash: bool = True
    """是否注册斜杠指令"""

    prefix: bool = True
    """是否注册前缀指令"""


class _SpamCatcherRuleConfigModel(BaseModel):
    """spam-catcher 单频道规则"""

    model_config = ConfigDict(populate_by_name=True)

    spammer: t.Literal["kick", "ban"] = "ban"
    """陌生账号处理方式"""

    hacked: t.Literal["kick", "ban", "mute"] | int = "mute"
    """正常账号疑似被盗处理方式: kick/ban/mute/分钟数"""

    clear_message: int | None = 3
    """清理消息窗口 (分钟), null/false 表示禁用"""

    public_log: bool = True
    """是否在频道公开通知处理结果"""
    unban_link: bool = False
    """是否在 antispam 解封日志中添加链接（需要 log_channel 配置）"""
    stranger_roles: list[int | str] = Field(default_factory=list)
    """被视为陌生账号的角色列表 (支持身份组 ID 或名称)"""

    ignored_roles: list[int | str] = Field(default_factory=list)
    """忽略处理的角色列表, 拥有任一角色的成员不会被处理 (支持身份组 ID 或名称)"""

    @field_validator("clear_message", mode="before")
    def normalize_clear_message(cls, v):
        if v in (None, False):
            return None
        if isinstance(v, bool):
            raise TypeError("clear_message must be int or null/false")
        return v

    @field_validator("hacked", mode="before")
    def normalize_hacked(cls, v):
        if isinstance(v, bool):
            raise TypeError("hacked must be kick/ban/mute or minutes")
        return v


class _AntiSpamConfigModel(BaseModel):
    """
    反垃圾消息模块配置
    无指令 (基于事件)
    """

    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = False
    """是否启用反垃圾消息模块"""

    spam_catcher: dict[int | str, _SpamCatcherRuleConfigModel] = Field(
        default_factory=dict
    )
    """按频道配置的捕获规则"""


class _PermConfigModel(BaseModel):
    """
    动态权限模块配置
    指令: /perm add, /perm rm, /perm show
    """

    enabled: bool = False
    """是否启用动态权限模块"""

    slash: bool = True
    """是否注册斜杠指令"""

    prefix: bool = True
    """是否注册前缀指令"""


class _AnnounceConfigModel(BaseModel):
    """
    公告推送模块配置
    指令: /subscribe
    """

    source_channel: int | None = None
    """
    公告频道 ID (News/Announcement Channel)
    - /subscribe 会使目标频道关注此频道
    - 设置为 None 禁用公告功能
    """


class _PresenceConfigModel(BaseModel):
    """
    Bot presence configuration (global).
    """

    enabled: bool = True
    """Enable custom presence"""

    activity: str = "Serving {servers} Servers with {members} Members"
    """Presence activity string, supports {servers} and {members} placeholders"""

    status: t.Literal["online", "idle", "dnd", "invisible"] = "online"
    """Discord status (online/dnd/idle/invisible)"""

    # optionally could add more fields later


class ConfigModel(BaseModel):
    """
    基础配置
    """

    token: str
    """Bot Token"""

    proxy: str | None = None
    """代理地址"""

    command_prefix: str = "\\"
    """命令前缀 (unused?)"""

    slash: bool = True
    """全局斜杠指令开关 (关闭后所有模块的斜杠指令均不注册)"""

    prefix: bool = True
    """全局前缀指令开关 (关闭后所有模块的前缀指令均不注册)"""

    secret_message_delay: int = 600
    """私密消息删除延迟 (秒)"""

    log: _LoggingConfigModel = _LoggingConfigModel()
    audit: _AuditLogConfigModel = _AuditLogConfigModel()
    emoji: _EmojiConfigModel = _EmojiConfigModel()
    tools: _ToolsConfigModel = _ToolsConfigModel()
    lock: _LockConfigModel = _LockConfigModel()
    antispam: _AntiSpamConfigModel = _AntiSpamConfigModel()
    rmtodo: _AutoRemoveTodoConfigModel = _AutoRemoveTodoConfigModel()
    rmmsg: _AutoRemoveMessageConfigModel = _AutoRemoveMessageConfigModel()
    voicechannel: _VoiceChannelConfigModel = _VoiceChannelConfigModel()
    presence: _PresenceConfigModel = _PresenceConfigModel()
    admins: _PermissionListConfigModel = _PermissionListConfigModel()
    mods: _ScopedPermissionListConfigModel = _ScopedPermissionListConfigModel()
    perm: _PermConfigModel = _PermConfigModel()
    announce: _AnnounceConfigModel = _AnnounceConfigModel()


def _normalize_config_keys(d: dict) -> dict:
    """Recursively normalize dict keys: replace '-' with '_'.

    If both forms like 'foo-bar' and 'foo_bar' exist, the '_' version has priority.
    """
    result = {}
    for key, value in d.items():
        if isinstance(value, dict):
            value = _normalize_config_keys(value)
        if isinstance(key, str):
            normalized = key.replace("-", "_")
            if "-" in key:
                if normalized not in result:
                    result[normalized] = value
            else:
                result[normalized] = value
        else:
            result[key] = value
    return result


class Config:
    """
    配置系统
    """

    config: ConfigModel

    def __init__(
        self,
        config_path: str | None = None,
        token_file: str | None = None,
        token: str | None = None,
    ):
        """
        初始化配置系统

        :param config_path: 配置文件路径 (默认: 先查找数据目录, 未找到再回退到主程序目录下的 config.yaml)
        :param token_file: token 文件路径 (默认: 先查找数据目录, 未找到再回退到主程序目录下的 tk.yaml)
        :param token: 直接指定 token, 优先级最高 (覆盖配置文件和 token 文件)
        """
        perf = u.perf_counter()

        self._config_path = config_path
        self._token_file = token_file
        self._token = token

        # resolve config path: 自定义路径按当前工作目录解析, 默认路径优先查找数据目录再回退到主程序目录
        if config_path:
            resolved_config = str(Path(config_path).expanduser())
        else:
            resolved_config = u.get_data_path("config.yaml", for_read=True)

        # prepare yaml
        try:
            with open(resolved_config, "r", encoding="utf-8") as f:
                raw_config: dict = safe_load(f)
        except FileNotFoundError:
            l.error(f"Config file {resolved_config} not found!")
            sys.exit(1)
        except Exception as e:
            l.error(f"Error when loading {resolved_config}: {e}")
            sys.exit(1)

        # load token from token file if it exists (for config splitting)
        # 自定义 token 文件路径按当前工作目录解析, 默认优先查找数据目录再回退到主程序目录
        if token_file:
            tk_path = str(Path(token_file).expanduser())
            tk_required = True
        else:
            tk_path = u.get_data_path("tk.yaml", for_read=True)
            tk_required = False
        if Path(tk_path).exists():
            try:
                with open(tk_path, "r", encoding="utf-8") as f:
                    tk_data: dict = safe_load(f)
                if isinstance(tk_data, dict) and "token" in tk_data:
                    raw_config["token"] = tk_data["token"]
                    l.info(f"[config] Loaded token from {tk_path}")
                else:
                    l.warning(f"[config] No 'token' key found in {tk_path}")
            except Exception as e:
                l.warning(f"[config] Failed to load {tk_path}: {e}")
        elif tk_required:
            l.error(f"Token file {tk_path} not found!")
            sys.exit(1)

        # 直接指定的 token 优先级最高, 覆盖配置文件和 token 文件
        # (来自 --token 参数或 W9DCBOT_TOKEN 环境变量)
        if token:
            raw_config["token"] = token
            l.info("[config] Using token from argument/environment variable")

        # normalize keys: support both '-' and '_' forms, '_' has priority
        raw_config = _normalize_config_keys(raw_config)

        # process config
        self.config = ConfigModel.model_validate(raw_config)

        if self.config.log.level == "DEBUG":
            l.debug(f"[config] init took {perf()}ms")
