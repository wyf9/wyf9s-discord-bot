# Rate limiting

"Rate limiting" here comes in two kinds: the bot's **custom command rate limiting** (application layer), and Discord's platform **API rate limit** (handled automatically by discord.py).

## Custom command rate limiting

The [Tools module](/en/modules/tools) and the [Emoji module](/en/modules/emoji) implement **sliding-window rate limiting** for the following commands to prevent abuse:

- `random`
- `uuid`
- `to-file`
- `e`
- `emoji-info`

In addition, **all commands** have a global rate-limit fallback of 10 reqs / 10s (handled uniformly by the `@u.requires()` decorator).

### How it works

The `RateLimiter` (`utils.py`) keys on `(command, user ID)` and records the call timestamps within the window:

```python
def hit(self, key, limit, window) -> tuple[bool, float]:
    # Returns (allowed?, seconds to wait if limited)
```

- Each user is **counted independently** for each command.
- When the limit is exceeded, the bot replies with `:hourglass_flowing_sand: Rate limited, retry in Ns` (a temporary message).

### Quota rules

| User type | Quota |
| --- | --- |
| **Regular user** | Base quota (e.g. `random: 10`) |
| **Mod** | Base quota × `mod_multiplier` (default ×3) |
| **Admin** | **Not rate-limited** |

> Here, Admin means a server admin or config admin (`is_admin`); Mod means someone matched in the mod list. See [Permission system](/en/guide/permissions) for details.

### Configuration

Rate limiting is **global**, with per-module / per-command quotas:

```yaml
ratelimit:
  enabled: true          # Whether to enable rate limiting
  window: 60             # Time window (seconds)
  mod_multiplier: 3      # Mod quota multiplier (relative to normal users); admin is not rate limited
  modules:               # Default quota per module
    emoji: 10
  commands:              # Quota per command / subcommand
    vc: 20
    "emoji update": 5
```

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `enabled` | `bool` | `true` | Whether to enable rate limiting |
| `window` | `int` | `60` | Time window in seconds |
| `mod_multiplier` | `int` | `3` | Mod quota multiplier relative to regular users |
| `modules` | `map` | Built-in command quotas | Default quota keyed by module name |
| `commands` | `map` | Built-in command quotas | Quota keyed by command or full subcommand name |

Quota precedence: **subcommand > command > module** (e.g. `"emoji update"` > `emoji` > `modules.emoji`).

The legacy `tools.ratelimit` / `emoji.ratelimit` sections are still accepted and migrated into the global `ratelimit` config. If `ratelimit` is omitted entirely, the legacy default command quotas still apply; once it is configured explicitly, only the listed `modules` / `commands` are used.

## Discord API rate limit

Beyond application-layer rate limiting, the Discord platform itself imposes a **rate limit** on API calls. This part is **handled automatically by discord.py**: the library parses the `X-RateLimit-*` response headers and, when a limit is hit, automatically queues / backs off and retries, with no extra configuration needed.

Scenarios worth noting:

- **Bulk message cleanup** (`clear-message`): uses `bulk_delete` (up to 100 messages per batch), and Discord **does not allow bulk-deleting messages older than 14 days**. When the number of such expired messages does not exceed `tools.clear_single_delete_max` (default `20`, set to `0` to disable), it **falls back to deleting them one by one with `Message.delete()`** (not subject to the 14-day limit); if the threshold is exceeded, they are still counted individually as "undeletable because older than 14 days", to avoid triggering rate limits with a large number of per-message requests.
- **Emoji sending**: makes an HTTP request to the remote `base_url` (via the `proxy` config), affected by the availability of the remote service.
- **Emoji search autocomplete**: too large a `max_results` may cause Discord autocomplete calls to fail; the default is `25`.

> If you use it heavily on a large self-hosted server, it is still recommended to set reasonable custom rate-limit quotas to avoid triggering Discord's global rate limiting through excessive requests.
