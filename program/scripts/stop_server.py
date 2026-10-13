from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "runtime" / "app-state.json"


def main() -> int:
    if not STATE.exists():
        print("程序当前未运行。")
        return 0
    try:
        pid = int(json.loads(STATE.read_text(encoding="utf-8"))["pid"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"[错误] 无法读取进程状态：{exc}")
        return 1
    result = subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
        check=False,
    )
    STATE.unlink(missing_ok=True)
    if result.returncode not in (0, 128):
        print(f"[错误] 关闭失败：{result.stderr.strip() or result.stdout.strip()}")
        return result.returncode
    if result.returncode == 128:
        print("未找到对应进程，已清理过期状态文件。")
    else:
        print("通信工程知识枢纽已可靠关闭。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
