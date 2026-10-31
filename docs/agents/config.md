# Config / 配置系统

- 入口：`config.py`
- 模型根：`ConfigModel`
- 加载器：`Config`（读取 YAML、拆分 token、递归归一化键名）

## 加载顺序

1. 读取 `--config` / 默认数据目录下的 `config.yaml`。
2. 若存在 `tk.yaml` / `--token-file`，用其中的 `token` 覆盖配置。
3. `--token` / `W9DCBOT_TOKEN` 优先级最高。
4. `_normalize_config_keys()` 递归把键名中的 `-` 转为 `_`。
5. `ConfigModel.model_validate()` 做 Pydantic 校验。

## 注意

- 配置字段的“事实来源”是 `config.example.yaml`，新增字段要同步示例与文档。
- 每个业务模块通常有 `enabled` / `slash` / `prefix` 字段。
- 兼容旧字段时优先在 Pydantic 层用 `field_validator` / `model_validator(mode="before")` 处理，不要散落到业务代码。
- 旧的 `tools.ratelimit` / `emoji.ratelimit` 会迁移到顶层 `ratelimit`，见 `ratelimit.md`。
- 共享运行时状态挂在 bot 上（`bot.config`、`bot.audit`、`bot.rate_limiter`、`bot.perm_store`、`bot.lang_store`、`bot.enhance_store`、`bot.schedule_store`），Cog 重载后仍保留。
