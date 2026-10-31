# Dynamic Permissions (perm)

Manage dynamic permission rules via the `/perm` command, stored in `perm.yaml`. Configuration in `config.yaml` always takes precedence.

- **Config key**: `perm`
- **Source files**: `cogs/perm.py`, `perm.py`
- **Data file**: `perm.yaml`

## Rule Granularity

Dynamic permissions act as a **supplement** to `mods` / `admins` in `config.yaml`, which always takes precedence (its rules appear as :lock: in `/perm show`). Rules can grant three levels of granularity:

- **Single module** (`module`): all commands under that module.
- **Single command** (`command`): only that command.
- **Mod permission** (neither `module` nor `command` set): equivalent to the `mods` list in `config.yaml`, granting **all mod-level commands** (`/lock`, `/vc`, `/move-channel`…).

## Commands

`/perm` is split into three subcommands: `/perm add`, `/perm rm`, `/perm show`.

### `/perm add` — Add a rule

| Item | Description |
| --- | --- |
| Permission | Admin (config admins) or server administrator (server scope only) |
| Parameter | `user` / `role` (one required), `module` (supports dropdown autocomplete) / `command` (one of the two, **neither set = grant mod permission**), `global` (bool option), `private` (bool option) |

- When **neither `module` nor `command`** is specified, the user or role is granted "mod permission" — equivalent to the `mods` list in the config file, with all mod-level commands available.
- Server administrators can only add rules with `global=False`.

### `/perm rm` — Remove a rule

| Item | Description |
| --- | --- |
| Permission | Admin or server administrator |
| Parameter | `rid` (rule ID) or a combination of `user` / `role` / `module` / `command` filters |

### `/perm show` — View rules

| Item | Description |
| --- | --- |
| Permission | Admin or server administrator |
| Parameter | `user`, `role`, `module`, `command` (optional filters), `scope` (`server` / `global` option), `private`, `show_server_mods`, `show_global` |

- By default, shows members who naturally hold mod permission by virtue of being the server owner, a server administrator, or a bot mod, in the order "owner > server administrator > bot mods"; this can be turned off via `show_server_mods`
- Only a config admin can view the global `admins` / `mods` at the same time by using `show_global=true` when `private=true`
- If the result exceeds 2000 characters, it is sent as a `.md` file attachment

## Configuration

```yaml
perm:
  enabled: false
```

| Field | Type | Default | Description |
| --- | --- | --- |
| `enabled` | `bool` | `false` | Whether to enable the dynamic permissions module |

::: tip Permission data
Rule data is stored in `perm.yaml`. It is recommended to manage it via the `/perm` command rather than editing manually. See `perm.example.yaml` for an example.
:::
