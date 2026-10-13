from __future__ import annotations

import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"program"/"backend"))
from app.backup import restore_backup

if len(sys.argv)<2:raise SystemExit("用法：restore_backup.py <备份zip>")
try:
    current=restore_backup(Path(sys.argv[1]))
except Exception as exc:
    raise SystemExit(str(exc)) from exc
print("当前状态已备份：",current)
print("恢复完成。")
