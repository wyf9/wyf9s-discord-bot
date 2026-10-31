# 频道锁定 (lock)

锁定 / 解锁频道（禁止 `@everyone` 发言 / 加入），并支持**定时计划锁定**（单次或每日 / 每周 / 每月周期）。

- **配置键**：`lock`
- **源文件**：`cogs/lock.py`
- **数据文件**：`schedules.yaml`（计划锁定持久化，自动生成）

## 所需权限

机器人需要**管理频道**（Manage Channels）权限，且身份组层级高于要操作的频道。锁定通过设置频道对 `@everyone` 的发言 / 连接权限覆盖实现，文字频道禁止发言，语音频道额外禁止连接。

## 指令

### `/lock now` — 锁定频道

| 项目 | 说明 |
| --- | --- |
| 权限 | Mod |
| 参数 | `channel`（可选，默认当前频道） |
| 审计 | ✅ 记录（`lock`） |

- 锁定后会在频道发送 `:lock: 频道已锁定` 提示（语音频道额外提示无法加入）。
- 锁定会清除该频道已有的计划锁定记录。

### `/lock unlock` — 解锁频道

| 项目 | 说明 |
| --- | --- |
| 权限 | Mod |
| 参数 | `channel`（可选，默认当前频道） |
| 审计 | ✅ 记录（`unlock`） |

### `/lock plan` — 计划锁定 / 解锁

为频道设置定时锁定 / 解锁计划，支持单次与循环。

| 项目 | 说明 |
| --- | --- |
| 权限 | Mod |
| 审计 | ✅ 记录（`plan-lock`） |

#### 参数

| 参数 | 格式 / 说明 |
| --- | --- |
| `channel` | 目标频道（可选，默认当前频道） |
| `lock_day` | 锁定日期：`yyyy-mm-dd` / `mm-dd` / `dd` |
| `lock_time` | 锁定时间：`hh-mm`（也支持 `hh:mm`） |
| `unlock_day` | 解锁日期 |
| `unlock_time` | 解锁时间 |
| `cycle` | 循环：`daily` / `mon,tue,...` / `1,2,3` / `1-5` |
| `cycle_start` | 循环开始日期（`yyyy-mm-dd`） |
| `cycle_end` | 循环结束日期（`yyyy-mm-dd`） |

- 必须至少指定锁定或解锁时间之一。
- 时间按 **UTC+8**（东八区）解析。
- `cycle` 说明：
  - `daily`：每天
  - 星期：`mon,tue,wed,thu,fri,sat,sun`（也支持中文 `周一`…`周日`）
  - 月内日期：`1,2,3` 或范围 `1-5`
- 单次计划执行后自动清除；循环计划保留，直到超过 `cycle_end`。

#### 前缀命令 flag

```text
//lock plan --channel=#公告 --lock-time=22-00 --unlock-time=08-00 --cycle=daily
```

支持 flag：`--channel` `--lock-day` `--lock-time` `--unlock-day` `--unlock-time` `--cycle` `--cycle-start` `--cycle-end`。

### `/lock unplan` — 取消计划

取消一条已有的计划锁定。

| 项目 | 说明 |
| --- | --- |
| 权限 | Mod |
| 参数 | `index`（计划编号，斜杠命令带**自动补全**） |
| 审计 | ✅ 记录（`unplan-lock`） |

- 传入无效编号时会列出当前所有计划及编号供选择。

## 配置

```yaml
lock:
  enabled: false
  slash: true
  prefix: true
```

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enabled` | `bool` | `false` | 是否启用锁定模块 |
| `slash` | `bool` | `true` | 是否注册斜杠指令 |
| `prefix` | `bool` | `true` | 是否注册前缀指令 |

::: warning
计划锁定的执行不受调用者是否在线影响，只要机器人运行即可。计划数据保存在 `schedules.yaml`，重启后仍生效。
:::
