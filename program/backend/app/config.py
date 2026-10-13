from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import yaml

PROJECT_ROOT = Path(os.getenv("CKH_ROOT", Path(__file__).resolve().parents[3])).resolve()
PROGRAM_DIR = PROJECT_ROOT / "program"
CONFIG_DIR = PROJECT_ROOT / "config"
PRIVATE_DIR = PROJECT_ROOT / "private"
USERDATA_DIR = PROJECT_ROOT / "userdata"
DB_PATH = USERDATA_DIR / "database" / "main.sqlite3"
MEDIA_DIR = USERDATA_DIR / "media"
ARCHIVE_DIR = USERDATA_DIR / "source_archive"
LOG_DIR = USERDATA_DIR / "logs"
BACKUP_DIR = PROJECT_ROOT / "backups"
EXPORT_DIR = PROJECT_ROOT / "exports"

DIRECTORIES = [
    DB_PATH.parent, LOG_DIR, BACKUP_DIR / "automatic", BACKUP_DIR / "manual",
    USERDATA_DIR / "search_index", USERDATA_DIR / "pending_review", USERDATA_DIR / "ai_history",
    USERDATA_DIR / "templates", USERDATA_DIR / "temp", ARCHIVE_DIR,
    *[MEDIA_DIR / x for x in ("generated", "uploaded", "imported", "screenshots", "backgrounds", "thumbnails")],
    *[ARCHIVE_DIR / x for x in ("postgraduate_policies", "universities", "courses", "competitions", "webpages")],
    *[EXPORT_DIR / x for x in ("json", "csv", "markdown", "images", "full_packages")],
    PRIVATE_DIR,
]

def ensure_directories() -> None:
    for path in DIRECTORIES:
        path.mkdir(parents=True, exist_ok=True)

def read_yaml(name: str, default: Any = None) -> Any:
    path = CONFIG_DIR / name
    if not path.exists():
        return default if default is not None else {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or (default if default is not None else {})

def write_yaml(name: str, value: Any) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = CONFIG_DIR / name
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
    tmp.replace(path)

def read_private_yaml(name: str, default: Any = None) -> Any:
    path = PRIVATE_DIR / name
    if not path.exists():
        return default if default is not None else {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or (default if default is not None else {})

def write_private_yaml(name: str, value: Any) -> None:
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    path = PRIVATE_DIR / name
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf-8")
    tmp.replace(path)

def read_secrets() -> dict[str, str]:
    result: dict[str, str] = {}
    path = PRIVATE_DIR / "secrets.env"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                result[key.strip()] = value.strip()
    return result

def set_secret(key: str, value: str) -> None:
    if not key.replace("_", "").isalnum() or not key.endswith("_API_KEY"):
        raise ValueError("不允许的密钥字段")
    if "\r" in value or "\n" in value:
        raise ValueError("密钥不能包含换行符")
    secrets = read_secrets()
    secrets[key] = value.strip()
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    path = PRIVATE_DIR / "secrets.env"
    tmp = path.with_suffix(".env.tmp")
    tmp.write_text("# 仅后端读取，禁止提交或导出\n" + "\n".join(f"{k}={v}" for k, v in secrets.items()) + "\n", encoding="utf-8")
    tmp.replace(path)

