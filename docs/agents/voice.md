# Voice Cog

- 文件：`cogs/voice.py`
- 配置：`voicechannel.*`
- 指令：`/vc join`、`/vc leave`
- 权限：`_voice_permission`（白名单用户 → 服务器白名单 → Mod）
- 限速：`_handle_joinvc` / `_handle_leavevc` 入口调用 `u.check_rate_limit()`，模块名 `voicechannel`，指令 `vc join` / `vc leave`

## 行为

- join 会 self-deaf + self-mute；已有连接会先断开再移动。
- 断线自动重连，指数退避，上限 `reconnect_max_delay`。
- `persist=true` 的会话写入 `voice.yaml`，重启后恢复。
- `/vc leave` 标记主动离开，不再重连。

## 注意

- DAVE 加密连接失败（4017）要给出明确提示。
- 重连任务要避免重复启动，注意 `_reconnecting` / `_intentional_disconnect` 状态。
- 修改连接逻辑后检查 `cog_unload` 是否清理任务。
