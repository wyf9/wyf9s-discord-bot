# wyf9s-discord-bot

A multi-purpose Discord bot built on discord.py with YAML + Pydantic configuration validation. Modules use the discord.py Cog architecture and support hot reloads. Built-in internationalization (i18n) lets users and servers switch languages independently.

## Feature Modules

| Module | Description |
| --- | --- |
| Tools (`tools`) | Random number / UUID generation, message deletion, bulk message cleanup, channel moving, exporting content as files |
| Emoji (`emoji`) | Browse / search / send remote emoji packs, view emoji source build info, update the emoji library |
| Channel Lock (`lock`) | Lock / unlock channels, with one-time / daily / weekly / monthly scheduled locks |
| Voice Channel (`voice`) | Bot joins / leaves voice channels, with DAVE encryption support |
| Auto Management (`manage`) | Auto-delete messages by nickname pattern and remove no-embed messages from selected bots in configured channels |
| Anti-Spam (`antispam`) | Channel-level anti-spam rules, automated actions, message cleanup, and audit logging |
| Audit Log (`audit`) | Global / per-server audit records for management actions, automated actions, and errors |
| Admin (`admin`) | Command sync and module / config hot reloads |
| Dynamic Permissions (`perm`) | Dynamic permission management via `perm.yaml`, with `config.yaml` always taking priority |
| Announcement Push (`announce`) | Follow announcement channels and let Discord forward messages automatically |
| Chat Enhance (`chatenhance`) | Server-level feature toggles; auto-converts X/Twitter links to a previewable form (fixupx / x-to-img) |
| Multilingual (`lang`) | Switch language preferences per user / server |

## Documentation

- Project overview: [Docs home](https://dc-bot.wyf9.top/en/) / [Introduction](https://dc-bot.wyf9.top/en/guide/introduction)
- Getting started and deployment: [Getting Started](https://dc-bot.wyf9.top/en/guide/getting-started)
- Configuration: [Configuration Guide](https://dc-bot.wyf9.top/en/guide/configuration)
- Permission system: [Permission System](https://dc-bot.wyf9.top/en/guide/permissions)
- Rate limits: [Rate Limit](https://dc-bot.wyf9.top/en/guide/rate-limit)
- Modules and commands: [Module Overview](https://dc-bot.wyf9.top/en/modules/)
- Terms of Service: [Terms of Service](https://dc-bot.wyf9.top/en/legal/tos)
- Privacy Policy: [Privacy Policy](https://dc-bot.wyf9.top/en/legal/privacy)

## License

[MIT](https://github.com/wyf9/wyf9s-discord-bot/blob/main/LICENSE)
