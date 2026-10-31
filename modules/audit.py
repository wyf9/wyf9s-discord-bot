import re
from datetime import datetime, timezone

import discord
from discord.ext import commands
from loguru import logger as l

from config import ConfigModel
from i18n import t as _t
from lang_store import LangStore

TAG_PREFIX = "antispam-action/"


def _build_antispam_tag(user_id: int, base_action: str) -> str:
    return f"-# *({TAG_PREFIX}{user_id}/{base_action})*"


class AntispamActionView(discord.ui.View):
    def __init__(
        self,
        *,
        guild_id: int,
        target_id: int,
        target_name: str,
        action_label: str,
        lang: str,
        lang_store: LangStore,
        trigger_channel_id: int,
        base_action: str,
        category: str,
        rule_unban_link: bool = False,
    ):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.target_id = target_id
        self.target_name = target_name
        self.action_label = action_label
        self.lang = lang
        self.lang_store = lang_store
        self.trigger_channel_id = trigger_channel_id
        self.base_action = base_action
        self.category = category
        self.rule_unban_link = rule_unban_link

        if "ban" in action_label.lower():
            self._add_btn_unban()
        elif "mute" in action_label.lower():
            self._add_btn_unmute()

    def _add_btn_unban(self):
        btn = discord.ui.Button(
            label=_t("antispam.snapshot_button_unban", self.lang),
            style=discord.ButtonStyle.danger,
            custom_id=f"antispam:unban:{self.guild_id}:{self.target_id}:{self.trigger_channel_id}",
        )
        btn.callback = self._handle_unban  # ty:ignore[invalid-assignment]
        self.add_item(btn)

    def _add_btn_unmute(self):
        btn = discord.ui.Button(
            label=_t("antispam.snapshot_button_unmute", self.lang),
            style=discord.ButtonStyle.danger,
            custom_id=f"antispam:unmute:{self.guild_id}:{self.target_id}:{self.trigger_channel_id}",
        )
        btn.callback = self._handle_unmute  # ty:ignore[invalid-assignment]
        self.add_item(btn)

    async def _resolve_lang(self, interaction: discord.Interaction) -> str:
        return self.lang_store.resolve(
            interaction.user.id, interaction.guild.id if interaction.guild else None
        )

    async def _set_expired_button(self, interaction: discord.Interaction) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
                item.label = _t("antispam.snapshot_button_expired", self.lang)[:80]
        self.stop()
        try:
            await interaction.response.edit_message(view=self)
        except discord.HTTPException:
            pass

    async def _finalize_button(
        self, interaction: discord.Interaction, action_key: str
    ) -> str:
        actor = getattr(interaction.user, "display_name", str(interaction.user))
        action_label = _t(action_key, self.lang)
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
                item.label = _t(
                    "antispam.snapshot_button_done",
                    self.lang,
                    actor=actor,
                    action=action_label,
                )[:80]
        self.stop()
        try:
            await interaction.response.edit_message(view=self)
        except discord.HTTPException:
            pass
        return actor

    async def _handle_unban(self, interaction: discord.Interaction):
        lang = await self._resolve_lang(interaction)
        guild = interaction.client.get_guild(self.guild_id)
        if guild is None:
            await interaction.response.send_message(
                _t("antispam.guild_not_found", lang), ephemeral=True
            )
            return
        if not (
            isinstance(interaction.user, discord.Member)
            and interaction.user.guild_permissions.ban_members
        ):
            await interaction.response.send_message(
                _t("antispam.snapshot_button_no_permission", lang),
                ephemeral=True,
            )
            return

        try:
            ban_entry = await guild.fetch_ban(discord.Object(id=self.target_id))
        except discord.NotFound:
            ban_entry = None
        except discord.Forbidden:
            await interaction.response.send_message(
                _t("antispam.snapshot_button_no_permission", lang),
                ephemeral=True,
            )
            return

        if ban_entry is None:
            await self._set_expired_button(interaction)
            return

        try:
            user = await interaction.client.fetch_user(self.target_id)
            await guild.unban(
                user,
                reason=_t("antispam.unban_reason", lang, actor=str(interaction.user)),
            )
        except discord.NotFound:
            await self._set_expired_button(interaction)
            return
        except discord.Forbidden:
            await interaction.response.send_message(
                _t("antispam.snapshot_button_no_permission", lang),
                ephemeral=True,
            )
            return
        except Exception as e:
            await interaction.response.send_message(
                _t("antispam.snapshot_button_failed", lang, error=str(e)[:400]),
                ephemeral=True,
            )
            return

        actor = await self._finalize_button(interaction, "antispam.action_unban")

        audit: AuditLogger | None = getattr(interaction.client, "audit", None)
        if audit:
            await audit._update_antispam_action_logs(
                guild=guild,
                target_id=self.target_id,
                base_action=self.base_action,
                trigger_channel_id=self.trigger_channel_id,
                undo_type="ban",
                actor=actor,
                source_message=interaction.message,
                category=self.category,
                rule_unban_link=self.rule_unban_link,
            )

    async def _handle_unmute(self, interaction: discord.Interaction):
        lang = await self._resolve_lang(interaction)
        guild = interaction.client.get_guild(self.guild_id)
        if guild is None:
            await interaction.response.send_message(
                _t("antispam.guild_not_found", lang), ephemeral=True
            )
            return
        if not (
            isinstance(interaction.user, discord.Member)
            and interaction.user.guild_permissions.moderate_members
        ):
            await interaction.response.send_message(
                _t("antispam.snapshot_button_no_permission", lang),
                ephemeral=True,
            )
            return

        try:
            member = await guild.fetch_member(self.target_id)
        except discord.NotFound:
            member = None
        except discord.Forbidden:
            await interaction.response.send_message(
                _t("antispam.snapshot_button_no_permission", lang),
                ephemeral=True,
            )
            return

        if member is None or member.timed_out_until is None:
            await self._set_expired_button(interaction)
            return

        try:
            await member.timeout(
                None,
                reason=_t("antispam.unmute_reason", lang, actor=str(interaction.user)),
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                _t("antispam.snapshot_button_no_permission", lang),
                ephemeral=True,
            )
            return
        except Exception as e:
            await interaction.response.send_message(
                _t("antispam.snapshot_button_failed", lang, error=str(e)[:400]),
                ephemeral=True,
            )
            return

        actor = await self._finalize_button(interaction, "antispam.action_unmute")

        audit: AuditLogger | None = getattr(interaction.client, "audit", None)
        if audit:
            await audit._update_antispam_action_logs(
                guild=guild,
                target_id=self.target_id,
                base_action=self.base_action,
                trigger_channel_id=self.trigger_channel_id,
                undo_type="mute",
                actor=actor,
                source_message=interaction.message,
                category=self.category,
                rule_unban_link=self.rule_unban_link,
            )


