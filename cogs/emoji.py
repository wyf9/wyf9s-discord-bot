import io

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger as l
from pydantic import BaseModel, ValidationError

import utils as u
from i18n import lang_of, ls
from i18n import t as _t
from modules.audit import AuditLogger


class EmojiModel(BaseModel):
    utc_build_timestamp: int = 0
    is_cf_pages: bool = False
    commit_id: str | None = None
    commit_branch: str | None = None
    emojis: list[str] = []


class EmojiCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.c = bot.config  # ty:ignore[unresolved-attribute]
        self.audit: AuditLogger | None = getattr(bot, "audit", None)
        self.lang_store = getattr(bot, "lang_store", None)

    def _tr(self, source, key: str, **kwargs) -> str:
        return _t(key, lang_of(source, self.lang_store), **kwargs)

    def cog_load(self):
        if not getattr(self.bot, "emoji_data", None):
            self.bot.emoji_data = EmojiModel()  # ty:ignore[unresolved-attribute]

    @property
    def emoji_data(self) -> EmojiModel:
        return self.bot.emoji_data  # ty:ignore[unresolved-attribute]

    # ========== Slash Group: /emoji ==========

    emoji_group = app_commands.Group(
        name="emoji", description=ls("emoji.cmd_group_desc")
    )

    def _build_update_msg(self, source) -> str:
        return self._tr(
            source,
            "emoji.update_success",
            ts=self.emoji_data.utc_build_timestamp,
            commit=self.emoji_data.commit_id,
            count=len(self.emoji_data.emojis),
        )

    def _build_info_msg(self, source) -> str:
        ed = self.emoji_data
        return self._tr(
            source,
            "emoji.info",
            ts=ed.utc_build_timestamp,
            cf=self._tr(source, "emoji.info_yes")
            if ed.is_cf_pages
            else self._tr(source, "emoji.info_no"),
            commit=ed.commit_id,
            branch=ed.commit_branch,
            count=len(ed.emojis),
            base_url=self.c.emoji.base_url,
        )

    @emoji_group.command(name="update", description=ls("emoji.cmd_update_desc"))
    @u.requires(u.Permission.ADMIN, perm_module="emoji")
    async def emoji_update(self, interaction: discord.Interaction):
        await interaction.response.defer()
        succ, err = await self.update_emoji_list()
        if succ:
            await interaction.followup.send(self._build_update_msg(interaction))
            if self.audit:
                await self.audit.log(
                    action="emoji-update",
                    user=interaction.user,
                    guild=interaction.guild,
                    channel=interaction.channel,
                    detail=f"Updated emoji list ({len(self.emoji_data.emojis)} total)",
                )
        else:
            await interaction.followup.send(
                self._tr(interaction, "emoji.update_failed", error=err),
                ephemeral=True,
            )

    @emoji_group.command(name="info", description=ls("emoji.cmd_info_desc"))
    async def emoji_info(self, interaction: discord.Interaction):
        if not await self._check_rate_limit(interaction, "emoji info"):
            return
        await interaction.response.send_message(self._build_info_msg(interaction))

    # ========== Slash: /e (send emoji) ==========

    async def e_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        filtered = [
            app_commands.Choice(name=name, value=name)
            for name in self.emoji_data.emojis
            if current.lower() in name.lower()
        ][: self.c.emoji.max_results]
        return filtered

    @app_commands.command(name="e", description=ls("emoji.cmd_e_desc"))
    @app_commands.describe(name=ls("emoji.param_e_name"))
    @app_commands.autocomplete(name=e_autocomplete)
    async def e(self, interaction: discord.Interaction, name: str):
        if not await self._check_rate_limit(interaction, "e"):
            return
        if name not in self.emoji_data.emojis:
            await interaction.response.send_message(
                self._tr(interaction, "emoji.invalid_name"),
                ephemeral=True,
                delete_after=10,
            )
            return

        imgurl = f"{self.c.emoji.base_url}/{name}"
        await interaction.response.defer()

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(imgurl, proxy=self.c.proxy) as resp,
            ):
                img = await resp.read()
                with io.BytesIO(img) as file:
                    await interaction.followup.send(
                        file=discord.File(
                            fp=file,
                            filename=name,
                            description=self._tr(
                                interaction, "emoji.sticker_desc", name=name
                            ),
                        )
                    )
        except Exception as err:
            await interaction.followup.send(
                self._tr(
                    interaction, "emoji.fetch_error", name=name, url=imgurl, error=err
                ),
                ephemeral=True,
            )

    # ========== Prefix Commands ==========

    @commands.group(name="emoji", invoke_without_command=True)
    async def prefix_emoji(self, ctx: commands.Context):
        await ctx.send(self._tr(ctx, "emoji.usage_prefix"))

    @prefix_emoji.command(name="update")
    @u.requires(u.Permission.ADMIN, perm_module="emoji")
    async def prefix_emoji_update(self, ctx: commands.Context):
        await ctx.defer()
        succ, err = await self.update_emoji_list()
        if succ:
            await ctx.send(self._build_update_msg(ctx))
            if self.audit:
                await self.audit.log(
                    action="emoji-update",
                    user=ctx.author,
                    guild=ctx.guild,
                    channel=ctx.channel,  # ty:ignore[invalid-argument-type]
                    detail=f"Updated emoji list ({len(self.emoji_data.emojis)} total)",
                )
        else:
            await ctx.send(
                self._tr(ctx, "emoji.update_failed", error=err), delete_after=10
            )

    @prefix_emoji.command(name="info")
    async def prefix_emoji_info(self, ctx: commands.Context):
        if not await self._check_rate_limit(ctx, "emoji info"):
            return
        await ctx.send(self._build_info_msg(ctx))

    @commands.command(name="e")
    async def prefix_e(self, ctx: commands.Context, *, name: str):
        if not await self._check_rate_limit(ctx, "e"):
            return
        if name not in self.emoji_data.emojis:
            await ctx.send(self._tr(ctx, "emoji.invalid_name"), delete_after=10)
            return

        imgurl = f"{self.c.emoji.base_url}/{name}"
        await ctx.defer()

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(imgurl, proxy=self.c.proxy) as resp,
            ):
                img = await resp.read()
                with io.BytesIO(img) as file:
                    await ctx.send(
                        file=discord.File(
                            fp=file,
                            filename=name,
                            description=self._tr(ctx, "emoji.sticker_desc", name=name),
                        )
                    )
        except Exception as err:
            await ctx.send(
                self._tr(ctx, "emoji.fetch_error", name=name, url=imgurl, error=err),
                delete_after=10,
            )

    # ========== Shared Logic ==========

    async def _check_rate_limit(self, source, command: str) -> bool:
        rate_limiter = getattr(self.bot, "rate_limiter", None)
        if not rate_limiter:
            return True
        return await u.check_rate_limit(
            source,
            config=self.c,
            rate_limiter=rate_limiter,
            module="emoji",
            command=command,
        )

    async def update_emoji_list(self) -> tuple[bool, str]:
        l.info("[emoji] Updating emoji list...")
        succ, resp, err = await u.get_json(
            f"{self.c.emoji.base_url}/emoji.json?disable-cache"
        )
        if succ:
            try:
                self.bot.emoji_data = EmojiModel.model_validate(resp)  # ty:ignore[unresolved-attribute]
            except ValidationError as e:
                l.warning(f"[emoji] Emoji list sync failed! \n{e}")
                return False, str(e)
            l.info(f"[emoji] Emoji list synced (count: {len(self.emoji_data.emojis)})")
            l.debug(f"[emoji] {self.emoji_data.emojis}")
            return True, ""
        else:
            l.warning(f"[emoji] Emoji list sync failed: {err}")
            return False, err


async def setup(bot: commands.Bot):
    if bot.config.emoji.enabled:  # ty:ignore[unresolved-attribute]
        await bot.add_cog(EmojiCog(bot))
        l.info("EmojiCog loaded.")
