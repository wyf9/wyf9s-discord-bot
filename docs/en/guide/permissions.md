# Permission system

This bot uses a **multi-layered custom permission** system (not Discord's built-in role permissions), implemented in `utils.py`. It supports two sources, `config.yaml` + `perm.yaml`, with `config.yaml` always taking precedence.

## Permission tiers

| Tier | Basis | Description |
| --- | --- | --- |
| **Admin** | `config.yaml > admins.users` | Only the admins defined in the config file; has all permissions |
| **Mod** | Server `administrator` + `mods.users` + `mods.guilds` + dynamic permissions | Mod commands + rate-limit exemption |

### Inclusion relationships

```text
config admins   →  Admin (all permissions)
server admins   →  Mod (mod command permissions, excluding admin-only)
config mods     →  Mod
perm.yaml       →  Mod (appended dynamic rules)
```

- **Admin** = only the `admins.users` list
- **Mod** = server admins + config admins + config mods + `perm.yaml` dynamic rules

Admin commands such as `/sync`, `/reload`, and `/emoji update` are **only available to config admins**; server admins cannot use them.

## List matching rules

Each entry in `admins.users` / `mods.users` / `mods.guilds.<server>.users` can be:

- A **user ID** (a number, e.g. `123456789012345678`)
- A **username** (a string, e.g. `"wyf9"`)
- A numeric string is also matched as an ID

Each entry in `mods.guilds.<server>.roles` can be:

- A **role ID** (a number)
- A **role name** (a string, e.g. `"Moderator"`)
- A numeric string is also matched as an ID

```python
def matches_identity(user, values):
    for value in values:
        if user.id == value or user.name == value:
            return True
        if isinstance(value, str) and value.isdigit() and user.id == int(value):
            return True
    return False


def matches_role(member, values):
    for value in values:
        for role in member.roles:
            if role.id == value or role.name == value:
                return True
            if isinstance(value, str) and value.isdigit() and role.id == int(value):
                return True
    return False
```

The legacy format of `mods.guilds` (a plain user list) is still supported and is equivalent to configuring only `users`.

::: warning
Username matching is based on the Discord global username (`user.name`), not the server nickname (`display_name`). It is recommended to prefer **user IDs / role IDs** to avoid ambiguity.
:::

## Declarative permission control

A command's handler method declares the required permission level via the `@u.requires(...)` decorator:

```python
@u.requires(u.Permission.MOD)
async def _handle_lock(self, source, channel=None): ...
```

The `Permission` level enum:

| Level | Meaning |
| --- | --- |
| `Permission.EVERYONE` | Available to everyone |
| `Permission.MOD` | Requires mod (includes admin) |
| `Permission.ADMIN` | Requires admin (server admin / config admin) |

It also supports passing a **custom decision function** `(module, user, guild) -> bool`, such as the allowlist check of the [Voice module](/en/modules/voice).

When a permission check fails, the bot replies with `:x: **You don't have permission to use this command** :x:` (a temporary message deleted after 10 seconds) and aborts execution.

## Quick reference of required permissions per command

| Command | Required permission |
| --- | --- |
| `random` / `uuid` / `to-file` | Everyone (subject to [rate limiting](/en/guide/rate-limit)) |
| `/e` / `/emoji info` | Everyone (subject to rate limiting) |
| `delete` / `clear-message` / `move-channel` | Mod |
| `/lock now` / `/lock unlock` / `/lock plan` / `/lock unplan` | Mod |
| `/vc join` / `/vc leave` | Allowlisted user or Mod (see [Voice module](/en/modules/voice)) |
| `/emoji update` | Admin (config admins only) |
| `/sync` | Admin (config admins only) |
| `/reload` | Admin (config admins only) |
| `/perm add` / `/perm rm` / `/perm show` | Admin (config admins only) |

::: tip Global rate limit
All commands have a global rate-limit fallback of 10 reqs / 10s. Admins are not subject to rate limiting.
:::
