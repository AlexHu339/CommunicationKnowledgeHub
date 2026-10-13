from __future__ import annotations
import importlib.util,json,os,socket,sqlite3,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def check(name,fn):
    try:detail=fn();print(f"[通过] {name}：{detail}");return True
    except Exception as e:print(f"[失败] {name}：{e}");return False
checks=[]
checks.append(check("Python",lambda:sys.version.split()[0]))
checks.append(check("Node",lambda:subprocess.check_output(["node","--version"],text=True).strip()))
checks.append(check("SQLite",lambda:sqlite3.connect(ROOT/"userdata"/"database"/"main.sqlite3").execute("select count(*) from knowledge_cards").fetchone()[0]))
checks.append(check("OCR",lambda:"PaddleOCR 已安装" if importlib.util.find_spec("paddleocr") else (_ for _ in()).throw(RuntimeError("未安装；重新运行 setup.bat"))))
checks.append(check("Playwright",lambda:"已安装" if importlib.util.find_spec("playwright") else (_ for _ in()).throw(RuntimeError("未安装"))))
checks.append(check("API配置",lambda:"密钥文件存在（不读取、不显示内容）" if (ROOT/"private"/"secrets.env").exists() else "尚未配置；离线功能可用"))
checks.append(check("网络",lambda:socket.gethostbyname("yz.chsi.com.cn")))
print("\n诊断结论："+("核心检查通过" if checks[0] and checks[2] else "存在核心故障，请查看上方中文说明"))

