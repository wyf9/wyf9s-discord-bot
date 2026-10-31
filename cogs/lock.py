import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks
from loguru import logger as l
from pydantic import BaseModel
from yaml import safe_dump, safe_load

import utils as u
from i18n import lang_of, ls
from i18n import t as _t
from modules.audit import AuditLogger

# ========== Data Models ==========


class ScheduledLock(BaseModel):
    channel_id: int
    lock_day: str | None = None
    lock_time: str | None = None
    unlock_day: str | None = None
    unlock_time: str | None = None
    cycle: str | None = None
    cycle_start: str | None = None
    cycle_end: str | None = None
    created_by: int
    created_at: datetime = datetime.now(timezone.utc)

    @property
    def label(self) -> str:
        ch = f"<#{self.channel_id}>"
        parts = [ch]
        if self.lock_day or self.lock_time:
            parts.append(f"Lock: {(self.lock_day or '?')} {(self.lock_time or '?')}")
        if self.unlock_day or self.unlock_time:
            parts.append(
                f"Unlock: {(self.unlock_day or '?')} {(self.unlock_time or '?')}"
            )
        if self.cycle:
            parts.append(f"Cycle: {self.cycle}")
        return " | ".join(parts)


class ScheduleStore:
    def __init__(self, path: str = "schedules.yaml"):
        self._name = path
        self._path = u.get_data_path(path)
        self.schedules: list[ScheduledLock] = []
        self._load()

    def _load(self):
        read_path = u.get_data_path(self._name, for_read=True)
        if Path(read_path).exists():
            try:
                with open(read_path, "r", encoding="utf-8") as f:
                    data = safe_load(f) or []
                self.schedules = [ScheduledLock.model_validate(item) for item in data]
            except Exception as e:
                l.warning(f"[lock] Failed to load schedules: {e}")
                self.schedules = []

    def _save(self):
        data = [s.model_dump(mode="json") for s in self.schedules]
        with open(self._path, "w", encoding="utf-8") as f:
            safe_dump(data, f, allow_unicode=True, default_flow_style=False)

    def add(self, schedule: ScheduledLock):
        self.schedules.append(schedule)
        self._save()

    def remove_by_channel(self, channel_id: int):
        self.schedules = [s for s in self.schedules if s.channel_id != channel_id]
        self._save()

    def remove_by_index(self, index: int):
        if 0 <= index < len(self.schedules):
            self.schedules.pop(index)
            self._save()


# ========== Date/Time Parsing ==========

_WEEKDAY_MAP = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


def _parse_day(value: str, ref_year: int | None = None) -> tuple[int, int, int]:
    value = value.strip()
    now = datetime.now(tz=timezone.utc)
    year = ref_year or now.year
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", value)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})", value)
    if m:
        return year, int(m.group(1)), int(m.group(2))
    m = re.fullmatch(r"(\d{1,2})", value)
    if m:
        return year, now.month, int(m.group(1))
    raise ValueError(f"Invalid date format: {value}")


def _parse_time(value: str) -> tuple[int, int]:
    value = value.strip()
    m = re.fullmatch(r"(\d{1,2})[-:](\d{2})", value)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return h, mi
    raise ValueError(f"Invalid time format: {value}")


def _parse_day_time(
    day_str: str | None, time_str: str | None, tz: timezone | None = None
) -> datetime | None:
    if not day_str and not time_str:
        return None
    if not time_str:
        time_str = "00-00"
    if not day_str:
        now = datetime.now(tz=timezone.utc)
        day_str = f"{now.year}-{now.month}-{now.day}"
    y, mo, d = _parse_day(day_str)
    h, mi = _parse_time(time_str)
    local_dt = datetime(y, mo, d, h, mi, tzinfo=tz or timezone(timedelta(hours=8)))
    return local_dt.astimezone(timezone.utc)


def _cycle_matches_today(cycle: str, now: datetime) -> bool:
    cycle = cycle.strip().lower()
    if cycle == "daily":
        return True
    parts = [p.strip() for p in cycle.split(",")]
    if all(p in _WEEKDAY_MAP for p in parts):
        return now.weekday() in [_WEEKDAY_MAP[p] for p in parts]
    days: set[int] = set()
    for part in parts:
        if "-" in part:
            a, b = part.split("-", 1)
            days.update(range(int(a), int(b) + 1))
        else:
            days.add(int(part))
    return now.day in days


