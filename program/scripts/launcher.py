from __future__ import annotations

import json
import msvcrt
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn
import yaml

ROOT=Path(__file__).resolve().parents[2]
cfg=yaml.safe_load((ROOT/"config"/"app.yaml").read_text(encoding="utf-8"))
state=ROOT/"runtime"/"app-state.json"
lock_path=ROOT/"runtime"/"launcher.lock"
state.parent.mkdir(parents=True,exist_ok=True)


def healthy_url() -> str | None:
    if not state.exists():
        return None
    try:
        running=json.loads(state.read_text(encoding="utf-8"))
        url=running["local_url"]
        with urllib.request.urlopen(url+"/api/health",timeout=1) as response:
            return url if response.status==200 else None
    except Exception:
        return None


def open_if_allowed(url:str) -> None:
    if os.getenv("CKH_NO_BROWSER")!="1":
        webbrowser.open(url)


lock_file=lock_path.open("a+b")
lock_file.seek(0,os.SEEK_END)
if lock_file.tell()==0:
    lock_file.write(b"0");lock_file.flush()
lock_file.seek(0)
try:
    msvcrt.locking(lock_file.fileno(),msvcrt.LK_NBLCK,1)
except OSError:
    for _ in range(120):
        url=healthy_url()
        if url:
            print(f"通信工程知识枢纽正在启动或已经运行：{url}")
            open_if_allowed(url)
            raise SystemExit(0)
        time.sleep(.1)
    raise SystemExit("错误：另一个启动过程长时间未就绪，请运行 stop.bat 后重试。")

url=healthy_url()
if url:
    print(f"通信工程知识枢纽已经在运行：{url}")
    open_if_allowed(url)
    raise SystemExit(0)
if state.exists():
    state.unlink(missing_ok=True)

settings={}
try:
    import sqlite3
    db=sqlite3.connect(ROOT/"userdata"/"database"/"main.sqlite3")
    settings=dict(db.execute("select key,value from app_settings").fetchall())
    db.close()
except Exception:
    pass

host="0.0.0.0" if settings.get("lan_enabled",str(cfg.get("lan_enabled",False))).lower()=="true" else "127.0.0.1"
preferred=int(cfg.get("preferred_port",8765));port=preferred
while port<preferred+100:
    with socket.socket() as probe:
        try:
            probe.bind((host,port));break
        except OSError:
            port+=1
if port>=preferred+100:
    raise SystemExit("错误：8765—8864 端口均被占用。")

local=f"http://127.0.0.1:{port}";lan=[]
if host=="0.0.0.0":
    try:
        name=socket.gethostname()
        lan=[f"http://{address}:{port}" for address in socket.gethostbyname_ex(name)[2] if not address.startswith("127.")]
    except Exception:
        pass


def publish_when_ready() -> None:
    for _ in range(120):
        try:
            with urllib.request.urlopen(local+"/api/health",timeout=.3) as response:
                if response.status==200:
                    payload={"pid":os.getpid(),"server_pid":os.getpid(),"host":host,"port":port,"local_url":local,"lan_urls":lan}
                    state.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
                    print(f"通信工程知识枢纽已启动：{local}",flush=True)
                    for address in lan:
                        print(f"局域网手机地址（需要登录）：{address}",flush=True)
                    open_if_allowed(local)
                    return
        except Exception:
            time.sleep(.1)
    print("错误：后端服务未能在 12 秒内启动，请运行 diagnose.bat 并查看 userdata/logs。",file=sys.stderr,flush=True)


publisher=threading.Thread(target=publish_when_ready,daemon=True)
publisher.start()
try:
    uvicorn.run("app.main:app",host=host,port=port,app_dir=str(ROOT/"program"/"backend"),log_level="info",access_log=False)
finally:
    try:
        current=json.loads(state.read_text(encoding="utf-8"))
        if current.get("pid")==os.getpid():
            state.unlink(missing_ok=True)
    except Exception:
        pass
    try:
        lock_file.seek(0);msvcrt.locking(lock_file.fileno(),msvcrt.LK_UNLCK,1)
    except OSError:
        pass
    lock_file.close()
