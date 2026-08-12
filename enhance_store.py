from pathlib import Path

from loguru import logger as l
from yaml import safe_dump, safe_load

import utils as u

_ENHANCE_FILE_NAME = "enhance_settings.yaml"


class EnhanceStore:
    """
    聊天增强模块的服务器级功能开关存储

    每个服务器独立控制各聊天增强功能 (如 autofixupx) 是否启用, 默认全部禁用,
    由服务器管理员通过 /enhance enable 显式启用.
    """

    def __init__(self):
        self._guild_functions: dict[int, set[str]] = {}
        self._load()

    def _load(self):
        read_path = u.get_data_path(_ENHANCE_FILE_NAME, for_read=True)
        if Path(read_path).exists():
            try:
                with open(read_path, "r", encoding="utf-8") as f:
                    data = safe_load(f) or {}
                raw_guilds = data.get("guilds", {}) or {}
                self._guild_functions = {
                    int(gid): set(funcs) for gid, funcs in raw_guilds.items()
                }
                total = sum(len(v) for v in self._guild_functions.values())
                l.debug(
                    f"[enhance] Loaded {len(self._guild_functions)} guilds / "
                    f"{total} enabled functions"
                )
            except Exception as e:
                l.warning(f"[enhance] Failed to load enhance settings: {e}")
                self._guild_functions = {}

    def _save(self):
        write_path = u.get_data_path(_ENHANCE_FILE_NAME)
        try:
            data = {
                "guilds": {
                    str(gid): sorted(funcs)
                    for gid, funcs in self._guild_functions.items()
                }
            }
            with open(write_path, "w", encoding="utf-8") as f:
                safe_dump(data, f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            raise RuntimeError(f"Cannot write to {write_path}: {e}")

    def is_enabled(self, guild_id: int, function: str) -> bool:
        """检查指定服务器的功能是否已启用"""
        return function in self._guild_functions.get(guild_id, set())

    def enable(self, guild_id: int, function: str) -> bool:
        """启用功能, 返回是否有变化"""
        funcs = self._guild_functions.setdefault(guild_id, set())
        if function in funcs:
            return False
        funcs.add(function)
        self._save()
        return True

    def disable(self, guild_id: int, function: str) -> bool:
        """禁用功能, 返回是否有变化"""
        funcs = self._guild_functions.get(guild_id)
        if funcs and function in funcs:
            funcs.discard(function)
            if not funcs:
                del self._guild_functions[guild_id]
            self._save()
            return True
        return False

    def list_enabled(self, guild_id: int) -> list[str]:
        """返回指定服务器已启用的功能列表"""
        return sorted(self._guild_functions.get(guild_id, set()))
