# Module Overview

The bot is composed of multiple modules, all **enabled on demand** via the `enabled` switch in `config.yaml` (disabled by default). Modules fall into three categories:

- **Command modules**: register slash / prefix commands for users to invoke (using the discord.py Cog architecture).
- **Event modules**: no commands; listen to Discord events (such as `on_message`) and run automatically.
- **Service modules**: no commands; provide shared capabilities to other modules (such as audit logging).

## Module List

| Module | Config Key | Type | Commands |
| --- | --- | --- | --- |
| [Tools / Admin](/en/modules/tools) | `tools` | Command | `random` `uuid` `to-file` `delete` `clear-message` `move-channel` |
| [Emoji](/en/modules/emoji) | `emoji` | Command | `/e` `/emoji info` `/emoji update` |
| [Channel Lock](/en/modules/lock) | `lock` | Command | `/lock now` `/lock unlock` `/lock plan` `/lock unplan` |
| [Voice Channel](/en/modules/voice) | `voicechannel` | Command | `/vc join` `/vc leave` |
| [Admin Commands](/en/modules/admin) | — | Command | `/sync` `/reload` |
| [Dynamic Permissions](/en/modules/perm) | `perm` | Command | `/perm add` `/perm rm` `/perm show` |
| [Announcement Push](/en/modules/announce) | `announce` | Command | `/subscribe` |
| [Chat Enhance](/en/modules/chatenhance) | `chatenhance` | Command / Event | `/enhance enable` `/enhance disable` `/enhance list` |
| [Multilingual](/en/modules/lang) | — (always enabled) | Command | `/lang` |
| [Auto Management](/en/modules/manage) | `rmmsg` / `rmtodo` | Event | None |
| [Anti-spam](/en/modules/antispam) | `antispam` | Event | None |
| [Audit Log](/en/modules/audit) | `audit` | Service | None |

## Command Quick Reference

| Command | Permission | Rate Limit | Description |
| --- | --- | --- | --- |
| `/random` | Everyone | Per-command quota | Generate a random number within a range |
| `/uuid` | Everyone | Per-command quota | Generate a UUID (ephemeral message) |
| `/to-file` | Everyone | Per-command quota | Send text as a file |
| `/delete` | Mod | — | Delete a single message |
| `/clear-message` | Mod | — | Batch clear messages by conditions |
| `/move-channel` | Mod | — | Move channel position / category |
| `/e` | Everyone | Per-module quota | Send an emoji from the library |
| `/emoji info` | Everyone | Per-command quota | View emoji library info |
| `/emoji update` | Admin | Per-command quota | Update emoji library data |
| `/lock now` | Mod | — | Lock a channel |
| `/lock unlock` | Mod | — | Unlock a channel |
| `/lock plan` | Mod | — | Schedule lock / unlock |
| `/lock unplan` | Mod | — | Cancel a schedule |
| `/vc join` | Allowlist / Mod | Per-command quota | Bot joins a voice channel |
| `/vc leave` | Allowlist / Mod | Per-command quota | Bot leaves a voice channel |
| `/sync` | Admin | — | Sync the slash command list |
| `/reload` | Admin | 15s CD | Hot reload modules |
| `/perm add` | Admin | — | Add a permission rule |
| `/perm rm` | Admin | — | Remove a permission rule |
| `/perm show` | Admin | — | View permission rules |
| `/subscribe` | Mod | — | Follow an announcement channel |
| `/enhance enable` | Admin | — | Enable a chat enhance function |
| `/enhance disable` | Admin | — | Disable a chat enhance function |
| `/enhance list` | Admin | — | View chat enhance function status |
| `/lang` | Everyone (server scope requires admin permission) | — | Switch / view language preference |

> Rate-limit quotas are configured under `ratelimit` in `config.yaml`; see [Rate Limiting](/en/guide/rate-limit). For permissions, see [Permission System](/en/guide/permissions).

## Dual Command Mode

All command modules can control the registration of slash and prefix commands separately via the `slash` / `prefix` switches. The prefix for prefix commands is determined by the top-level `command_prefix` (the example config uses `//`).

- Slash command example: `/random 1 100`
- Prefix command example: `//random 1 100`

Complex commands (`clear-message`, `lock plan`) use `--key=value` flags to pass arguments in their prefix form, for example:

```text
//lock plan --channel=#announcements --lock-time=22-00 --unlock-time=08-00 --cycle=daily
```
