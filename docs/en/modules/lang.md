# Localization (lang)

Switch the language preference of a user / server. All user-facing text of the bot supports localization (i18n).

- **Config key**: none (this module is always enabled)
- **Source files**: `cogs/lang.py`, `i18n.py`, `lang_store.py`, `lang/*.yaml`

## Language Resolution Priority

For each message, the bot resolves the language to use in the following priority order:

1. **User preference** — the personal language the user set via `/lang`
2. **Server preference** — the language a server administrator set via `/lang scope:server`
3. **Default language** — `zh` (Simplified Chinese)

Preferences are persisted to `lang_settings.yaml` (auto-generated).

## Commands

### `/lang` — Set / view language preference

| Item | Description |
| --- | --- |
| Permission | Everyone (`scope:server` requires the "Manage Server" permission or a config admin) |
| Parameter | `lang` (optional, `zh` / `en`, leave empty to view the current setting), `scope` (optional, `user` (default) / `server`) |

- `/lang lang:en` — Set **your** language to English.
- `/lang lang:zh scope:server` — Set **this server's** default language to Chinese (requires manage permission).
- `/lang` — View your current language preference.
- `/lang scope:server` — View this server's language preference.

## Coverage

Runtime messages such as command replies, errors, and audit logs use the priority above. Slash command and parameter descriptions follow the user's **Discord client language**; command names stay unchanged.

## Supported Languages

| Code | Language | Discord Locale |
| --- | --- | --- |
| `zh` | Simplified Chinese (default) | `zh-CN` / `zh-TW` |
| `en` | English | `en-US` / `en-GB` |

