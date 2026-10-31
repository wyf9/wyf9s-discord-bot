# 动态权限 (perm)

通过 `/perm` 指令管理动态权限规则，存储于 `perm.yaml`。`config.yaml` 中的配置始终优先。

- **配置键**：`perm`
- **源文件**：`cogs/perm.py`、`perm.py`
- **数据文件**：`perm.yaml`

## 规则粒度

动态权限作为 `config.yaml` 中 `mods` / `admins` 的**补充**，`config.yaml` 始终优先（其规则在 `/perm show` 中显示为 :lock:）。规则可授予三种粒度：

- **单个模块**（`module`）：该模块下的所有指令。
- **单个指令**（`command`）：仅该指令。
- **mod 权限**（`module` 与 `command` 都不填）：等同于 `config.yaml` 的 `mods` 名单，授予**所有 mod 级指令**（`/lock`、`/vc`、`/move-channel`…）。

## 指令

`/perm` 拆分为三个子指令：`/perm add`、`/perm rm`、`/perm show`。

### `/perm add` — 添加规则

| 项目 | 说明 |
| --- | --- |
| 权限 | Admin（config admins）或服务器管理员（仅限 server scope） |
| 参数 | `user` / `role`（二选一必填）、`module`（支持下拉自动补全）/ `command`（二选一，**都不填 = 授予 mod 权限**）、`global`（bool 选项）、`private`（bool 选项） |

- **不指定 `module` 与 `command`** 时，授予该用户或身份组「mod 权限」——效果等同配置文件 `mods` 名单，所有 mod 级指令均可用。
- 服务器管理员仅可添加 `global=False` 的规则。

### `/perm rm` — 删除规则

| 项目 | 说明 |
| --- | --- |
| 权限 | Admin 或服务器管理员 |
| 参数 | `rid`（规则 ID）或 `user` / `role` / `module` / `command` 组合筛选 |

### `/perm show` — 查看规则

| 项目 | 说明 |
| --- | --- |
| 权限 | Admin 或服务器管理员 |
| 参数 | `user`、`role`、`module`、`command`（可选筛选）、`scope`（`server` / `global` 选项）、`private`、`show_server_mods`、`show_global` |

- 默认显示因服务器拥有者、服务器管理员、bot mods 身份而天然拥有 mod 权限的成员，顺序为「拥有者 > 服务器管理员 > bot mods」，可通过 `show_server_mods` 关闭
- 仅 config admin 可在 `private=true` 时通过 `show_global=true` 同时查看全局 `admins` / `mods`
- 结果超过 2000 字符时以 `.md` 文件附件发送

## 配置

```yaml
perm:
  enabled: false
```

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enabled` | `bool` | `false` | 是否启用动态权限模块 |

::: tip 权限数据
规则数据存储在 `perm.yaml` 中，建议通过 `/perm` 指令管理而非手动编辑。示例见 `perm.example.yaml`。
:::
