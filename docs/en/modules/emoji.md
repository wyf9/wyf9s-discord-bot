# Emoji (emoji)

Browse, search, and send emojis from a remote emoji source (as files / stickers), and view the emoji source's build information.

- **Config key**: `emoji`
- **Source file**: `cogs/emoji.py`

## Commands

### `/e` — Send an Emoji

Select and send an emoji from the emoji library.

| Item | Description |
| --- | --- |
| Permission | Everyone |
| Parameters | `name` (emoji name, slash command has **autocomplete**) |

- When typing a slash command, candidates are fuzzy-matched against the current input, returning up to `max_results` candidates.
- If the name is not in the library, "Invalid emoji name" is shown.

### `/emoji info` — Emoji Library Info

View the emoji source's build information.

| Item | Description |
| --- | --- |
| Permission | Everyone |

The returned information includes: build time, whether it was built on CF Pages, Commit ID / branch, emoji count, and the link to the emoji source `emoji.json`.

### `/emoji update` — Update Emoji Library

Re-fetch the emoji list from the remote source and refresh the cache.

| Item | Description |
| --- | --- |
| Permission | **Admin** |
| Audit | ✅ Recorded (`emoji-update`) |

On success, returns the build time, Commit, and emoji count.

## Configuration

```yaml
emoji:
  enabled: false
  slash: true
  prefix: true
  base_url: "https://ghimg.siiway.top/emoji"
  max_results: 25
```

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `enabled` | `bool` | `false` | Whether to enable the emoji module |
| `slash` | `bool` | `true` | Whether to register slash commands |
| `prefix` | `bool` | `true` | Whether to register prefix commands |
| `base_url` | `str` | `https://ghimg.siiway.top/emoji` | Emoji source base URL (no trailing `/`; the directory must contain `emoji.json`) |
| `max_results` | `int` | `25` | Maximum number of search / autocomplete results (too large may cause call failures) |

::: tip
Emoji image requests use the top-level `proxy` configuration. If the remote source is unreachable, sending an emoji returns a fetch error.
:::
