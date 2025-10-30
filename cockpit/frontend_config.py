import json
import os
from typing import Dict, Any


# 统一前端配置文件路径改为 cockpit 目录
CONFIG_PATH = os.path.join("cockpit", "ui_config.json")
OLD_CONFIG_PATH = os.path.join("assets", "user", "ui_config.json")


def _defaults() -> Dict[str, Any]:
    return {
        "title": "Fusion Cockpit",
        "logo_path": "assets/user/logo.png",
        "background_path": "assets/user/bg.jpg",
        "background_enabled": False,
        # OBS 输出配置
        "obs_enabled": False,
        "obs_url": "http://localhost:8000/obs/push",
    }


def ensure_config_file() -> None:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        return
    # 迁移旧路径配置
    if os.path.exists(OLD_CONFIG_PATH):
        try:
            with open(OLD_CONFIG_PATH, "r", encoding="utf-8") as f:
                older = json.load(f)
        except Exception:
            older = {}
        merged = _defaults()
        merged.update({k: v for k, v in older.items() if k in merged})
        save_config(merged)
        return
    # 不存在则创建默认
    save_config(_defaults())


def load_config() -> Dict[str, Any]:
    """Load UI config, merging with defaults for missing keys."""
    ensure_config_file()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    # merge defaults
    merged = _defaults()
    merged.update({k: v for k, v in data.items() if k in merged})
    return merged


def save_config(cfg: Dict[str, Any]) -> None:
    """Persist config atomically to avoid partial writes."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    tmp_path = CONFIG_PATH + ".tmp"
    # only persist known keys
    data = _defaults()
    data.update({k: v for k, v in cfg.items() if k in data})
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, CONFIG_PATH)