class AuditLogger:
    c: ConfigModel
    client: commands.Bot
    lang_store: LangStore

    def __init__(
        self, config: ConfigModel, client: commands.Bot, lang_store: LangStore
    ):
        self.c = config
        self.client = client
        self.lang_store = lang_store

    def _resolve_targets(self, guild: discord.Guild | None) -> list[int]:
        targets: list[int] = []
        seen: set[int] = set()

        if self.c.audit.global_channel:
            targets.append(self.c.audit.global_channel)
            seen.add(self.c.audit.global_channel)

        if guild is not None:
            guild_conf = self.c.audit.guilds.get(
                guild.id, self.c.audit.guilds.get(str(guild.id))
            )
            if guild_conf is not None and guild_conf.channel not in seen:
                targets.append(guild_conf.channel)

        return targets

    def _resolve_lang(self, guild: discord.Guild | None) -> str:
        if guild is not None:
            return self.lang_store.resolve(0, guild.id)
        return "zh"

    @staticmethod
    def _get_guild_audit_channel_id(config: ConfigModel, guild_id: int) -> int | None:
        guild_conf = config.audit.guilds.get(
            guild_id, config.audit.guilds.get(str(guild_id))
        )
        if guild_conf is not None:
            return guild_conf.channel
        return None

    def _build_embed(
        self,
        *,
        lang: str,
        action: str,
        user: discord.User | discord.Member,
        guild: discord.Guild | None,
        channel: discord.abc.GuildChannel
        | discord.abc.PrivateChannel
        | discord.Thread
        | None,
        detail: str,
        success: bool,
        auto: bool,
    ) -> discord.Embed:
        color = discord.Color.green() if success else discord.Color.red()

        if auto:
            title_key = "audit.title_auto_ok" if success else "audit.title_auto_fail"
        else:
            title_key = (
                "audit.title_manual_ok" if success else "audit.title_manual_fail"
            )

        embed = discord.Embed(
            title=_t(title_key, lang),
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(
            name=_t("audit.field_action", lang),
            value=f"`{action}`",
            inline=True,
        )
        embed.add_field(
            name=_t("audit.field_actor", lang),
            value=f"{user.mention} (`{user.name}` / `{user.id}`)",
            inline=True,
        )
        if guild is not None:
            embed.add_field(
                name=_t("audit.field_guild", lang),
                value=f"`{guild.name}` (`{guild.id}`)",
                inline=False,
            )
        if channel is not None:
            channel_repr = getattr(channel, "mention", None) or getattr(
                channel, "name", str(channel)
            )
            embed.add_field(
                name=_t("audit.field_channel", lang),
                value=str(channel_repr),
                inline=False,
            )
        if detail:
            embed.add_field(
                name=_t("audit.field_detail", lang),
                value=detail[:1024],
                inline=False,
            )
        return embed

    async def _send_to_channel(
        self,
        channel_id: int,
        *,
        embed: discord.Embed | None = None,
        view: discord.ui.View | None = None,
        content: str | None = None,
    ):
        try:
            target = self.client.get_channel(channel_id)
            if target is None:
                target = await self.client.fetch_channel(channel_id)
            if not isinstance(target, (discord.TextChannel, discord.Thread)):
                l.warning(
                    f"[audit] Log channel {channel_id} is not a text channel, skipped"
                )
                return None
            kwargs: dict[str, discord.Embed | discord.ui.View | str] = {}
            if embed:
                kwargs["embed"] = embed
            if view:
                kwargs["view"] = view
            if content:
                kwargs["content"] = content
            return await target.send(**kwargs)  # ty:ignore[no-matching-overload]
        except discord.Forbidden:
            l.warning(f"[audit] No permission to send to log channel {channel_id}")
        except discord.NotFound:
            l.warning(f"[audit] Log channel {channel_id} not found")
        except Exception as e:
            l.warning(f"[audit] Error sending log to channel {channel_id}: {e}")
        return None

    async def log(
        self,
        *,
        action: str,
        user: discord.User | discord.Member,
        guild: discord.Guild | None = None,
        channel: discord.abc.GuildChannel
        | discord.abc.PrivateChannel
        | discord.Thread
        | None = None,
        detail: str = "",
        success: bool = True,
        auto: bool = False,
    ):
        if not self.c.audit.enabled:
            return

        targets = self._resolve_targets(guild)
        if not targets:
            return

        lang = self._resolve_lang(guild)
        embed = self._build_embed(
            lang=lang,
            action=action,
            user=user,
            guild=guild,
            channel=channel,
            detail=detail,
            success=success,
            auto=auto,
        )

        for channel_id in targets:
            await self._send_to_channel(channel_id, embed=embed)

    @staticmethod
    def _build_message_snapshot_embed(
        message: discord.Message,
        lang: str,
    ) -> discord.Embed:
        embed = discord.Embed(
            title=_t("antispam.snapshot_title", lang),
            color=discord.Color.blue(),
            timestamp=message.created_at,
        )

        content = message.content or ""
        if not content and message.embeds:
            content = _t("audit.snapshot_content_embed", lang)
        if not content and message.attachments:
            content = _t("audit.snapshot_content_attachment", lang)
        if not content:
            content = _t("antispam.snapshot_content_empty", lang)

        embed.add_field(
            name=_t("audit.snapshot_field_content", lang),
            value=content[:1024] if len(content) <= 1024 else content[:1021] + "...",
            inline=False,
        )

        embed.add_field(
            name=_t("audit.snapshot_field_author", lang),
            value=f"{message.author} (`{message.author.id}`)",
            inline=True,
        )
        embed.add_field(
            name=_t("antispam.snapshot_field_channel", lang),
            value=f"{message.channel} (`{message.channel.id}`)",
            inline=True,
        )

        attachment_urls = [a.url for a in message.attachments]
        sticker_urls = [s.url for s in message.stickers if hasattr(s, "url") and s.url]
        all_urls = attachment_urls + sticker_urls
        if all_urls:
            embed.add_field(
                name=_t("antispam.snapshot_field_attachments", lang),
                value="\n".join(all_urls)[:1024],
                inline=False,
            )
        else:
            embed.add_field(
                name=_t("antispam.snapshot_field_attachments", lang),
                value=_t("antispam.snapshot_field_no_attachments", lang),
                inline=False,
            )

        if message.jump_url:
            embed.add_field(
                name=_t("audit.snapshot_field_jump", lang),
                value=message.jump_url,
                inline=False,
            )

        if message.author.avatar:
            embed.set_thumbnail(url=message.author.avatar.url)

        embed.set_footer(text=_t("audit.snapshot_footer", lang, id=message.id))
        return embed

    async def forward_antispam_trigger(
        self,
        *,
        guild: discord.Guild,
        trigger_message: discord.Message,
    ) -> dict[int, discord.Message]:
        if not self.c.audit.enabled:
            return {}

        targets = self._resolve_targets(guild)
        if not targets:
            return {}

        lang = self._resolve_lang(guild)
        pending: dict[int, discord.Message] = {}

        for channel_id in targets:
            target = self.client.get_channel(channel_id)
            if target is None:
                try:
                    target = await self.client.fetch_channel(channel_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    continue
            if not isinstance(target, (discord.TextChannel, discord.Thread)):
                l.warning(
                    f"[audit] Log channel {channel_id} is not a text channel, skipped"
                )
                continue
            try:
                forwarded = await trigger_message.forward(target)
                pending[channel_id] = await forwarded.reply(
                    _t("audit.processing", lang)
                )
            except discord.HTTPException as e:
                l.warning(
                    f"[audit] Failed to forward trigger message to {channel_id}: {e}"
                )

        return pending

    async def log_antispam_with_snapshot(
        self,
        *,
        user: discord.User | discord.Member,
        guild: discord.Guild,
        channel: discord.TextChannel,
        detail: str,
        success: bool,
        trigger_message: discord.Message,
        category: str,
        action_label: str,
        base_action: str,
        pending: dict[int, discord.Message] | None = None,
    ):
        if not self.c.audit.enabled:
            return

        targets = self._resolve_targets(guild)
        if not targets:
            return

        lang = self._resolve_lang(guild)

        embed = self._build_embed(
            lang=lang,
            action="antispam-auto-catch",
            user=user,
            guild=guild,
            channel=channel,
            detail=detail,
            success=success,
            auto=True,
        )

        tag = _build_antispam_tag(user.id, base_action)

        rule = self.c.antispam.spam_catcher.get(
            channel.id, self.c.antispam.spam_catcher.get(str(channel.id))
        )
        rule_unban_link: bool = getattr(rule, "unban_link", False) if rule else False

        pending = pending or {}

        for channel_id in targets:
            view = AntispamActionView(
                guild_id=guild.id,
                target_id=user.id,
                target_name=str(user),
                action_label=action_label,
                lang=lang,
                lang_store=self.lang_store,
                trigger_channel_id=channel.id,
                base_action=base_action,
                category=category,
                rule_unban_link=rule_unban_link,
            )
            placeholder = pending.get(channel_id)
            if placeholder is not None:
                try:
                    await placeholder.edit(content=tag, embed=embed, view=view)
                    continue
                except discord.HTTPException as e:
                    l.warning(
                        f"[audit] Failed to edit placeholder in {channel_id}: {e}"
                    )
            snapshot_embed = self._build_message_snapshot_embed(trigger_message, lang)
            await self._send_to_channel(channel_id, embed=snapshot_embed)
            await self._send_to_channel(channel_id, content=tag, embed=embed, view=view)

    @staticmethod
    def _build_disabled_undo_view(
        action_key: str, actor: str, lang: str
    ) -> discord.ui.View:
        action_label = _t(action_key, lang)
        view = discord.ui.View()
        btn = discord.ui.Button(
            label=_t(
                "antispam.snapshot_button_done",
                lang,
                actor=actor,
                action=action_label,
            )[:80],
            style=discord.ButtonStyle.secondary,
            disabled=True,
        )
        view.add_item(btn)
        return view

    async def _update_antispam_action_logs(
        self,
        *,
        guild: discord.Guild,
        target_id: int,
        base_action: str,
        trigger_channel_id: int,
        undo_type: str,
        actor: str,
        source_message: discord.Message | None,
        category: str,
        rule_unban_link: bool,
    ) -> None:
        """Search and update all audit log messages and the public log for an undo action."""
        if not self.c.audit.enabled:
            return

        tag = _build_antispam_tag(target_id, base_action)
        action_key = f"antispam.action_un{undo_type}"
        lang = self._resolve_lang(guild)
        disabled_view = self._build_disabled_undo_view(action_key, actor, lang)

        targets = self._resolve_targets(guild)

        for channel_id in targets:
            channel = self.client.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await self.client.fetch_channel(channel_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    continue
            if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                continue
            try:
                async for msg in channel.history(limit=100):
                    if msg.author != self.client.user:
                        continue
                    if msg == source_message:
                        continue
                    if tag in (msg.content or ""):
                        try:
                            await msg.edit(content=None, view=disabled_view)
                        except discord.HTTPException:
                            pass
            except discord.Forbidden:
                l.warning(
                    f"[audit] No permission to search channel {channel_id} for tag"
                )
            except discord.HTTPException as e:
                l.warning(f"[audit] Error searching channel {channel_id}: {e}")

        guild_audit_channel_id = self._get_guild_audit_channel_id(self.c, guild.id)
        audit_link: str | None = None
        if rule_unban_link and guild_audit_channel_id is not None:
            if source_message is not None and (
                source_message.channel.id == guild_audit_channel_id
            ):
                audit_link = source_message.jump_url
            else:
                channel = self.client.get_channel(guild_audit_channel_id)
                if channel is None:
                    try:
                        channel = await self.client.fetch_channel(
                            guild_audit_channel_id
                        )
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        channel = None
                if isinstance(channel, (discord.TextChannel, discord.Thread)):
                    try:
                        async for msg in channel.history(limit=100):
                            if msg.author == self.client.user and tag in (
                                msg.content or ""
                            ):
                                audit_link = msg.jump_url
                                break
                    except (discord.Forbidden, discord.HTTPException):
                        pass

        trigger_channel = self.client.get_channel(trigger_channel_id)
        if trigger_channel is None:
            try:
                trigger_channel = await self.client.fetch_channel(trigger_channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                trigger_channel = None
        if isinstance(trigger_channel, (discord.TextChannel, discord.Thread)):
            undo_text_key = f"antispam.public_undo_{undo_type}"
            undo_text = _t(undo_text_key, lang)
            try:
                async for msg in trigger_channel.history(limit=100):
                    if msg.author != self.client.user:
                        continue
                    if tag in (msg.content or ""):
                        new_content = self._rebuild_public_notice_undone(
                            msg.content, undo_type, undo_text, audit_link, lang
                        )
                        if new_content is not None:
                            try:
                                await msg.edit(content=new_content)
                            except discord.HTTPException:
                                pass
            except (discord.Forbidden, discord.HTTPException):
                pass

    @staticmethod
    def _rebuild_public_notice_undone(
        original: str,
        undo_type: str,
        undo_text: str,
        audit_link: str | None,
        lang: str,
    ) -> str | None:
        """Rebuild a public notice message to show the undo action.

        Example output:
            🚨 Antispam triggered: @user (`name`) -> ~~Spammer/ban~~ -> **[Unban by moderator](link)**
            -# *(antispam-action/xxx/ban)*
        """
        lines = original.split("\n")
        tag_line = ""
        main_parts: list[str] = []

        for i, line in enumerate(lines):
            if line.startswith("-# *(" + TAG_PREFIX):
                tag_line = line
            else:
                main_parts.append(line)

        main = "\n".join(main_parts)

        if audit_link:
            undo_md = f"**[{undo_text}]({audit_link})**"
        else:
            undo_md = f"**{undo_text}**"

        triggered_match = re.search(r"^(.*?-> )\*\*(.+?)/(.+?)\*\*(.*?)$", main)
        if triggered_match:
            prefix = triggered_match.group(1)
            cat = triggered_match.group(2)
            act = triggered_match.group(3)
            suffix = triggered_match.group(4)
            new_main = f"{prefix}~~**{cat}/{act}**~~{suffix} -> {undo_md}"
        else:
            new_main = f"{main} -> {undo_md}"

        if tag_line:
            return f"{new_main}\n{tag_line}"
        return new_main
