# Voice Channel (voice)

Lets the bot join / leave voice channels, with support for DAVE encryption and automatic reconnection.

- **Config key**: `voicechannel`
- **Source file**: `cogs/voice.py`

## Permission Check (Special)

Voice commands use a **custom permission check** rather than the usual Mod / Admin levels:

- If `allowed_users` is **empty**: only Mods (including Admins) can use them.
- If `allowed_users` is **non-empty**: whitelisted users **or** Mods can use them.

Whitelist entries can be user IDs or usernames. You can also configure per-server whitelists via `allowed_guilds`.

## Commands

### `vc join` — Join a Voice Channel

Have the bot join the voice channel you are currently in, or a specified channel.

| Item | Description |
| --- | --- |
| Permission | Whitelisted user / Mod |
| Parameters | `channel` (optional, leave empty to use the voice channel you are currently in), `persist` (optional, persist session) |
| Bot permissions | Connect |
| Rate Limit | ✅ Limited |
| Audit | ✅ Recorded (`joinvc`) |

Behavior details:

- On joining, the bot automatically **self-deaf + self-mute** (self-deafen / self-mute).
- If the bot is already in another channel, it disconnects first and then joins the target channel (showing "Moved to").
- If it is already in the target channel, it shows "Already inside".
- If the channel requires **DAVE encryption** but the connection fails (error code 4017), a corresponding error is shown.
- Stage channels (StageChannel) are not supported for automatic joining as "the channel you are currently in".

### `vc leave` — Leave a Voice Channel

Have the bot leave the voice channel it is currently in.

| Item | Description |
| --- | --- |
| Permission | Whitelisted user / Mod |
| Rate Limit | ✅ Limited |
| Audit | ✅ Recorded (`leavevc`) |

- If the bot is not in any voice channel, a message is shown.

## Auto-Reconnect

When the bot is unexpectedly disconnected from voice (network issues, Discord server errors, kicked by admin, etc.), it will automatically attempt to reconnect.

### Reconnect Strategy

- Uses **exponential backoff**: starts at 5 seconds, doubles after each failure, capped at `reconnect_max_delay` (default 300 seconds).
- Before each attempt, checks whether the channel still exists and whether the bot has Connect permission.
- If the channel has been deleted or is no longer a voice channel, reconnect stops.
- If the bot has already reconnected to the same channel through other means, reconnect stops.

### Persist Mode (`persist`)

The `persist` parameter on `vc join` controls behavior after disconnection:

| Scenario | `persist=false` (default) | `persist=true` |
| --- | --- | --- |
| Network / Discord disconnect | Auto-reconnect | Auto-reconnect |
| Kicked by admin | **No** reconnect | Auto-reconnect, sends hint in voice channel |
| `/vc leave` used | **No** reconnect | **No** reconnect |
| Missing Connect permission | Retry with backoff | Retry with backoff |

When `persist=true` and the bot is kicked by an admin, after reconnecting it sends a message in the voice channel telling the admin to use `/vc leave` or `{prefix}vc leave` to make the bot leave.

::: tip Persisted Data
Persisted session info is saved in `voice.yaml` in the data directory. The bot will automatically restore the connection after restart.
:::

## Configuration

```yaml
voicechannel:
  enabled: false
  slash: true
  prefix: true
  allowed_users: []           # empty: only mod can use; non-empty: whitelisted users + mod can use
  allowed_guilds: {}           # per-server whitelist { guild_id: [user...] }
  reconnect: true             # auto-reconnect after disconnect
  reconnect_max_delay: 300    # max exponential backoff delay (seconds)
```

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `enabled` | `bool` | `false` | Whether to enable the voice module |
| `slash` | `bool` | `true` | Whether to register slash commands |
| `prefix` | `bool` | `true` | Whether to register prefix commands |
| `allowed_users` | `list[int \| str]` | `[]` | Whitelist for voice commands (user IDs / usernames) |
| `allowed_guilds` | `dict[int \| str, list[int \| str]]` | `{}` | Per-server whitelist |
| `reconnect` | `bool` | `true` | Auto-reconnect after disconnect (including when Discord's internal reconnect fails) |
| `reconnect_max_delay` | `int` | `300` | Max exponential backoff delay for reconnect (seconds) |

::: tip DAVE Encryption
DAVE (Discord Audio & Video End-to-End Encryption) depends on `davey` and `PyNaCl`, which are already included in the project dependencies (`discord-py[voice]`).
:::
