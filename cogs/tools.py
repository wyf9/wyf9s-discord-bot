import io
import random
import re
from datetime import datetime, timezone
from uuid import uuid4 as uuid

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger as l

import utils as u
from i18n import lang_of, ls
from i18n import t as _t
from modules.audit import AuditLogger
from modules.clear_message import CLEAR_MESSAGE_MARKER, ClearMessageService


def _parse_flags(content: str) -> dict[str, str]:
    return u.parse_flags(content)


class ClearMessageResultView(discord.ui.View):
    def __init__(self, tools: "ToolsCog", guild: discord.Guild | None):
        super().__init__(timeout=None)
        self.tools = tools
        self.guild = guild

    @discord.ui.button(label="OK", style=discord.ButtonStyle.secondary)
    async def btn_ok(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not u.is_mod(interaction.user, self.tools.c, self.guild):
            await interaction.response.send_message(
                self.tools._tr(interaction, "tools.clear_btn_no_permission"),
                ephemeral=True,
            )
            return
        self.stop()
        try:
            await interaction.response.defer()
        except discord.HTTPException:
            pass
        msg = interaction.message
        if msg is not None:
            try:
                await msg.delete()
                return
            except discord.HTTPException:
                pass
        try:
            await interaction.delete_original_response()
        except discord.HTTPException:
            pass


class ToolsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.c = bot.config  # ty:ignore[unresolved-attribute]
        self.audit: AuditLogger | None = getattr(bot, "audit", None)
        self.rate_limiter = getattr(bot, "rate_limiter", u.RateLimiter())
        self.lang_store = getattr(bot, "lang_store", None)
        self.clear_message = ClearMessageService(
            config=self.c, client=bot, audit=self.audit
        )

    def _tr(self, source, key: str, **kwargs) -> str:
        return _t(key, lang_of(source, self.lang_store), **kwargs)

    def _lang(self, source) -> str:
        return lang_of(source, self.lang_store)

    @staticmethod
    def _bool_choices() -> list[app_commands.Choice[int]]:
        return [
            app_commands.Choice(name="True", value=1),
            app_commands.Choice(name="False", value=0),
        ]

    @staticmethod
    def _clear_scope_choices() -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name="channel", value="channel"),
            app_commands.Choice(name="server", value="server"),
        ]

    # ========== Slash Commands ==========

    @app_commands.command(name="random", description=ls("tools.cmd_random_desc"))
    @app_commands.describe(
        min_num=ls("tools.param_random_min"), max_num=ls("tools.param_random_max")
    )
    async def slash_random(
        self, interaction: discord.Interaction, min_num: int = 1, max_num: int = 114514
    ):
        await self._handle_random(interaction, min_num, max_num)

    @app_commands.command(name="uuid", description=ls("tools.cmd_uuid_desc"))
    @app_commands.describe(delete_after=ls("tools.param_uuid_delete_after"))
    async def slash_uuid(self, interaction: discord.Interaction, delete_after: int = 0):
        if delete_after <= 0:
            delete_after = self.c.secret_message_delay
        await self._handle_uuid(interaction, delete_after)

    @app_commands.command(name="delete", description=ls("tools.cmd_delete_desc"))
    @app_commands.describe(
        message_id=ls("tools.param_delete_message_id"),
        show_to_public=ls("tools.param_delete_show_public"),
    )
    @app_commands.choices(show_to_public=_bool_choices())
    @u.requires(u.Permission.MOD, perm_module="tools")
    async def slash_delete(
        self,
        interaction: discord.Interaction,
        message_id: str,
        show_to_public: int = 0,
    ):
        await self._handle_delete(interaction, message_id, bool(show_to_public))

    @app_commands.command(name="clear-message", description=ls("tools.cmd_clear_desc"))
    @app_commands.describe(
        user=ls("tools.param_clear_user"),
        user_ids=ls("tools.param_clear_user_ids"),
        webhook_ids=ls("tools.param_clear_webhook_ids"),
        nick_pattern=ls("tools.param_clear_nick_pattern"),
        content_pattern=ls("tools.param_clear_content_pattern"),
        message_count=ls("tools.param_clear_message_count"),
        within_minutes=ls("tools.param_clear_within_minutes"),
        scope=ls("tools.param_clear_scope"),
        channel=ls("tools.param_clear_channel"),
        start=ls("tools.param_clear_start"),
        end=ls("tools.param_clear_end"),
        delete_threads=ls("tools.param_clear_delete_threads"),
        forum_scan_count=ls("tools.param_clear_forum_scan_count"),
    )
    @app_commands.choices(scope=_clear_scope_choices())
    @app_commands.choices(delete_threads=_bool_choices())
    @u.requires(u.Permission.MOD, perm_module="tools")
    async def slash_clear_message(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
        user_ids: str | None = None,
        webhook_ids: str | None = None,
        nick_pattern: str | None = None,
        content_pattern: str | None = None,
        message_count: int | None = None,
        within_minutes: int | None = None,
        scope: str = "channel",
        channel: discord.TextChannel
        | discord.VoiceChannel
        | discord.StageChannel
        | discord.ForumChannel
        | None = None,
        start: str | None = None,
        end: str | None = None,
        delete_threads: int = 0,
        forum_scan_count: int | None = None,
    ):
        await interaction.response.defer()
        result = await self._do_clear_message(
            interaction.user,
            interaction.guild,
            interaction.channel,
            lang=self._lang(interaction),
            user=user,
            user_ids=user_ids,
            webhook_ids=webhook_ids,
            nick_pattern=nick_pattern,
            content_pattern=content_pattern,
            message_count=message_count,
            within_minutes=within_minutes,
            scope=scope,
            channel_target=channel,
            start=start,
            end=end,
            delete_threads=bool(delete_threads),
            forum_scan_count=forum_scan_count,
        )
        view = (
            ClearMessageResultView(self, interaction.guild)
            if CLEAR_MESSAGE_MARKER in result
            else discord.utils.MISSING
        )
        await interaction.followup.send(result, ephemeral=True, view=view)

    @app_commands.command(name="move-channel", description=ls("tools.cmd_move_desc"))
    @app_commands.describe(
        target_channel=ls("tools.param_move_target"),
        category=ls("tools.param_move_category"),
        before=ls("tools.param_move_before"),
        after=ls("tools.param_move_after"),
        sync_perm=ls("tools.param_move_sync_perm"),
    )
    @app_commands.choices(sync_perm=_bool_choices())
    @u.requires(u.Permission.MOD, perm_module="tools")
    async def slash_move_channel(
        self,
        interaction: discord.Interaction,
        target_channel: discord.abc.GuildChannel | None = None,
        category: discord.CategoryChannel | None = None,
        before: discord.abc.GuildChannel | None = None,
        after: discord.abc.GuildChannel | None = None,
        sync_perm: int = 1,
    ):
        await self._handle_move_channel(
            interaction, target_channel, category, before, after, bool(sync_perm)
        )

    @app_commands.command(name="to-file", description=ls("tools.cmd_tofile_desc"))
    @app_commands.describe(
        name=ls("tools.param_tofile_name"), content=ls("tools.param_tofile_content")
    )
    async def slash_to_file(
        self, interaction: discord.Interaction, name: str, content: str
    ):
        await self._handle_to_file(interaction, name, content)

    # ========== Prefix Commands ==========

    @commands.command(name="random")
    async def prefix_random(
        self, ctx: commands.Context, min_num: int = 1, max_num: int = 114514
    ):
        await self._handle_random(ctx, min_num, max_num)

    @commands.command(name="uuid")
    async def prefix_uuid(self, ctx: commands.Context, delete_after: int = 0):
        if delete_after <= 0:
            delete_after = self.c.secret_message_delay
        await self._handle_uuid(ctx, delete_after)

    @commands.command(name="delete")
    @u.requires(u.Permission.MOD, perm_module="tools")
    async def prefix_delete(
        self, ctx: commands.Context, message_id: str, show_to_public: str = "false"
    ):
        try:
            parsed = u.parse_bool(show_to_public)
        except ValueError:
            await ctx.send(
                self._tr(ctx, "tools.bool_invalid", value=show_to_public),
                delete_after=10,
            )
            return
        await self._handle_delete(ctx, message_id, parsed)

    @commands.command(name="clear-message")
    @u.requires(u.Permission.MOD, perm_module="tools")
    async def prefix_clear_message(self, ctx: commands.Context):
        flags = _parse_flags(ctx.message.content)

        user = None
        if "user" in flags:
            user_str = flags["user"]
            m = re.match(r"<@!?(\d+)>", user_str)
            if m:
                try:
                    user = await self.bot.fetch_user(int(m.group(1)))
                except discord.NotFound:
                    pass
            elif user_str.isdigit():
                try:
                    user = await self.bot.fetch_user(int(user_str))
                except discord.NotFound:
                    pass

        user_ids = flags.get("user-ids") or flags.get("user_ids") or None
        webhook_ids = flags.get("webhook-ids") or flags.get("webhook_ids") or None
        nick_pattern = (
            flags.get("nick")
            or flags.get("nick-pattern")
            or flags.get("nick_pattern")
            or None
        )
        content_pattern = (
            flags.get("content")
            or flags.get("content-pattern")
            or flags.get("content_pattern")
            or None
        )

        message_count = None
        if "count" in flags:
            try:
                message_count = int(flags["count"])
            except ValueError:
                await ctx.send(
                    self._mark_clear_message(self._tr(ctx, "tools.clear_count_int")),
                    delete_after=10,
                )
                return

        within_minutes = None
        if "within" in flags:
            val = flags["within"]
            m = re.fullmatch(r"(\d+)([dhm])", val)
            if m:
                n = int(m.group(1))
                unit = m.group(2)
                if unit == "d":
                    within_minutes = n * 1440
                elif unit == "h":
                    within_minutes = n * 60
                elif unit == "m":
                    within_minutes = n
            elif val.isdigit():
                within_minutes = int(val)
            else:
                await ctx.send(
                    self._mark_clear_message(
                        self._tr(ctx, "tools.clear_within_invalid")
                    ),
                    delete_after=10,
                )
                return

        scope = flags.get("scope", "channel")

        channel = None
        if "channel" in flags:
            ch_str = flags["channel"]
            m = re.match(r"<#(\d+)>", ch_str)
            if m:
                channel = self.bot.get_channel(int(m.group(1)))
            elif ch_str.isdigit():
                channel = self.bot.get_channel(int(ch_str))

        start = flags.get("start") or None
        end = flags.get("end") or None

        delete_threads = False
        dt_flag = (
            flags.get("delete-threads")
            or flags.get("delete_threads")
            or flags.get("delete-thread")
        )
        if dt_flag is not None:
            try:
                delete_threads = u.parse_bool(dt_flag) if dt_flag != "" else True
            except ValueError:
                await ctx.send(
                    self._mark_clear_message(
                        self._tr(ctx, "tools.bool_invalid", value=dt_flag)
                    ),
                    delete_after=10,
                )
                return

        forum_scan_count = None
        fsc_flag = (
            flags.get("forum-scan-count")
            or flags.get("forum_scan_count")
            or flags.get("forum-scan")
        )
        if fsc_flag is not None:
            try:
                forum_scan_count = int(fsc_flag)
            except ValueError:
                await ctx.send(
                    self._mark_clear_message(
                        self._tr(ctx, "tools.clear_forum_scan_int")
                    ),
                    delete_after=10,
                )
                return

        await ctx.defer()
        result = await self._do_clear_message(
            ctx.author,
            ctx.guild,
            ctx.channel,
            lang=self._lang(ctx),
            user=user,
            user_ids=user_ids,
            webhook_ids=webhook_ids,
            nick_pattern=nick_pattern,
            content_pattern=content_pattern,
            message_count=message_count,
            within_minutes=within_minutes,
            scope=scope,
            channel_target=channel,
            start=start,
            end=end,
            delete_threads=delete_threads,
            forum_scan_count=forum_scan_count,
        )
        is_success = CLEAR_MESSAGE_MARKER in result
        view = (
            ClearMessageResultView(self, ctx.guild)
            if is_success
            else discord.utils.MISSING
        )
        await ctx.send(self._mark_clear_message(result), view=view)

    @commands.command(name="move-channel")
    @u.requires(u.Permission.MOD, perm_module="tools")
    async def prefix_move_channel(
        self,
        ctx: commands.Context,
        target_channel: discord.abc.GuildChannel | None = None,
        category: discord.CategoryChannel | None = None,
        sync_perm: str = "true",
    ):
        try:
            parsed = u.parse_bool(sync_perm)
        except ValueError:
            await ctx.send(
                self._tr(ctx, "tools.bool_invalid", value=sync_perm), delete_after=10
            )
            return
        await self._handle_move_channel(
            ctx, target_channel, category, None, None, parsed
        )

    @commands.command(name="to-file")
    async def prefix_to_file(self, ctx: commands.Context, name: str, *, content: str):
        await self._handle_to_file(ctx, name, content)

    # ========== Shared Logic ==========

    async def _handle_random(self, source, min_num: int = 1, max_num: int = 114514):
        if not await self._check_rate_limit(source, "random"):
            return
        try:
            if min_num > max_num:
                min_num, max_num = max_num, min_num
            result = random.randint(min_num, max_num)
            await u.send_msg(
                source,
                self._tr(
                    source,
                    "tools.random_result",
                    min=min_num,
                    max=max_num,
                    result=result,
                ),
            )
        except ValueError:
            await u.send_msg(
                source,
                self._tr(source, "tools.random_invalid"),
                ephemeral=True,
                delete_after=10,
            )

    async def _handle_uuid(self, source, delete_after: int):
        if not await self._check_rate_limit(source, "uuid"):
            return
        now = int(datetime.now(tz=timezone.utc).timestamp())
        await u.send_msg(
            source,
            self._tr(
                source,
                "tools.uuid_result",
                uuid=uuid(),
                ts=now + delete_after,
            ),
            ephemeral=True,
            delete_after=delete_after,
        )

    async def _handle_to_file(self, source, name: str, content: str):
        if not await self._check_rate_limit(source, "to-file"):
            return
        bio = io.BytesIO(content.encode("utf-8"))
        await u.send_msg(source, "", file=discord.File(fp=bio, filename=name))

    async def _handle_delete(
        self, source, message_id: str, show_to_public: bool = False
    ):
        user = source.user if isinstance(source, discord.Interaction) else source.author
        if not message_id:
            await u.send_msg(
                source,
                self._tr(source, "tools.delete_no_id"),
                ephemeral=True,
                delete_after=10,
            )
            return
        try:
            message_id_int = int(message_id)
            channel = source.channel
            message = channel.get_partial_message(message_id_int)
            await message.delete()
        except discord.Forbidden:
            await u.send_msg(
                source,
                self._tr(source, "common.permission_denied"),
                ephemeral=True,
                delete_after=10,
            )
        except discord.NotFound:
            await u.send_msg(
                source,
                self._tr(source, "tools.delete_not_found", id=message_id),
                ephemeral=True,
                delete_after=10,
            )
        except ValueError:
            await u.send_msg(
                source,
                self._tr(source, "tools.delete_invalid_id", id=message_id),
                ephemeral=True,
                delete_after=10,
            )
        except Exception as e:
            await u.send_msg(
                source,
                self._tr(source, "tools.delete_error", id=message_id, error=e),
                ephemeral=True,
                delete_after=10,
            )
        else:
            await u.send_msg(
                source,
                self._tr(source, "tools.delete_ok", id=message_id),
                ephemeral=not show_to_public,
            )
            if self.audit:
                await self.audit.log(
                    action="delete",
                    user=user,
                    guild=source.guild,
                    channel=source.channel,
                    detail=f"Deleted message `{message_id}`",
                )

    async def _do_clear_message(
        self,
        author,
        guild,
        channel,
        **kwargs,
    ) -> str:
        return await self.clear_message.do_clear_message(
            author=author, guild=guild, channel=channel, **kwargs
        )

    def _move_position_parts(self, source, category, before, after) -> str:
        msg_parts = []
        if category:
            msg_parts.append(
                self._tr(source, "tools.move_part_category", name=category.name)
            )
        if before:
            msg_parts.append(
                self._tr(source, "tools.move_part_before", name=before.name)
            )
        elif after:
            msg_parts.append(self._tr(source, "tools.move_part_after", name=after.name))
        return " / ".join(msg_parts)

    async def _handle_move_channel(
        self,
        source,
        target_channel=None,
        category=None,
        before=None,
        after=None,
        sync_perm=True,
    ):
        user = source.user if isinstance(source, discord.Interaction) else source.author
        if not category and not before and not after:
            await u.send_msg(
                source,
                self._tr(source, "tools.move_need_target"),
                ephemeral=True,
                delete_after=10,
            )
            return
        if before and after:
            await u.send_msg(
                source,
                self._tr(source, "tools.move_both_before_after"),
                ephemeral=True,
                delete_after=10,
            )
            return
        channel = target_channel or source.channel
        if not isinstance(channel, discord.abc.GuildChannel):
            await u.send_msg(
                source,
                self._tr(source, "tools.move_only_guild"),
                ephemeral=True,
                delete_after=10,
            )
            return

        # Safety: non-admin mods must have manage_channels on the target channel
        if (
            not u.is_admin(user, self.c)
            and not u.is_server_admin(user)
            and isinstance(user, discord.Member)
        ):
            perms = channel.permissions_for(user)
            if not perms.manage_channels:
                await u.send_msg(
                    source,
                    self._tr(source, "tools.move_no_manage_channels"),
                    ephemeral=True,
                    delete_after=10,
                )
                return

        kwargs = {}
        update_category = False
        target_category = None
        if category:
            target_category = category
            update_category = True
        if before:
            if not update_category:
                target_category = getattr(before, "category", None)
                update_category = True
            kwargs["position"] = before.position
        elif after:
            if not update_category:
                target_category = getattr(after, "category", None)
                update_category = True
            kwargs["position"] = after.position + 1
        if update_category:
            kwargs["category"] = target_category
            if sync_perm:
                kwargs["sync_permissions"] = True
        try:
            await channel.edit(**kwargs)  # type: ignore[attr-defined]
            position = self._move_position_parts(source, category, before, after)
            await u.send_msg(
                source,
                self._tr(
                    source,
                    "tools.move_ok",
                    channel=channel.mention,
                    position=position,
                ),
            )
            if self.audit:
                await self.audit.log(
                    action="move-channel",
                    user=user,
                    guild=source.guild,
                    channel=source.channel,
                    detail=f"Moved channel `{channel.name}` to {position}",
                )
        except discord.Forbidden:
            await u.send_msg(
                source,
                self._tr(source, "tools.move_forbidden"),
                ephemeral=True,
                delete_after=10,
            )
        except discord.HTTPException as e:
            await u.send_msg(
                source,
                self._tr(source, "tools.move_api_error", status=e.status, text=e.text),
                ephemeral=True,
                delete_after=10,
            )
        except Exception as e:
            await u.send_msg(
                source,
                self._tr(source, "tools.move_unexpected", error=e),
                ephemeral=True,
                delete_after=10,
            )

    async def _check_rate_limit(self, source, command: str) -> bool:
        user = source.user if isinstance(source, discord.Interaction) else source.author
        guild = getattr(source, "guild", None)
        params = u.resolve_rate_limit(self.c, user, guild, "tools", command)
        if params is None:
            return True
        limit, window = params
        allowed, retry_after = self.rate_limiter.hit((command, user.id), limit, window)
        if not allowed:
            await u.send_msg(
                source,
                self._tr(source, "common.rate_limited", retry=f"{retry_after:.0f}"),
                ephemeral=True,
                delete_after=10,
            )
            return False
        return True

    @staticmethod
    def _mark_clear_message(text: str) -> str:
        if CLEAR_MESSAGE_MARKER in text:
            return text
        return f"{text}\n-# {CLEAR_MESSAGE_MARKER}"


async def setup(bot: commands.Bot):
    if bot.config.tools.enabled:  # ty:ignore[unresolved-attribute]
        await bot.add_cog(ToolsCog(bot))
        l.info("ToolsCog loaded.")
