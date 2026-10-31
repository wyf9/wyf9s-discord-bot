import typing as t
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands
from loguru import logger as l

from config import _SpamCatcherRuleConfigModel
from i18n import t as _t
from modules.audit import AuditLogger, _build_antispam_tag
from modules.clear_message import CLEAR_MESSAGE_MARKER, ClearMessageService


class AntiSpamCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.c = bot.config  # ty:ignore[unresolved-attribute]
        self.audit: AuditLogger | None = getattr(bot, "audit", None)
        self.lang_store = getattr(bot, "lang_store", None)
        self.clear_message = ClearMessageService(
            config=self.c, client=bot, audit=self.audit
        )

    def _guild_lang(self, guild: discord.Guild | None) -> str:
        if self.lang_store and guild:
            return self.lang_store.resolve(0, guild.id)
        return "zh"

    @commands.Cog.listener("on_message")
    async def antispam_auto_handler(self, message: discord.Message):
        await self._handle_auto_message(message)

    def _resolve_rule(self, channel_id: int) -> _SpamCatcherRuleConfigModel | None:
        return self.c.antispam.spam_catcher.get(
            channel_id, self.c.antispam.spam_catcher.get(str(channel_id))
        )

    @staticmethod
    def _parse_role_ids(
        values: list[int | str], guild: discord.Guild | None = None
    ) -> set[int]:
        role_ids: set[int] = set()
        name_to_ids: dict[str, set[int]] | None = None
        for value in values:
            if isinstance(value, int):
                role_ids.add(value)
            elif isinstance(value, str) and value.isdigit():
                role_ids.add(int(value))
            elif isinstance(value, str) and guild is not None:
                if name_to_ids is None:
                    name_to_ids = {}
                    for role in guild.roles:
                        name_to_ids.setdefault(role.name, set()).add(role.id)
                role_ids.update(name_to_ids.get(value, set()))
        return role_ids

    def _is_ignored(
        self, member: discord.Member, rule: _SpamCatcherRuleConfigModel
    ) -> bool:
        ignored_role_ids = self._parse_role_ids(rule.ignored_roles, member.guild)
        if not ignored_role_ids:
            return False
        member_role_ids = {role.id for role in member.roles}
        return bool(member_role_ids & ignored_role_ids)

    def _is_spammer(
        self, member: discord.Member, rule: _SpamCatcherRuleConfigModel
    ) -> bool:
        role_ids = {role.id for role in member.roles if not role.is_default()}
        if not role_ids:
            return True
        stranger_role_ids = self._parse_role_ids(rule.stranger_roles, member.guild)
        return bool(stranger_role_ids) and role_ids.issubset(stranger_role_ids)

    async def _cleanup_messages(
        self,
        actor: discord.User,
        guild: discord.Guild,
        channel: discord.TextChannel,
        target: discord.Member,
        within_minutes: int | None,
    ) -> str | None:
        if within_minutes is None or within_minutes <= 0:
            return None
        result = await self.clear_message.do_clear_message(
            author=actor,
            guild=guild,
            channel=channel,
            user=t.cast(discord.User, target),
            within_minutes=within_minutes,
            scope="server",
            delete_threads=True,
            write_audit=False,
            lang=self._guild_lang(guild),
        )
        return result.replace(f"\n-# {CLEAR_MESSAGE_MARKER}", "").replace(
            CLEAR_MESSAGE_MARKER, ""
        )

    def _build_public_notice(
        self,
        member: discord.Member,
        category: str,
        action_label: str,
        should_ping: bool,
        base_action: str,
    ) -> str:
        lang = self._guild_lang(member.guild)
        mention = member.mention
        if should_ping:
            notice = _t("antispam.public_notice_hacked", lang, mention=mention)
        else:
            if action_label in ("kick", "ban"):
                mention = f"{mention} (`{member.name}`)"
            category_label = _t(f"antispam.category_{category}", lang)
            notice = _t(
                "antispam.public_notice_triggered",
                lang,
                mention=mention,
                category=category_label,
                action=action_label,
            )
        tag = _build_antispam_tag(member.id, base_action)
        return f"{notice}\n{tag}"

    @staticmethod
    def _action_permission(action: str | int) -> tuple[str, str]:
        if action == "kick":
            return "kick", "kick_members"
        if action == "ban":
            return "ban", "ban_members"
        return "mute", "moderate_members"

    async def _execute_action(
        self,
        guild: discord.Guild,
        target: discord.Member,
        category: str,
        action: str | int,
    ) -> tuple[str, bool, str]:
        should_ping = False
        if action == "kick":
            await target.kick(reason=f"antispam/{category}")
            return "kick", should_ping, "kick"
        if action == "ban":
            await guild.ban(discord.Object(id=target.id), reason=f"antispam/{category}")
            return "ban", should_ping, "ban"
        mute_minutes = 60
        if isinstance(action, int):
            mute_minutes = max(1, action)
        until = datetime.now(timezone.utc) + timedelta(minutes=mute_minutes)
        await target.timeout(until, reason=f"antispam/{category}")
        should_ping = True
        return f"mute {mute_minutes}m", should_ping, "mute"

    async def _audit_failure(
        self,
        *,
        actor: discord.User,
        guild: discord.Guild,
        channel: discord.TextChannel,
        target: discord.Member,
        category: str,
        action_type: str,
        reason: str,
        error: str,
    ) -> None:
        if not self.audit:
            return
        await self.audit.log(
            action="antispam-auto-catch",
            user=target,
            guild=guild,
            channel=channel,
            detail=(
                f"Target: {target} ({target.id})"
                f"\nCategory: {category}"
                f"\nAction: {action_type}"
                f"\nReason: {reason}"
                f"\nError: {error[:400]}"
            ),
            success=False,
            auto=True,
        )

    async def _process_target(
        self,
        *,
        actor: discord.User,
        guild: discord.Guild,
        trigger_channel: discord.TextChannel,
        target: discord.Member,
        rule: _SpamCatcherRuleConfigModel,
        trigger_message: discord.Message,
    ) -> tuple[bool, str, str, bool, str]:
        is_spammer = self._is_spammer(target, rule)
        category = "spammer" if is_spammer else "hacked"
        action: str | int = rule.spammer if is_spammer else rule.hacked

        try:
            action_label, should_ping, base_action = await self._execute_action(
                guild=guild, target=target, category=category, action=action
            )
        except discord.Forbidden as e:
            action_type, perm_name = self._action_permission(action)
            me = guild.me
            has_perm = False
            if me is not None:
                has_perm = bool(getattr(me.guild_permissions, perm_name, False))
            if me is not None and has_perm:
                reason = (
                    f"Bot has {perm_name} but target's top role "
                    f"({target.top_role.name}) is higher or equal to bot's "
                    f"({me.top_role.name}), move bot role above target"
                )
            else:
                reason = f"Bot lacks {perm_name} permission"
            l.warning(
                f"[antispam] Cannot {action_type} {target} ({target.id}): {reason} | {e}"
            )
            await self._audit_failure(
                actor=actor,
                guild=guild,
                channel=trigger_channel,
                target=target,
                category=category,
                action_type=action_type,
                reason=f"Permission ({perm_name}): {reason}",
                error=str(e),
            )
            return False, category, "failed", False, action_type
        except discord.HTTPException as e:
            action_type, _ = self._action_permission(action)
            l.warning(f"[antispam] HTTP error {action_type} on {target}: {e}")
            await self._audit_failure(
                actor=actor,
                guild=guild,
                channel=trigger_channel,
                target=target,
                category=category,
                action_type=action_type,
                reason="HTTP error during action",
                error=str(e),
            )
            return False, category, "failed", False, action_type

        pending: dict[int, discord.Message] = {}
        if self.audit:
            pending = await self.audit.forward_antispam_trigger(
                guild=guild, trigger_message=trigger_message
            )

        clear_result = await self._cleanup_messages(
            actor=actor,
            guild=guild,
            channel=trigger_channel,
            target=target,
            within_minutes=rule.clear_message,
        )

        if self.audit:
            detail_lines = [
                f"Category: {category}",
                f"Action: {action_label}",
                f"Cleanup mins: {rule.clear_message}",
            ]
            if clear_result:
                quoted = "> " + clear_result[:900].replace("\n", "\n> ")
                detail_lines.append(f"Cleanup:\n{quoted}")
            await self.audit.log_antispam_with_snapshot(
                user=target,
                guild=guild,
                channel=trigger_channel,
                detail="\n".join(detail_lines),
                success=True,
                trigger_message=trigger_message,
                category=category,
                action_label=action_label,
                base_action=base_action,
                pending=pending,
            )

        return True, category, action_label, should_ping, base_action

    async def _handle_auto_message(self, message: discord.Message):
        try:
            await self._handle_auto_message_inner(message)
        except Exception as e:
            l.exception(f"[antispam] Error handling message: {e}")

    async def _handle_auto_message_inner(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild is None:
            return

        rule = self._resolve_rule(message.channel.id)
        if rule is None:
            return

        l.debug(
            f"[antispam] Rule hit: channel={message.channel.id} "
            f"author={message.author} ({message.author.id})"
        )

        if not isinstance(
            message.channel,
            (discord.TextChannel, discord.Thread, discord.VoiceChannel),
        ):
            l.warning(
                f"[antispam] Unsupported channel type: channel={message.channel.id}"
            )
            return
        if not isinstance(message.author, discord.Member):
            l.warning(f"[antispam] Author is not Member: {message.author}")
            return

        if self._is_ignored(message.author, rule):
            l.debug(f"[antispam] Member has ignored role, skipping: {message.author}")
            return

        actor = self.bot.user
        if not isinstance(actor, discord.ClientUser):
            l.warning("[antispam] client.user unavailable")
            return

        (
            ok,
            category,
            action_label,
            should_ping,
            _base_action,
        ) = await self._process_target(
            actor=t.cast(discord.User, actor),
            guild=message.guild,
            trigger_channel=t.cast(discord.TextChannel, message.channel),
            target=message.author,
            rule=rule,
            trigger_message=message,
        )
        if not ok:
            l.warning(f"[antispam] Failed: target={message.author} category={category}")
            return

        l.info(f"[antispam] Handled: {message.author} -> {category}/{action_label}")

        if rule.public_log:
            notice = self._build_public_notice(
                member=message.author,
                category=category,
                action_label=action_label,
                should_ping=should_ping,
                base_action=_base_action,
            )
            await message.channel.send(notice)


async def setup(bot: commands.Bot):
    if bot.config.antispam.enabled:  # ty:ignore[unresolved-attribute]
        await bot.add_cog(AntiSpamCog(bot))
        l.info("AntiSpamCog loaded.")
