# 权限系统

本机器人使用**多层自定义权限**（非 Discord 内置角色权限），在 `utils.py` 中实现。支持 `config.yaml` + `perm.yaml` 双重来源，`config.yaml` 始终优先。

## 权限层级

| 层级 | 判定依据 | 说明 |
| --- | --- | --- |
| **Admin** | `config.yaml > admins.users` | 仅限配置文件中定义的管理员，拥有全部权限 |
| **Mod** | 服务器 `administrator` + `mods.users` + `mods.guilds` + 动态权限 | mod 命令 + 限速豁免 |

### 包含关系

```text
config admins   →  Admin (所有权限)
服务器管理员    →  Mod (mod 命令权限，不含 admin 专属)
config mods     →  Mod
perm.yaml       →  Mod (动态规则追加)
```

- **Admin** = 仅限 `admins.users` 名单
- **Mod** = 服务器管理员 + config admins + config mods + perm.yaml 动态规则

`/sync`、`/reload`、`/emoji update` 等 Admin 命令**仅 config admins 可用**，服务器管理员无法使用。

## 名单匹配规则

`admins.users` / `mods.users` / `mods.guilds.<server>.users` 中的每一项可以是：

- **用户 ID**（数字，如 `123456789012345678`）
- **用户名**（字符串，如 `"wyf9"`）
- 数字字符串同样按 ID 匹配

`mods.guilds.<server>.roles` 中的每一项可以是：

- **身份组 ID**（数字）
- **身份组名称**（字符串，如 `"Moderator"`）
- 数字字符串同样按 ID 匹配

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

`mods.guilds` 的旧格式（直接写用户列表）仍然兼容，等同于只配置 `users`。

::: warning
用户名匹配基于 Discord 全局用户名（`user.name`），并非服务器昵称（`display_name`）。推荐优先使用**用户 ID / 身份组 ID** 以避免歧义。
:::

## 声明式权限控制

指令的处理方法通过 `@u.requires(...)` 装饰器声明所需权限等级：

```python
@u.requires(u.Permission.MOD)
async def _handle_lock(self, source, channel=None): ...
```

权限等级枚举 `Permission`：

| 等级 | 含义 |
| --- | --- |
| `Permission.EVERYONE` | 所有人可用 |
| `Permission.MOD` | 需要 mod（含 admin） |
| `Permission.ADMIN` | 需要 admin（服务器管理员 / 配置管理员） |

也支持传入**自定义判定函数** `(module, user, guild) -> bool`，例如[语音模块](/modules/voice)的白名单判定。

当权限不通过时，机器人会回复 `:x: 你没有权限使用此指令 :x:`（临时消息，10 秒后删除）并中止执行。

## 各指令所需权限速查

| 指令 | 所需权限 |
| --- | --- |
| `random` / `uuid` / `to-file` | 所有人（受[限速](/guide/rate-limit)） |
| `/e` / `/emoji info` | 所有人（受限速） |
| `delete` / `clear-message` / `move-channel` | Mod |
| `/lock now` / `/lock unlock` / `/lock plan` / `/lock unplan` | Mod |
| `/vc join` / `/vc leave` | 白名单用户或 Mod（见[语音模块](/modules/voice)） |
| `/emoji update` | Admin（仅 config admins） |
| `/sync` | Admin（仅 config admins） |
| `/reload` | Admin（仅 config admins） |
| `/perm add` / `/perm rm` / `/perm show` | Admin（仅 config admins） |

::: tip 全局限速
所有指令均有 10reqs / 10s 全局限速 fallback。Admin 不受限速。
:::
