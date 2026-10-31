# Rate limit / 限速

- 模型：`config.py` 的 `_RateLimitConfigModel`
- 共享计算：`utils.resolve_rate_limit()`
- 滑动窗口实现：`utils.RateLimiter`
- 使用方：`cogs/tools.py`、`cogs/emoji.py`
- 测试：`tests/test_ratelimit_config.py`

## 配置形态

```yaml
ratelimit:
  enabled: true
  window: 60
  mod_multiplier: 3
  modules: { emoji: 10 }
  commands: { vc: 20, "emoji update": 5 }
```

## 解析优先级

`_RateLimitConfigModel.resolve(module, command)`：

1. `commands[完整指令名]`（如 `emoji update`、`vc join`）
2. `commands[指令名]`（如 `emoji`、`vc`）
3. `modules[module]`
4. 都没有 → 不限速

`resolve_rate_limit()` 还会处理：限速总开关、Admin 豁免、Mod 额度倍数。

## 默认值与旧配置兼容

- 完全没有配置 `ratelimit`（也没有旧版段）时，沿用旧版默认指令额度（`random` / `uuid` / `to-file` / `e` / `emoji info` 各 10）。
- 一旦显式写入顶层 `ratelimit`，只使用其中列出的 `modules` / `commands`，不再隐式继承默认指令额度。
- 顶层没有 `ratelimit` 时，根 `ConfigModel` 的 `normalize_legacy` 会把 `tools.ratelimit` / `emoji.ratelimit` 迁移为顶层命令额度。
- 直接写在顶层 `ratelimit` 下的旧式指令键（如 `random: 5`、`"2file": 3`）也会迁入 `commands`。
- 旧字段 `2file` / `to_file` → `to-file`，`emoji_info` → `emoji-info`；`emoji info` 也接受。
- 旧模块 `enabled: false` 只会移除该模块的旧指令额度，不影响其他模块。
- 顶层已存在 `ratelimit` 时以新配置为准，不再合并旧模块段。

修改限速逻辑时必须跑：

```bash
.venv/bin/python -m unittest tests.test_ratelimit_config -v
```
