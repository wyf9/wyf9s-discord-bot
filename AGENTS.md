# AGENTS.md

## Code Quality

After making changes, always run (in this order):

```bash
uvx ruff check --fix && uvx ty check --fix && uvx ruff format
```

- `ruff check --fix` — lint and auto-fix
- `ty check --fix` — type check and auto-fix
- `ruff format` — format code (**must** run after `ruff check` and `ty check` so that
  their fixes are formatted consistently)

**Commit requirements:**

- **All ruff errors/warnings, ty errors/warnings, and other hints must be resolved
  before committing.** Do not leave any unaddressed diagnostics.
- **Do NOT use `# noqa` or `type: ignore` to suppress issues on an entire file or
  line unless absolutely necessary and reasonable.** When suppression is justified,
  add the specific rule id to `pyproject.toml`'s `lint.ignore` list and include a
  comment naming the rule (e.g. `# noqa: E402  # module-import-not-at-top-of-file`).
  The existing project-level ignores in `pyproject.toml` already follow this
  convention — always check them before adding new suppressions.

### prek (pre-commit)

The repo ships a [`prek`](https://prek.j178.dev) config (`prek.toml`, prek-native TOML — not the `.pre-commit-config.yaml` compat format). It runs `ruff check --fix`, `ty check --fix`, and `ruff format` as local hooks (ruff format runs last).

- Install the git hook once per clone: `uvx prek install`
- Run on demand: `uvx prek run --all-files`

## Project Structure

```text
config.py            # Pydantic config models + loader
config.yaml          # Runtime config (gitignored)
config.example.yaml  # Example config with docs
schedules.yaml       # Scheduled lock data (auto-generated)
main.py              # Bot entry point, cog loading, translator setup
utils.py             # Shared utilities (perm decorators, rate limiter, send_msg)
i18n.py              # i18n runtime (t/lang_of) + Discord command localization
lang_store.py        # Per-user / per-guild language preference persistence
lang_settings.yaml   # Saved language preferences (auto-generated, gitignored)
lang/
  zh.yaml            # Chinese strings (default language)
  en.yaml            # English strings
cogs/                # Command modules (discord.py Cogs, loaded in main.py COG_LIST)
  emoji.py           # Emoji/sticker commands
  tools.py           # Utility/moderation commands (+ clear-message)
  lock.py            # Channel lock/unlock + scheduled locks
  voice.py           # Voice channel commands
  antispam.py        # Anti-spam message handler
  manage.py          # Auto-delete event handlers
  admin.py           # /sync, /reload
  perm.py            # /perm dynamic permission management
  announce.py        # /subscribe announcement following
  lang.py            # /lang language preference
  chatenhance.py     # Chat enhance (autofixupx) + /enhance
modules/             # Shared, command-less services used by cogs
  audit.py           # Audit logging service (+ antispam action view)
  clear_message.py   # Bulk message clearing service
docs/                # VitePress user docs (zh root + en/), excluded agents/
  agents/            # Internal agent/maintainer notes (not built into the site)
tests/               # unittest suites (run with .venv/bin/python -m unittest discover -s tests)
```

## Module Maintenance Docs

Start here before changing a module; these notes cover code entry points,
shared state, and gotchas (not shipped to the user docs site):

- [Config system](docs/agents/config.md) · [Rate limit](docs/agents/ratelimit.md) · [i18n](docs/agents/i18n.md) · [Docs maintenance](docs/agents/docs.md)
- [tools](docs/agents/tools.md) · [emoji](docs/agents/emoji.md) · [lock](docs/agents/lock.md) · [voice](docs/agents/voice.md)
- [admin](docs/agents/admin.md) · [perm](docs/agents/perm.md) · [announce](docs/agents/announce.md) · [chatenhance](docs/agents/chatenhance.md) · [lang](docs/agents/lang.md)
- [manage](docs/agents/manage.md) · [antispam](docs/agents/antispam.md) · [audit](docs/agents/audit.md)

## Config System

- `config.yaml` - User-editable YAML config
- `config.py` - Pydantic `BaseModel` hierarchy validated on startup
- Each module has `enabled: bool = False` (default off)
- Slash/prefix toggles: `slash: bool = True`, `prefix: bool = True`

## Module Pattern

Command modules are discord.py **Cogs** (`commands.Cog` subclasses) in `cogs/`, loaded
via `main.py` `COG_LIST`. Each cog reads shared state from the `bot` instance and defines
both slash and prefix commands that funnel into a shared `_handle_*` method:

```python
class MyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.c = bot.config
        self.audit = getattr(bot, "audit", None)
        self.lang_store = getattr(bot, "lang_store", None)

    def _tr(self, source, key: str, **kwargs) -> str:
        return _t(key, lang_of(source, self.lang_store), **kwargs)

    @app_commands.command(name="cmd", description=ls("mycog.cmd_desc"))
    async def slash_cmd(self, interaction: discord.Interaction):
        await self._handle_cmd(interaction)

    @commands.command(name="cmd")
    async def prefix_cmd(self, ctx: commands.Context):
        await self._handle_cmd(ctx)

    async def _handle_cmd(self, source):
        # Shared logic for both slash and prefix
        await u.send_msg(source, self._tr(source, "mycog.done"))


async def setup(bot: commands.Bot):
    if bot.config.mycog.enabled:
        await bot.add_cog(MyCog(bot))
```

- Register the cog in `COG_LIST` in `main.py`.
- `setup()` gates loading on the module's `enabled` flag.
- Shared per-bot state (audit, rate limiter, perm store, lang store, emoji cache,
  schedule store) is stored on the `bot` instance so it survives cog reloads.

## Internationalization (i18n)

All user-facing text must be localized. Never hardcode display strings.

- Strings live in `lang/zh.yaml` (default) and `lang/en.yaml`, keyed by `namespace.key`.
  Both files must stay in key-parity; add a key to both when introducing text.
- `f`-string interpolation uses `{name}` placeholders resolved via `str.format`.
- **Runtime messages** (command replies, errors): resolve the language per user with
  `self._tr(source, "ns.key", **fmt)` (helper wraps `i18n.t(key, lang_of(source, lang_store))`).
  For channel/guild-scoped messages with no user (scheduled locks, antispam public
  notices, audit embeds) resolve via `lang_store.resolve(0, guild.id)`.
- **Slash command & parameter descriptions**: wrap with `ls("ns.key")` from `i18n`.
  These register the English string as the base value; `I18nTranslator` (set in
  `main.py` via `tree.set_translator`) provides per-locale translations at `tree.sync()`
  time. Command/group **names** stay plain ASCII strings (not localized).
- `lang_of(source, lang_store)` resolves the effective language from an
  `Interaction`/`Context`; `LangStore.resolve(user_id, guild_id)` applies the
  user > guild > default (`zh`) precedence.
- The `/lang` command (`cogs/lang.py`) lets users/servers set their preference.
- Language ↔ Discord locale mapping lives in `i18n._LOCALE_TO_LANG`; extend
  `SUPPORTED_LANGS` + add a `lang/<code>.yaml` to add a language.

## Type Checking Notes

- discord.py type stubs are strict about channel types
- Use `type: ignore[arg-type]` for `ctx.channel` / `interaction.channel` where guild context is assumed
- `AuditLogger.log()` accepts `discord.Thread` in channel parameter

## Documentation

- After modifying a module or adding new configuration fields, update `config.example.yaml` and sync the docs if needed.
- When adding/changing user-facing text, update **both** `lang/zh.yaml` and `lang/en.yaml`.
- `config.example.yaml` — example config with inline docs (the source of truth for config fields)
- `README.md` / `README.en.md` — concise entry points only: keep the introduction and module overview inline, and make every other section point to the matching Chinese / English docs URL instead of duplicating documentation.
- `docs/` — VitePress site (guides + per-module pages); keep command tables and the i18n guide in sync
- `docs/agents/` — internal agent/maintainer notes; excluded from the VitePress build via `srcExclude`
- `AGENTS.md` — global developer/agent rules only; module-specific notes live under `docs/agents/`

### Bilingual docs (i18n)

The docs site is bilingual: Simplified Chinese at the root (`docs/**`) and
English under the `/en/` locale (`docs/en/**`). The language switcher is wired
up in `docs/.vitepress/config.mts` via `locales` (`root` = zh, `en` = English).

- **Chinese and English docs must stay fully in sync.** Whenever you add or
  change a page/section under `docs/`, apply the equivalent change to the
  mirrored file under `docs/en/` (and vice versa). A zh page at
  `docs/<path>.md` maps to `docs/en/<path>.md`.
- Internal doc links in English pages use the `/en/` prefix
  (e.g. `/en/modules/tools`); external links stay unchanged.
- Because headings are translated, the `#anchor` slugs differ between zh and en
  — don't reuse a Chinese anchor in an English link.
- Verify with a build: `cd docs && bunx vitepress build`.

## Changelog / Announcement

Only generate a changelog **when the user explicitly asks for one.** Do not
volunteer it after ordinary changes.

When asked to write a changelog for the bot announcement channel:

1. Provide **both** Chinese and English versions (no need to explicitly label which is which).
2. Wrap the **whole** changelog output in a fenced ` ```md ` code block so the
   user can copy it in one go.
3. Get the current date from the system (run `date +%Y-%m-%d`) and use it as the
   changelog date — never guess.
4. Each language starts with a dated heading that includes a language flag icon:

   ```md
   # :flag_cn: 更新日志 - 2026-07-15

   - ...

   # :flag_us: Changelog - 2026-07-15

   - ...
   ```

5. Append a `[Docs](url)` link after every change entry, pointing to the most
   precise documentation location possible (may include `#section-name`).
   Docs site base URL is `https://dc-bot.wyf9.top` (VitePress `cleanUrls`).
   - The **Chinese** changelog links to the Chinese docs, e.g.
     `https://dc-bot.wyf9.top/guide/getting-started#启动参数`.
   - The **English** changelog links to the English docs with the `/en/` prefix,
     e.g. `https://dc-bot.wyf9.top/en/guide/getting-started#launch-arguments`.
   - The `#anchor` differs between languages (headings are translated), so pick
     the correct per-language anchor rather than reusing the Chinese one.
6. Purely technical changes that basically don't affect the user experience
   (refactors, tooling, CI, dependency bumps, etc.) go as **subtext** (`-#`
   small-text lines) at the **end of each language section**, instead of as
   normal bullet points:

   ```md
   # :flag_cn: 更新日志 - 2026-07-15

   - 面向用户的更新... [Docs](https://dc-bot.wyf9.top/...)

   -# (技术性修改)
   -# - 某项内部重构
   -# - 某项工具链调整
   ```

7. Breaking changes go in their own emphasized section: `## :rotating_light: 破坏性更改`
   (Chinese) / `## :rotating_light: Breaking Changes` (English).

## Logging & Audit

- `AuditLogger.log(...)` sends an embed to a single audit channel set
  (`audit.global_channel` + per-guild `{channel}`). Only log **meaningful**
  operations: commands tagged `[ADMIN]`/`[MOD]`, server-scope changes
  (`/lang scope:server`, `/vc`, `/move-channel`, …), and automated moderation /
  errors. Do **not** audit trivial user-scope commands (`/random`, `/uuid`,
  `/to-file`, `/lang` user scope).
- All slash command errors are caught by `client.tree.error` in `main.py`, which logs full tracebacks and sends to the audit channel.
- Batch operations (e.g. `clear-message`, `announce`, `antispam-auto-catch`) should **not** log individual per-item failures to audit—log one summary at the end. Use `l.warning()` for per-item debug logging to avoid flooding audit channels.
- If audit logging itself fails (e.g. channel not found, Forbidden), catch and silently ignore.
- stdlib logging (incl. discord.py) is funneled to loguru via a single
  `InterceptHandler` on the root logger; discord.py verbosity is set separately
  via `log.discord_level` (default `INFO`) to avoid gateway spam at app DEBUG.

@README.md
