# Tools / Admin (tools)

Provides common utility and admin commands: random number / UUID generation, message deletion, batch message clearing, channel moving, text-to-file, and command syncing.

- **Config key**: `tools`
- **Source file**: `cogs/tools.py` (batch clearing logic is in `modules/clear_message.py`)

## Commands

### `random` — Generate a Random Number

Generate a random integer within a specified range.

| Item | Description |
| --- | --- |
| Permission | Everyone |
| Rate limit | ✅ Limited (`random`, default 10 times / 60s) |
| Parameters | `min_num` (default `1`), `max_num` (default `114514`) |

- If `min_num > max_num`, they are swapped automatically.
- Slash: `/random min_num:1 max_num:100`; prefix: `//random 1 100`

### `uuid` — Generate a UUID

Generate a random UUID, sent as an **ephemeral message**, and automatically deleted after a delay.

| Item | Description |
| --- | --- |
| Permission | Everyone |
| Rate limit | ✅ Limited (`uuid`, default 10 times / 60s) |
| Parameters | `delete_after` (deletion delay in seconds, default `secret_message_delay` = 600) |

- In prefix commands, the default value is used when `delete_after <= 0`.

### `to-file` — Text to File

Send text content as a file.

| Item | Description |
| --- | --- |
| Permission | Everyone |
| Parameters | `name` (file name), `content` (file content) |
| Rate limit | ✅ Limited (`to-file`, default 10 times / 60s) |
| Audit | ✅ Recorded (`to-file`) |

- Prefix: `//to-file filename.txt the remaining content becomes the file body` (`content` is all the remaining text).

### `delete` — Delete a Message

Delete a single message with the specified ID in the **current channel**.

| Item | Description |
| --- | --- |
| Permission | Mod |
| Parameters | `message_id` (message ID), `show_to_public` (whether to display the result publicly, default `false`) |
| Bot permissions | Manage Messages |
| Audit | ✅ Recorded (`delete`) |

- Error handling: insufficient permission / message not found / non-integer ID, etc. all return a clear message.

### `clear-message` — Batch Clear Messages

Batch clear messages by various filter conditions, supporting a single channel or the entire server.

| Item | Description |
| --- | --- |
| Permission | Mod |
| Bot permissions | Manage Messages; Read Message History |
| Audit | ✅ Recorded (`clear-message`) |

#### Parameters

| Parameter | Description |
| --- | --- |
| `user` | Target user (single, selector) |
| `user_ids` | List of target user IDs (comma-separated) |
| `webhook_ids` | List of target Webhook IDs (comma-separated) |
| `nick_pattern` | Nickname wildcard (fnmatch, e.g. `*bot*`) |
| `content_pattern` | Message content wildcard (fnmatch, e.g. `*error*`) |
| `message_count` | Maximum number of messages to check per channel (empty / 0 = no limit but slower) |
| `within_minutes` | Only clear messages within the last N minutes (empty / 0 = no limit) |
| `scope` | Scope: `channel` (single channel, default) or `server` (entire server) |
| `channel` | Specify a channel (only effective when `scope=channel`, default current channel; **a forum channel can be specified**) |
| `start` | Start of range: message ID / **thread ID** or time (`30m` / `2h` / `1d` / ISO time) |
| `end` | End of range: message ID / **thread ID** or time |
| `delete_threads` | Whether to directly delete the **entire thread** created by the target user (default `false`) |
| `forum_scan_count` | How many threads to scan per forum channel (sorted by most recent activity; if empty, inherits the message count / time limit) |

#### Forum / Thread Clearing

- **Clear messages within threads**: when the target channel is a forum (or `scope=server`), forum threads are scanned and matching messages inside them are deleted. Use `forum_scan_count` to limit how many threads are scanned per forum.
- **Delete an entire thread**: with `delete_threads=true`, threads created by the target user that match the filters are deleted, **along with every message inside them**. This is why it is disabled by default.
- **Specify a range by thread ID**: `start` / `end` also accept thread IDs and use the thread creation time as the boundary; `delete_threads=true` is required.

#### Constraints

- `start`/`end` cannot be used **at the same time** as `within_minutes`/`message_count`.
- If no time range is used, at least one of `message_count` and `within_minutes` must be set.
  - **Special case**: When `delete_threads=true` and `forum_scan_count` is specified, `forum_scan_count` itself acts as the limit, so there is no need to set `message_count`/`within_minutes`. In this case **only forum threads are scanned, and regular channel messages are not**: if a forum channel is explicitly specified, only that forum is processed; otherwise all forums in the server are processed.
- If there is no range limit at all, at least one matching filter condition must be provided.
- **Messages older than 14 days cannot be batch deleted** (Discord limitation). When the number of such messages does not exceed `tools.clear_single_delete_max` (default `20`, `0` disables), they are automatically deleted one by one; if the threshold is exceeded, they are counted separately as "undeletable because older than 14 days".
- Result messages sent by the bot itself with the `[clear-message]` tag are automatically skipped to avoid accidental deletion.

#### Prefix Command Flags

Prefix mode passes arguments with `--key=value`:

```text
//clear-message --user=@someone --within=30m
//clear-message --nick="*bot*" --scope=server --count=500
//clear-message --content="*spam*" --start=1d --end=2h
//clear-message --user=@someone --channel=<forum channel> --within=7d --delete-threads=true --forum-scan-count=100
//clear-message --user=@someone --delete-threads=true --forum-scan-count=100   # scan all forums in the server
//clear-message --user=@someone --start=<thread ID> --end=<thread ID> --delete-threads=true
```

- Aliases supported: `--user-ids` / `--webhook-ids` / `--nick`(=`--nick-pattern`) / `--content`(=`--content-pattern`) / `--count` / `--within` / `--scope` / `--channel` / `--start` / `--end` / `--delete-threads` / `--forum-scan-count`(=`--forum-scan`)
- `--within` supports `30m` / `2h` / `1d` or a plain number of minutes.
- Only `--delete-threads=true` will delete an entire thread (must be explicitly enabled).

#### Result Message OK Button

The clearing result message comes with an **OK button**; clicking it deletes that result message (the clicker needs the same Mod permission as the command).

### `move-channel` — Move a Channel

Move the current or specified channel into a category, or before / after another channel.

| Item | Description |
| --- | --- |
| Permission | Mod |
| Bot permissions | Manage Channels, with a sufficient role hierarchy |
| Audit | ✅ Recorded (`move-channel`) |

#### Parameters

| Parameter | Description |
| --- | --- |
| `target_channel` | The channel to operate on (default current channel) |
| `category` | Target category |
| `before` | Move to before this channel |
| `after` | Move to after this channel |
| `sync_perm` | Whether to sync the target category's permissions (default `true`) |

- At least one of `category` / `before` / `after` must be provided.
- `before` and `after` cannot be specified at the same time.
- Prefix commands only support the two positional parameters `target_channel` and `category`.

::: tip `/sync` has moved to [Admin Commands](/en/modules/admin)
Command sync `/sync` and hot reload `/reload` are now provided by `cogs/admin.py`.
:::

## Configuration

```yaml
tools:
  enabled: false
  slash: true
  prefix: true
```

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `enabled` | `bool` | `false` | Whether to enable the tools module |
| `slash` | `bool` | `true` | Whether to register slash commands |
| `prefix` | `bool` | `true` | Whether to register prefix commands |
