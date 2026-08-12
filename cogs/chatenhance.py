import io
import re
from urllib.parse import urlencode

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger as l

import utils as u
from enhance_store import EnhanceStore
from i18n import lang_of, ls
from i18n import t as _t
from modules.audit import AuditLogger

# 匹配 x.com / twitter.com 的推文链接: https://x.com/user/status/<id>
_TWEET_URL_RE = re.compile(
    r"https?://(?:[^/\s]*\.)?(?:x|twitter)\.com/([A-Za-z0-9_]+)/status/(\d+)",
    re.IGNORECASE,
)
# 已转换过的域名 (fixupx.com / fxtwitter.com), 出现则不再重复处理
_FIXED_URL_RE = re.compile(
    r"https?://(?:[^/\s]*\.)?(?:fixupx|fxtwitter)\.com/([A-Za-z0-9_]+)/status/(\d+)",
    re.IGNORECASE,
)

KNOWN_FUNCTIONS = ("autofixupx",)


def _enhance_admin_permission(
    module: "ChatEnhanceCog",
    user: discord.User | discord.Member,
    guild: discord.Guild | None,
) -> bool:
    return u.is_admin(user, module.c) or u.is_server_admin(user)


class ChatEnhanceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.c = bot.config  # ty:ignore[unresolved-attribute]
        self.audit: AuditLogger | None = getattr(bot, "audit", None)
        self.lang_store = getattr(bot, "lang_store", None)
        self.enhance_store: EnhanceStore = (
            getattr(bot, "enhance_store", None) or EnhanceStore()
        )
        bot.enhance_store = self.enhance_store  # ty:ignore[unresolved-attribute]

    def _tr(self, source, key: str, **kwargs) -> str:
        return _t(key, lang_of(source, self.lang_store), **kwargs)

    def _guild_lang(self, guild: discord.Guild | None) -> str:
        if self.lang_store and guild:
            return self.lang_store.resolve(0, guild.id)
        return "zh"

    # ========== Message handler ==========

    @commands.Cog.listener("on_message")
    async def autofixupx_handler(self, message: discord.Message):
        try:
            await self._handle_autofixupx(message)
        except Exception as e:
            l.exception(f"[chatenhance] Error handling message: {e}")

    async def _handle_autofixupx(self, message: discord.Message):
        if message.author.bot or message.webhook_id is not None:
            return
        if message.guild is None:
            return
        if not self.enhance_store.is_enabled(message.guild.id, "autofixupx"):
            return
        if not isinstance(message.channel, (discord.TextChannel, discord.Thread)):
            return

        cfg = self.c.chatenhance.autofixupx
        lang = self._guild_lang(message.guild)

        if cfg.mode in ("fixupx", "both") and _FIXED_URL_RE.search(message.content):
            return

        matches = list(_TWEET_URL_RE.finditer(message.content))
        if not matches:
            return

        seen: set[str] = set()
        tweets: list[tuple[str, str]] = []
        for m in matches:
            key = f"{m.group(1).lower()}/status/{m.group(2)}"
            if key in seen:
                continue
            seen.add(key)
            tweets.append((m.group(1), m.group(2)))
            if len(tweets) >= max(1, cfg.limit):
                break

        if cfg.mode == "x-to-img":
            if not cfg.x_to_img_url:
                await self._reply_auto(
                    message,
                    content=_t("chatenhance.autofixupx_no_api_error", lang),
                    lang=lang,
                )
                return
            await self._reply_x_to_img(message, tweets, cfg, lang)
            return

        link_lines = [f"https://fixupx.com/{user}/status/{sid}" for user, sid in tweets]
        if cfg.mode == "both" and cfg.x_to_img_url:
            files = await self._fetch_tweet_images(tweets, cfg)
            await self._reply_auto(
                message,
                content="\n".join(link_lines),
                files=files,
                lang=lang,
            )
        else:
            content = "\n".join(link_lines)
            if cfg.mode == "both":
                content += (
                    "\n-# *" + _t("chatenhance.autofixupx_no_api_warning", lang) + "*"
                )
            await self._reply_auto(message, content=content, lang=lang)

    async def _reply_x_to_img(
        self,
        message: discord.Message,
        tweets: list[tuple[str, str]],
        cfg,
        lang: str,
    ):
        files = await self._fetch_tweet_images(tweets, cfg)
        if len(files) == len(tweets):
            await self._reply_auto(message, files=files, lang=lang)
        elif files:
            await self._reply_auto(
                message,
                content=_t("chatenhance.autofixupx_partial_failed", lang),
                files=files,
                lang=lang,
            )
        else:
            await self._reply_auto(
                message,
                content=_t("chatenhance.autofixupx_all_failed", lang),
                lang=lang,
            )

    async def _fetch_tweet_images(
        self, tweets: list[tuple[str, str]], cfg
    ) -> list[discord.File]:
        """调用 x-to-img API 将推文渲染为图片, 返回成功的图片文件列表"""
        files: list[discord.File] = []
        headers = (
            {"Authorization": f"Bearer {cfg.api_token}"} if cfg.api_token else None
        )
        base_url = cfg.x_to_img_url.rstrip("/")
        async with aiohttp.ClientSession() as session:
            for user, sid in tweets:
                query = urlencode(
                    {
                        "url": f"https://x.com/{user}/status/{sid}",
                        "theme": cfg.theme,
                    }
                )
                api_url = f"{base_url}/api/convert?{query}"
                try:
                    async with session.get(
                        api_url, proxy=self.c.proxy, headers=headers
                    ) as resp:
                        if resp.status != 200:
                            raise aiohttp.ClientResponseError(
                                request_info=resp.request_info,
                                history=resp.history,
                                status=resp.status,
                                message=f"Status code isn't 200: {resp.status}",
                            )
                        data = await resp.read()
                        files.append(
                            discord.File(
                                io.BytesIO(data),
                                filename=f"tweet-{sid}.png",
                            )
                        )
                except Exception as e:
                    l.warning(f"[chatenhance] Failed to convert {api_url}: {e}")
        return files

    async def _reply_auto(
        self,
        message: discord.Message,
        *,
        content: str | None = None,
        files: list[discord.File] | None = None,
        lang: str,
    ):
        if not content and not files:
            return
        try:
            await message.reply(
                content=content or None,
                files=files or None,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException as e:
            l.warning(f"[chatenhance] Failed to reply ({lang}): {e}")

    # ========== /enhance enable | disable | list ==========

    enhance_group = app_commands.Group(
        name="enhance", description=ls("chatenhance.group_desc")
    )

    @enhance_group.command(name="enable", description=ls("chatenhance.cmd_enable_desc"))
    @app_commands.describe(function=ls("chatenhance.param_function"))
    @app_commands.choices(
        function=[app_commands.Choice(name="autofixupx", value="autofixupx")]
    )
    @u.requires(_enhance_admin_permission, perm_module="chatenhance")
    async def enhance_enable(self, interaction: discord.Interaction, function: str):
        await self._handle_toggle(interaction, function, enable=True)

    @enhance_group.command(
        name="disable", description=ls("chatenhance.cmd_disable_desc")
    )
    @app_commands.describe(function=ls("chatenhance.param_function"))
    @app_commands.choices(
        function=[app_commands.Choice(name="autofixupx", value="autofixupx")]
    )
    @u.requires(_enhance_admin_permission, perm_module="chatenhance")
    async def enhance_disable(self, interaction: discord.Interaction, function: str):
        await self._handle_toggle(interaction, function, enable=False)

    @enhance_group.command(name="list", description=ls("chatenhance.cmd_list_desc"))
    @u.requires(_enhance_admin_permission, perm_module="chatenhance")
    async def enhance_list(self, interaction: discord.Interaction):
        await self._handle_list(interaction)

    # ========== Prefix Commands ==========

    @commands.group(name="enhance", invoke_without_command=True)
    async def prefix_enhance(self, ctx: commands.Context):
        await ctx.send(self._tr(ctx, "chatenhance.usage_prefix"))

    @prefix_enhance.command(name="enable")
    @u.requires(_enhance_admin_permission, perm_module="chatenhance")
    async def prefix_enhance_enable(self, ctx: commands.Context, function: str):
        await self._handle_toggle(ctx, function, enable=True)

    @prefix_enhance.command(name="disable")
    @u.requires(_enhance_admin_permission, perm_module="chatenhance")
    async def prefix_enhance_disable(self, ctx: commands.Context, function: str):
        await self._handle_toggle(ctx, function, enable=False)

    @prefix_enhance.command(name="list")
    @u.requires(_enhance_admin_permission, perm_module="chatenhance")
    async def prefix_enhance_list(self, ctx: commands.Context):
        await self._handle_list(ctx)

    # ========== Shared Logic ==========

    async def _handle_toggle(self, source, function: str, *, enable: bool):
        is_interaction = isinstance(source, discord.Interaction)
        actor = source.user if is_interaction else source.author

        function = function.strip().lower()
        if function not in KNOWN_FUNCTIONS:
            await u.send_msg(
                source,
                self._tr(source, "chatenhance.function_invalid", function=function),
                ephemeral=True,
            )
            return
        if source.guild is None:
            await u.send_msg(
                source,
                self._tr(source, "chatenhance.server_only"),
                ephemeral=True,
            )
            return

        guild_id = source.guild.id
        changed = (
            self.enhance_store.enable(guild_id, function)
            if enable
            else self.enhance_store.disable(guild_id, function)
        )
        if enable:
            msg_key = (
                "chatenhance.already_enabled" if not changed else "chatenhance.enabled"
            )
        else:
            msg_key = (
                "chatenhance.not_enabled" if not changed else "chatenhance.disabled"
            )
        await u.send_msg(source, self._tr(source, msg_key, function=function))

        if changed and self.audit:
            await self.audit.log(
                action="enhance-enable" if enable else "enhance-disable",
                user=actor,
                guild=source.guild,
                channel=source.channel,
                detail=f"Function `{function}` {'enabled' if enable else 'disabled'}",
            )

    async def _handle_list(self, source):
        if source.guild is None:
            await u.send_msg(
                source,
                self._tr(source, "chatenhance.server_only"),
                ephemeral=True,
            )
            return

        enabled = set(self.enhance_store.list_enabled(source.guild.id))
        lines = [
            self._tr(
                source,
                "chatenhance.list_item",
                status=":white_check_mark:" if fn in enabled else ":x:",
                function=fn,
            )
            for fn in KNOWN_FUNCTIONS
        ]
        await u.send_msg(
            source,
            self._tr(source, "chatenhance.list_title") + "\n" + "\n".join(lines),
        )


async def setup(bot: commands.Bot):
    if bot.config.chatenhance.enabled:  # ty:ignore[unresolved-attribute]
        await bot.add_cog(ChatEnhanceCog(bot))
        l.info("ChatEnhanceCog loaded.")
