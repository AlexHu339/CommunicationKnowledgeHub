from __future__ import annotations
import os,shutil,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
if hasattr(sys.stdout,"reconfigure"):sys.stdout.reconfigure(encoding="utf-8")
ENV=os.environ.copy();ENV.update({"PYTHONIOENCODING":"utf-8","CKH_ROOT":str(ROOT),"PYTHONPATH":str(ROOT/"program"/"backend"),"PADDLE_PDX_CACHE_HOME":str(ROOT/"runtime"/"ocr_models"),"PLAYWRIGHT_BROWSERS_PATH":str(ROOT/"runtime"/"browsers")})

def run(args:list[str],cwd:Path=ROOT,required:bool=True)->bool:
    print("\n>"," ".join(args));r=subprocess.run(args,cwd=cwd,env=ENV)
    if r.returncode and required:raise RuntimeError(f"命令失败（退出码 {r.returncode}）：{' '.join(args)}")
    return r.returncode==0

def main():
    if any(ord(c)>127 for c in str(ROOT)):raise RuntimeError("安装路径不能包含中文或特殊字符。请使用 D:\\CommunicationKnowledgeHub。")
    npm=shutil.which("npm.cmd") or shutil.which("npm")
    if not shutil.which("node") or not npm:raise RuntimeError("未找到 Node.js 20 或更高版本。")
    venv=ROOT/"runtime"/"python";py=venv/"Scripts"/"python.exe"
    if not py.exists():run([sys.executable,"-m","venv",str(venv)])
    run([str(py),"-m","pip","install","--upgrade","pip"])
    run([str(py),"-m","pip","install","-r",str(ROOT/"program"/"backend"/"requirements.txt")]);print("[1/6] 后端锁定依赖安装完成。")
    run([os.environ.get("COMSPEC","cmd.exe"),"/d","/c",npm,"install","--no-audit","--no-fund"],ROOT/"program"/"frontend")
    run([os.environ.get("COMSPEC","cmd.exe"),"/d","/c",npm,"run","build"],ROOT/"program"/"frontend");print("[2/6] 前端正式构建完成。")
    run([str(py),str(ROOT/"program"/"scripts"/"generate_seed.py")]);run([str(py),str(ROOT/"program"/"scripts"/"validate_content.py")])
    db=ROOT/"userdata"/"database"/"main.sqlite3"
    if db.exists():run([str(py),"-c","from app.backup import create_backup;print(create_backup('automatic','pre-migration'))"])
    run([str(venv/"Scripts"/"alembic.exe"),"-c",str(ROOT/"program"/"migrations"/"alembic.ini"),"upgrade","head"])
    run([str(py),str(ROOT/"program"/"scripts"/"seed_database.py")]);print("[3/6] 406 个去重后的知识主题已校验并导入。")
    ocr_ok=False
    for attempt in range(1,3):
        print(f"[4/6] OCR 安装与自检（第 {attempt}/2 次）。")
        installed=run([str(py),"-m","pip","install","-r",str(ROOT/"program"/"backend"/"requirements-ocr.txt")],required=False)
        ocr_ok=installed and run([str(py),str(ROOT/"program"/"scripts"/"ocr_smoke.py")],required=False)
        if ocr_ok:break
    if ocr_ok:print("[4/6] PaddleOCR CPU 与中文模型已配置并通过测试。")
    else:print("[警告] OCR 安装或测试未完成；其他功能可用，稍后可重试 setup.bat 或导入离线模型。")
    run([str(py),"-m","pip","check"])
    if run([str(py),"-m","playwright","install","chromium"],required=False):print("[5/6] Playwright Chromium 已配置。")
    else:print("[警告] Playwright 浏览器安装失败；普通 HTTP 更新仍可用。")
    private=ROOT/"private";private.mkdir(exist_ok=True);secrets=private/"secrets.env"
    if not secrets.exists():shutil.copy2(private/"secrets.env.example",secrets)
    (ROOT/"runtime"/"install-root.txt").write_text(str(ROOT),encoding="utf-8");(ROOT/"runtime"/"node-path.txt").write_text(shutil.which("node") or "",encoding="utf-8")
    print("[6/6] 安装完成。未填写真实 API Key 是正常状态；首次启动进入可视化向导。")

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print(f"\n[错误] 安装未完成：{exc}");raise SystemExit(1)
