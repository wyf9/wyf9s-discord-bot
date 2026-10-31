import asyncio
import functools
import json

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger as l

import utils as u
from i18n import lang_of, ls
from i18n import t as _t
from modules.audit import AuditLogger


def _read_json(path: str, default: dict | None = None) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def _write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _voice_permission(
    module: "VoiceCog",
    user: discord.User | discord.Member,
    guild: discord.Guild | None,
) -> bool:
    vc = module.c.voicechannel
    if user.id in vc.allowed_users or user.name in vc.allowed_users:
        return True
    if isinstance(user, discord.Member) and guild is not None:
        guild_users = vc.allowed_guilds.get(
            guild.id, vc.allowed_guilds.get(str(guild.id), [])
        )
        if u.matches_identity(user, guild_users):
            return True
    return u.is_mod(user, module.c, guild)


class VoiceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.c = bot.config  # ty:ignore[unresolved-attribute]
        self.audit: AuditLogger | None = getattr(bot, "audit", None)
        self.lang_store = getattr(bot, "lang_store", None)
        self.rate_limiter = getattr(bot, "rate_limiter", u.RateLimiter())
        self._reconnecting: set[int] = set()  # guild IDs currently reconnecting
        self._last_vc: dict[int, int] = {}  # guild_id -> channel_id before disconnect
        self._intentional_disconnect: set[int] = set()  # guild IDs from /vc leave

    def _tr(self, source, key: str, **kwargs) -> str:
        return _t(key, lang_of(source, self.lang_store), **kwargs)

    # ========== Slash Group: /vc ==========

    vc_group = app_commands.Group(name="vc", description=ls("voice.cmd_group_desc"))

    @vc_group.command(name="join", description=ls("voice.cmd_join_desc"))
    @app_commands.describe(
        channel=ls("voice.param_join_channel"), persist=ls("voice.param_persist")
    )
    @u.requires(_voice_permission, perm_module="voice")
    async def vc_join(
        self,
        interaction: discord.Interaction,
        channel: discord.VoiceChannel | None = None,
        persist: bool = False,
    ):
        await self._handle_joinvc(interaction, channel, persist)

    @vc_group.command(name="leave", description=ls("voice.cmd_leave_desc"))
    @u.requires(_voice_permission, perm_module="voice")
    async def vc_leave(self, interaction: discord.Interaction):
        await self._handle_leavevc(interaction)

    # ========== Prefix Group: vc ==========

    @commands.group(name="vc", invoke_without_command=True)
    async def prefix_vc(self, ctx: commands.Context):
        await ctx.send(self._tr(ctx, "voice.usage_prefix"))

    @prefix_vc.command(name="join")
    @u.requires(_voice_permission, perm_module="voice")
    async def prefix_vc_join(
        self,
        ctx: commands.Context,
        channel: discord.VoiceChannel | None = None,
        persist: bool = False,
    ):
        await self._handle_joinvc(ctx, channel, persist)

    @prefix_vc.command(name="leave")
    @u.requires(_voice_permission, perm_module="voice")
    async def prefix_vc_leave(self, ctx: commands.Context):
        await self._handle_leavevc(ctx)

    async def _handle_joinvc(
        self, source, channel: discord.VoiceChannel | None = None, persist: bool = False
    ):
        if not await u.check_rate_limit(
            source,
            config=self.c,
            rate_limiter=self.rate_limiter,
            module="voicechannel",
            command="vc join",
        ):
            return
        user = source.user if isinstance(source, discord.Interaction) else source.author

        if channel is None and isinstance(user, discord.Member):
            if (
                not user.voice
                or not user.voice.channel
                or isinstance(user.voice.channel, discord.StageChannel)
            ):
                await u.send_msg(
                    source,
                    self._tr(source, "voice.join_first"),
                    ephemeral=True,
                    delete_after=10,
                )
                return
            channel = user.voice.channel

        if not isinstance(channel, discord.VoiceChannel):
            await u.send_msg(
                source,
                self._tr(source, "voice.not_voice_channel"),
                ephemeral=True,
                delete_after=10,
            )
            return

        try:
            guild = source.guild
            if guild and guild.voice_client:
                if (
                    isinstance(guild.voice_client.channel, discord.VoiceChannel)
                    and guild.voice_client.channel.id == channel.id
                ):
                    await u.send_msg(
                        source,
                        self._tr(source, "voice.already_in", channel=channel.name),
                        ephemeral=True,
                        delete_after=10,
                    )
                    return
                await guild.voice_client.disconnect(force=False)
                await channel.connect(self_deaf=True, self_mute=True)
                await u.send_msg(
                    source, self._tr(source, "voice.moved_to", channel=channel.name)
                )
            else:
                await channel.connect(self_deaf=True, self_mute=True)
                await u.send_msg(
                    source, self._tr(source, "voice.joined", channel=channel.name)
                )

            l.info(f"Bot joined voice: {channel.name} ({channel.id})")
            if persist and guild:
                try:
                    data_path = u.get_data_path("voice.yaml")
                    try:
                        persisted = await asyncio.to_thread(
                            functools.partial(_read_json, data_path, default={})
                        )
                    except Exception:
                        persisted = {}
                    persisted[str(guild.id)] = channel.id
                    await asyncio.to_thread(
                        functools.partial(_write_json, data_path, persisted)
                    )
                    l.info(
                        f"[voice] Persisted voice for guild {guild.id} -> channel {channel.id}"
                    )
                except Exception as e:
                    l.warning(f"[voice] Failed to persist voice: {e}")
            if self.audit:
                await self.audit.log(
                    action="joinvc",
                    user=user,
                    guild=source.guild,
                    channel=source.channel,
                    detail=f"Joined voice `{channel.name}` (`{channel.id}`)",
                )
        except discord.errors.ConnectionClosed as exc:
            if exc.code == 4017:
                await u.send_msg(
                    source,
                    self._tr(source, "voice.dave_failed"),
                    ephemeral=True,
                    delete_after=10,
                )
            else:
                raise
        except discord.ClientException as e:
            await u.send_msg(
                source,
                self._tr(source, "voice.connect_failed", error=e),
                ephemeral=True,
                delete_after=10,
            )
            l.error(f"Failed to join voice: {e}")
        except Exception as e:
            await u.send_msg(
                source,
                self._tr(source, "voice.error_generic", error=type(e).__name__),
                ephemeral=True,
                delete_after=10,
            )
            l.error(f"Unexpected error in joinvc: {type(e).__name__}: {e}")

    async def _handle_leavevc(self, source):
        if not await u.check_rate_limit(
            source,
            config=self.c,
            rate_limiter=self.rate_limiter,
            module="voicechannel",
            command="vc leave",
        ):
            return
        user = source.user if isinstance(source, discord.Interaction) else source.author

        guild = source.guild
        if not guild or not guild.voice_client:
            await u.send_msg(
                source,
                self._tr(source, "voice.not_in_voice"),
                ephemeral=True,
                delete_after=10,
            )
            return

        if not isinstance(guild.voice_client.channel, discord.VoiceChannel):
            await u.send_msg(
                source,
                self._tr(source, "voice.not_valid_voice"),
                ephemeral=True,
                delete_after=10,
            )
            return

        channel = guild.voice_client.channel
        self._intentional_disconnect.add(guild.id)
        self._reconnecting.discard(guild.id)
        self._last_vc.pop(guild.id, None)
        await guild.voice_client.disconnect(force=False)
        await u.send_msg(source, self._tr(source, "voice.left", channel=channel.name))

        l.info(f"Bot left voice: {channel.name} ({channel.id})")
        # Clean up persisted voice state if present
        try:
            data_path = u.get_data_path("voice.yaml")
            persisted = await asyncio.to_thread(
                functools.partial(_read_json, data_path, default={})
            )
            persisted.pop(str(guild.id), None)
            await asyncio.to_thread(
                functools.partial(_write_json, data_path, persisted)
            )
        except Exception as e:
            l.warning(f"[voice] Failed to clean persisted voice entry: {e}")
        if self.audit:
            await self.audit.log(
                action="leavevc",
                user=user,
                guild=source.guild,
                channel=source.channel,
                detail=f"Left voice `{channel.name}`",
            )

    async def _attempt_reconnect(
        self, guild: discord.Guild, channel_id: int, *, notify_admin: bool = False
    ):
        """Exponential-backoff reconnection loop for a single guild."""
        if guild.id in self._reconnecting:
            return
        self._reconnecting.add(guild.id)

        try:
            max_delay = self.c.voicechannel.reconnect_max_delay
            delay = 5
            while guild.id in self._reconnecting:
                try:
                    channel = guild.get_channel(channel_id)
                    if not channel:
                        try:
                            channel = await guild.fetch_channel(channel_id)
                        except Exception:
                            l.warning(
                                f"[voice] Channel {channel_id} not found in guild {guild.id}, stopping reconnect"
                            )
                            break

                    if not isinstance(channel, discord.VoiceChannel):
                        l.warning(
                            f"[voice] Channel {channel_id} in guild {guild.id} is not a voice channel, stopping reconnect"
                        )
                        break

                    me = guild.me
                    if me and not channel.permissions_for(me).connect:
                        l.warning(
                            f"[voice] No connect permission for {channel.name} in guild {guild.id}, retrying in {delay}s"
                        )
                        await asyncio.sleep(delay)
                        delay = min(delay * 2, max_delay)
                        continue

                    if (
                        guild.voice_client
                        and isinstance(guild.voice_client.channel, discord.VoiceChannel)
                        and guild.voice_client.channel.id == channel_id
                    ):
                        l.info(
                            f"[voice] Already reconnected to {channel.name} in guild {guild.id}"
                        )
                        break

                    await channel.connect(self_deaf=True, self_mute=True)
                    l.info(
                        f"[voice] Reconnected to {channel.name} ({channel_id}) in guild {guild.id}"
                    )
                    self._reconnecting.discard(guild.id)

                    try:
                        await channel.send(
                            self._t_for_guild(
                                guild, "voice.reconnected", channel=channel.name
                            )
                        )
                    except Exception as e:
                        l.debug(f"[voice] Failed to send reconnected notice: {e}")

                    if notify_admin:
                        try:
                            prefix = self.c.command_prefix
                            await channel.send(
                                self._t_for_guild(
                                    guild,
                                    "voice.admin_disconnected",
                                    prefix=prefix,
                                )
                            )
                        except Exception as e:
                            l.debug(
                                f"[voice] Failed to send admin disconnect notice: {e}"
                            )

                    if self.audit:
                        try:
                            assert self.bot.user is not None
                            await self.audit.log(
                                action="voice-reconnect",
                                user=self.bot.user,  # ty:ignore[invalid-argument-type]
                                guild=guild,
                                detail=f"Reconnected to voice `{channel.name}` (`{channel_id}`)",
                            )
                        except Exception as e:
                            l.debug(
                                f"[voice] Failed to log voice reconnect to audit: {e}"
                            )
                    return

                except discord.ClientException as e:
                    l.warning(
                        f"[voice] Reconnect attempt failed for guild {guild.id}: {e}, retrying in {delay}s"
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, max_delay)
                except discord.ConnectionClosed as e:
                    l.warning(
                        f"[voice] Connection closed during reconnect for guild {guild.id}: {e}, retrying in {delay}s"
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, max_delay)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    l.error(
                        f"[voice] Unexpected error during reconnect for guild {guild.id}: {type(e).__name__}: {e}"
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, max_delay)

            l.warning(f"[voice] Reconnect loop ended for guild {guild.id}")
        finally:
            self._reconnecting.discard(guild.id)
            self._last_vc.pop(guild.id, None)

    def _t_for_guild(self, guild: discord.Guild, key: str, **kwargs) -> str:
        lang = "zh"
        if self.lang_store:
            lang = self.lang_store.resolve(0, guild.id)
        return _t(key, lang, **kwargs)

    @staticmethod
    def _is_persisted(guild_id: int) -> bool:
        try:
            data_path = u.get_data_path("voice.yaml")
            with open(
                data_path, "r", encoding="utf-8"
            ) as f:  # startup read, event loop idle
                persisted = json.load(f)
            return str(guild_id) in persisted
        except Exception:
            return False

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if not self.bot.user or member.id != self.bot.user.id:
            return

        guild = member.guild
        vc = self.c.voicechannel

        if before.channel and not after.channel:
            if guild.id in self._intentional_disconnect:
                self._intentional_disconnect.discard(guild.id)
                return

            l.info(
                f"[voice] Bot disconnected from voice in guild {guild.id} (channel: {before.channel.name})"
            )

            if not vc.reconnect:
                return

            if guild.id in self._reconnecting:
                return

            self._last_vc[guild.id] = before.channel.id

            if vc.enabled:
                is_persisted = self._is_persisted(guild.id)
                # persist=True → always reconnect, notify admin to use /vc leave
                # persist=False → reconnect only for non-admin disconnects
                asyncio.create_task(
                    self._attempt_reconnect(
                        guild, before.channel.id, notify_admin=is_persisted
                    )
                )
            else:
                l.info("[voice] Voice module disabled, skipping reconnect")

        elif after.channel and not before.channel:
            self._last_vc[guild.id] = after.channel.id

    async def cog_unload(self):
        self._reconnecting.clear()
        self._last_vc.clear()
        self._intentional_disconnect.clear()


async def setup(bot: commands.Bot):
    if bot.config.voicechannel.enabled:  # ty:ignore[unresolved-attribute]
        await bot.add_cog(VoiceCog(bot))
        l.info("VoiceCog loaded.")