# ========== Cog ==========


class LockCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.c = bot.config  # ty:ignore[unresolved-attribute]
        self.audit: AuditLogger | None = getattr(bot, "audit", None)
        self.store = getattr(bot, "schedule_store", ScheduleStore())
        bot.schedule_store = self.store  # ty:ignore[unresolved-attribute]
        self.lang_store = getattr(bot, "lang_store", None)

    def _tr(self, source, key: str, **kwargs) -> str:
        return _t(key, lang_of(source, self.lang_store), **kwargs)

    def _tr_guild(self, guild: discord.Guild | None, key: str, **kwargs) -> str:
        lang = (
            self.lang_store.resolve(0, guild.id) if self.lang_store and guild else "zh"
        )
        return _t(key, lang, **kwargs)

    def cog_load(self):
        if not self._check_schedules.is_running():
            self._check_schedules.start()
            l.info("[lock] Schedule checker started.")

    def cog_unload(self):
        if self._check_schedules.is_running():
            self._check_schedules.cancel()
            l.info("[lock] Schedule checker stopped.")

    # ========== Slash Commands ==========

    lock_group = app_commands.Group(name="lock", description=ls("lock.cmd_group_desc"))

    @lock_group.command(name="now", description=ls("lock.cmd_now_desc"))
    @app_commands.describe(channel=ls("lock.param_channel_lock"))
    @u.requires(u.Permission.MOD, perm_module="lock")
    async def slash_lock(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
        | discord.VoiceChannel
        | discord.StageChannel
        | None = None,
    ):
        await self._handle_lock(interaction, channel)

    @lock_group.command(name="unlock", description=ls("lock.cmd_unlock_desc"))
    @app_commands.describe(channel=ls("lock.param_channel_unlock"))
    @u.requires(u.Permission.MOD, perm_module="lock")
    async def slash_unlock(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
        | discord.VoiceChannel
        | discord.StageChannel
        | None = None,
    ):
        await self._handle_unlock(interaction, channel)

    @lock_group.command(name="plan", description=ls("lock.cmd_plan_desc"))
    @app_commands.describe(
        channel=ls("lock.param_plan_channel"),
        lock_day=ls("lock.param_plan_lock_day"),
        lock_time=ls("lock.param_plan_lock_time"),
        unlock_day=ls("lock.param_plan_unlock_day"),
        unlock_time=ls("lock.param_plan_unlock_time"),
        cycle=ls("lock.param_plan_cycle"),
        cycle_start=ls("lock.param_plan_cycle_start"),
        cycle_end=ls("lock.param_plan_cycle_end"),
    )
    @u.requires(u.Permission.MOD, perm_module="lock")
    async def slash_plan_lock(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
        | discord.VoiceChannel
        | discord.StageChannel
        | None = None,
        lock_day: str | None = None,
        lock_time: str | None = None,
        unlock_day: str | None = None,
        unlock_time: str | None = None,
        cycle: str | None = None,
        cycle_start: str | None = None,
        cycle_end: str | None = None,
    ):
        await self._handle_plan_lock(
            interaction,
            channel,
            lock_day,
            lock_time,
            unlock_day,
            unlock_time,
            cycle,
            cycle_start,
            cycle_end,
        )

    async def unplan_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[int]]:
        choices = []
        for i, s in enumerate(self.store.schedules):
            label = s.label
            if current.lower() in label.lower():
                choices.append(app_commands.Choice(name=label[:100], value=i))
        return choices[:25]

    @lock_group.command(name="unplan", description=ls("lock.cmd_unplan_desc"))
    @app_commands.describe(index=ls("lock.param_unplan_index"))
    @app_commands.autocomplete(index=unplan_autocomplete)
    @u.requires(u.Permission.MOD, perm_module="lock")
    async def slash_unplan_lock(self, interaction: discord.Interaction, index: int):
        await self._handle_unplan_lock(interaction, index)

    # ========== Prefix Commands ==========

    @commands.group(name="lock", invoke_without_command=True)
    async def prefix_lock_group(self, ctx: commands.Context):
        await ctx.send(self._tr(ctx, "lock.usage_prefix"))

    @prefix_lock_group.command(name="now")
    @u.requires(u.Permission.MOD, perm_module="lock")
    async def prefix_lock(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel
        | discord.VoiceChannel
        | discord.StageChannel
        | None = None,
    ):
        await self._handle_lock(ctx, channel)

    @prefix_lock_group.command(name="unlock")
    @u.requires(u.Permission.MOD, perm_module="lock")
    async def prefix_unlock(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel
        | discord.VoiceChannel
        | discord.StageChannel
        | None = None,
    ):
        await self._handle_unlock(ctx, channel)

    @prefix_lock_group.command(name="plan")
    @u.requires(u.Permission.MOD, perm_module="lock")
    async def prefix_plan_lock(self, ctx: commands.Context):
        flags = u.parse_flags(ctx.message.content)
        channel = None
        if "channel" in flags:
            ch_str = flags["channel"]
            m = re.match(r"<#(\d+)>", ch_str)
            if m:
                channel = self.bot.get_channel(int(m.group(1)))
            elif ch_str.isdigit():
                channel = self.bot.get_channel(int(ch_str))
        await self._handle_plan_lock(
            ctx,
            channel,
            lock_day=flags.get("lock-day") or flags.get("lock_day"),
            lock_time=flags.get("lock-time") or flags.get("lock_time"),
            unlock_day=flags.get("unlock-day") or flags.get("unlock_day"),
            unlock_time=flags.get("unlock-time") or flags.get("unlock_time"),
            cycle=flags.get("cycle"),
            cycle_start=flags.get("cycle-start") or flags.get("cycle_start"),
            cycle_end=flags.get("cycle-end") or flags.get("cycle_end"),
        )

    @prefix_lock_group.command(name="unplan")
    @u.requires(u.Permission.MOD, perm_module="lock")
    async def prefix_unplan_lock(self, ctx: commands.Context, index: int = -1):
        await self._handle_unplan_lock(ctx, index)

    # ========== Shared Logic ==========

    async def _handle_lock(self, source, channel=None):
        user = source.user if isinstance(source, discord.Interaction) else source.author
        target = channel or source.channel
        if not isinstance(
            target, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)
        ):
            await u.send_msg(
                source,
                self._tr(source, "lock.type_not_supported_lock"),
                ephemeral=True,
                delete_after=10,
            )
            return
        try:
            is_voice = isinstance(target, (discord.VoiceChannel, discord.StageChannel))
            everyone = target.guild.default_role
            if is_voice:
                await u.send_msg(source, self._tr(source, "lock.locked_voice"))
            else:
                await u.send_msg(source, self._tr(source, "lock.locked"))
            overwrites = target.overwrites_for(everyone)
            overwrites.send_messages = False
            overwrites.send_messages_in_threads = False
            if is_voice:
                overwrites.connect = False
            await target.set_permissions(
                everyone, overwrite=overwrites, reason=f"Lock by {user}"
            )
            if self.audit:
                await self.audit.log(
                    action="lock",
                    user=user,
                    guild=source.guild,
                    channel=target,
                    detail=f"Locked channel `{target.name}`",
                )
            self.store.remove_by_channel(target.id)
        except discord.Forbidden:
            await u.send_msg(
                source,
                self._tr(source, "common.permission_denied"),
                ephemeral=True,
                delete_after=10,
            )
        except Exception as e:
            await u.send_msg(
                source,
                self._tr(source, "lock.lock_failed", error=e),
                ephemeral=True,
                delete_after=10,
            )

    async def _handle_unlock(self, source, channel=None):
        user = source.user if isinstance(source, discord.Interaction) else source.author
        target = channel or source.channel
        if not isinstance(
            target, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)
        ):
            await u.send_msg(
                source,
                self._tr(source, "lock.type_not_supported"),
                ephemeral=True,
                delete_after=10,
            )
            return
        try:
            is_voice = isinstance(target, (discord.VoiceChannel, discord.StageChannel))
            everyone = target.guild.default_role
            overwrites = target.overwrites_for(everyone)
            overwrites.send_messages = None
            overwrites.send_messages_in_threads = None
            if is_voice:
                overwrites.connect = None
            await target.set_permissions(
                everyone, overwrite=overwrites, reason=f"Unlock by {user}"
            )
            if is_voice:
                await u.send_msg(source, self._tr(source, "lock.unlocked_voice"))
            else:
                await u.send_msg(source, self._tr(source, "lock.unlocked"))
            if self.audit:
                await self.audit.log(
                    action="unlock",
                    user=user,
                    guild=source.guild,
                    channel=target,
                    detail=f"Unlocked channel `{target.name}`",
                )
            self.store.remove_by_channel(target.id)
        except discord.Forbidden:
            await u.send_msg(
                source,
                self._tr(source, "common.permission_denied"),
                ephemeral=True,
                delete_after=10,
            )
        except Exception as e:
            await u.send_msg(
                source,
                self._tr(source, "lock.unlock_failed", error=e),
                ephemeral=True,
                delete_after=10,
            )

    async def _handle_plan_lock(
        self,
        source,
        channel,
        lock_day,
        lock_time,
        unlock_day,
        unlock_time,
        cycle,
        cycle_start,
        cycle_end,
    ):
        user = source.user if isinstance(source, discord.Interaction) else source.author
        target = channel or source.channel
        if not isinstance(
            target, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)
        ):
            await u.send_msg(
                source,
                self._tr(source, "lock.type_not_supported"),
                ephemeral=True,
                delete_after=10,
            )
            return
        if not lock_day and not lock_time and not unlock_day and not unlock_time:
            await u.send_msg(
                source,
                self._tr(source, "lock.plan_need_time"),
                ephemeral=True,
                delete_after=10,
            )
            return
        if cycle:
            cycle = cycle.strip().lower()
            if cycle != "daily":
                pts = [p.strip() for p in cycle.split(",")]
                is_wd = all(p in _WEEKDAY_MAP for p in pts)
                is_dom = all(re.fullmatch(r"\d+(-\d+)?", p) for p in pts)
                if not is_wd and not is_dom:
                    await u.send_msg(
                        source,
                        self._tr(source, "lock.plan_invalid_cycle"),
                        ephemeral=True,
                        delete_after=10,
                    )
                    return
        self.store.remove_by_channel(target.id)
        schedule = ScheduledLock(
            channel_id=target.id,
            lock_day=lock_day,
            lock_time=lock_time,
            unlock_day=unlock_day,
            unlock_time=unlock_time,
            cycle=cycle,
            cycle_start=cycle_start,
            cycle_end=cycle_end,
            created_by=user.id,
        )
        self.store.add(schedule)
        parts = []
        if lock_day or lock_time:
            parts.append(
                self._tr(
                    source,
                    "lock.plan_part_lock",
                    day=lock_day or "?",
                    time=lock_time or "?",
                )
            )
        if unlock_day or unlock_time:
            parts.append(
                self._tr(
                    source,
                    "lock.plan_part_unlock",
                    day=unlock_day or "?",
                    time=unlock_time or "?",
                )
            )
        if cycle:
            parts.append(self._tr(source, "lock.plan_part_cycle", cycle=cycle))
        await u.send_msg(
            source,
            self._tr(
                source,
                "lock.plan_ok",
                channel=target.mention,
                detail=" / ".join(parts),
            ),
        )
        if self.audit:
            await self.audit.log(
                action="plan-lock",
                user=user,
                guild=source.guild,
                channel=target,
                detail=f"Planned: {' / '.join(parts)}",
            )

    async def _handle_unplan_lock(self, source, index: int):
        user = source.user if isinstance(source, discord.Interaction) else source.author
        if not self.store.schedules:
            await u.send_msg(
                source,
                self._tr(source, "lock.unplan_none"),
                ephemeral=True,
                delete_after=10,
            )
            return
        if index < 0 or index >= len(self.store.schedules):
            items = "\n".join(
                f"`{i}` - {s.label}" for i, s in enumerate(self.store.schedules)
            )
            await u.send_msg(
                source,
                self._tr(source, "lock.unplan_invalid_index", items=items),
                ephemeral=True,
                delete_after=15,
            )
            return
        removed = self.store.schedules[index]
        self.store.remove_by_index(index)
        await u.send_msg(
            source, self._tr(source, "lock.unplan_ok", label=removed.label)
        )
        if self.audit:
            await self.audit.log(
                action="unplan-lock",
                user=user,
                guild=source.guild,
                channel=source.channel,
                detail=f"Cancelled: {removed.label}",
            )

    # ========== Schedule Checker ==========

    @tasks.loop(minutes=1)
    async def _check_schedules(self):
        now = datetime.now(timezone.utc)
        now_local = datetime.now(tz=timezone(timedelta(hours=8)))
        to_remove: list[int] = []

        for idx, schedule in enumerate(self.store.schedules):
            channel = self.bot.get_channel(schedule.channel_id)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(schedule.channel_id)
                except Exception:
                    l.warning(f"[lock] Cannot fetch {schedule.channel_id}, removing")
                    to_remove.append(idx)
                    continue
            if not isinstance(
                channel,
                (discord.TextChannel, discord.VoiceChannel, discord.StageChannel),
            ):
                to_remove.append(idx)
                continue

            if schedule.cycle:
                if schedule.cycle_start:
                    try:
                        cy, cm, cd = _parse_day(schedule.cycle_start)
                        if (
                            now_local.date() < datetime(cy, cm, cd).date()
                        ):  # date-only comparison is intentional
                            continue
                    except ValueError:
                        pass
                if schedule.cycle_end:
                    try:
                        cy, cm, cd = _parse_day(schedule.cycle_end)
                        if (
                            now_local.date() > datetime(cy, cm, cd).date()
                        ):  # date-only comparison is intentional
                            to_remove.append(idx)
                            continue
                    except ValueError:
                        pass

            if schedule.cycle and not _cycle_matches_today(schedule.cycle, now_local):
                continue

            is_voice = isinstance(channel, (discord.VoiceChannel, discord.StageChannel))
            everyone = channel.guild.default_role

            if schedule.lock_day or schedule.lock_time:
                lock_dt = _parse_day_time(schedule.lock_day, schedule.lock_time)
                if lock_dt and lock_dt <= now:
                    try:
                        if is_voice:
                            await channel.send(
                                self._tr_guild(
                                    channel.guild, "lock.scheduled_locked_voice"
                                )
                            )
                        else:
                            await channel.send(
                                self._tr_guild(channel.guild, "lock.scheduled_locked")
                            )
                        overwrites = channel.overwrites_for(everyone)
                        overwrites.update(
                            send_messages=False,
                            send_messages_in_threads=False,
                            **({"connect": False} if is_voice else {}),
                        )
                        await channel.set_permissions(
                            everyone, overwrite=overwrites, reason="Scheduled lock"
                        )
                        l.info(f"[lock] Scheduled lock: {channel.name} ({channel.id})")
                        if not schedule.cycle:
                            schedule.lock_day = None
                            schedule.lock_time = None
                    except discord.Forbidden:
                        l.warning(f"[lock] No permission to lock {channel.id}")
                        if not schedule.cycle:
                            to_remove.append(idx)
                    except Exception as e:
                        l.error(f"[lock] Lock failed {channel.id}: {e}")

            if schedule.unlock_day or schedule.unlock_time:
                unlock_dt = _parse_day_time(schedule.unlock_day, schedule.unlock_time)
                if unlock_dt and unlock_dt <= now:
                    try:
                        overwrites = channel.overwrites_for(everyone)
                        overwrites.update(
                            send_messages=None,
                            send_messages_in_threads=None,
                            **({"connect": None} if is_voice else {}),
                        )
                        await channel.set_permissions(
                            everyone, overwrite=overwrites, reason="Scheduled unlock"
                        )
                        if is_voice:
                            await channel.send(
                                self._tr_guild(
                                    channel.guild, "lock.scheduled_unlocked_voice"
                                )
                            )
                        else:
                            await channel.send(
                                self._tr_guild(channel.guild, "lock.scheduled_unlocked")
                            )
                        l.info(
                            f"[lock] Scheduled unlock: {channel.name} ({channel.id})"
                        )
                        if not schedule.cycle:
                            schedule.unlock_day = None
                            schedule.unlock_time = None
                    except discord.Forbidden:
                        l.warning(f"[lock] No permission to unlock {channel.id}")
                        if not schedule.cycle:
                            to_remove.append(idx)
                    except Exception as e:
                        l.error(f"[lock] Unlock failed {channel.id}: {e}")

            if not schedule.cycle and (
                not schedule.lock_day
                and not schedule.lock_time
                and not schedule.unlock_day
                and not schedule.unlock_time
            ):
                to_remove.append(idx)

        for idx in sorted(set(to_remove), reverse=True):
            self.store.remove_by_index(idx)

    @_check_schedules.before_loop
    async def _before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    if bot.config.lock.enabled:  # ty:ignore[unresolved-attribute]
        await bot.add_cog(LockCog(bot))
        l.info("LockCog loaded.")
