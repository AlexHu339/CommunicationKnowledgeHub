from __future__ import annotations
from datetime import datetime
import hashlib, json, shutil, sqlite3, tempfile, zipfile
from pathlib import Path
from .config import PROJECT_ROOT, DB_PATH, USERDATA_DIR, CONFIG_DIR, BACKUP_DIR, LOG_DIR

def create_backup(kind: str = "manual", reason: str = "用户手动备份") -> Path:
    target_dir = BACKUP_DIR / ("automatic" if kind == "automatic" else "manual")
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = target_dir / f"ckh_{stamp}.zip"
    temp_db = USERDATA_DIR / "temp" / f"backup_{stamp}.sqlite3"
    temp_db.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        src = sqlite3.connect(DB_PATH); dst = sqlite3.connect(temp_db)
        src.backup(dst); dst.close(); src.close()
    manifest = {"version":"1.0.0","created_at":datetime.now().isoformat(),"reason":reason,"files":{}}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        candidates = []
        if temp_db.exists(): candidates.append((temp_db, "userdata/database/main.sqlite3"))
        for root in [USERDATA_DIR / "media", USERDATA_DIR / "source_archive", USERDATA_DIR / "templates", CONFIG_DIR]:
            if root.exists():
                candidates += [(p, p.relative_to(PROJECT_ROOT).as_posix()) for p in root.rglob("*") if p.is_file()]
        for p, arc in candidates:
            data = p.read_bytes(); manifest["files"][arc] = hashlib.sha256(data).hexdigest(); z.writestr(arc, data)
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    temp_db.unlink(missing_ok=True)
    if kind=="automatic":cleanup_automatic_backups()
    return out

def cleanup_automatic_backups() -> None:
    folder=(BACKUP_DIR/"automatic").resolve();files=sorted(folder.glob("ckh_*.zip"),key=lambda p:p.stat().st_mtime,reverse=True);keep=set(files[:30]);months=set()
    for p in files:
        month=datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m")
        if month not in months and len(months)<12:months.add(month);keep.add(p)
    removed=[]
    for p in files:
        resolved=p.resolve()
        if p not in keep and folder in resolved.parents:resolved.unlink();removed.append(p.name)
    if removed:
        LOG_DIR.mkdir(parents=True,exist_ok=True)
        with (LOG_DIR/"backup-cleanup.log").open("a",encoding="utf-8") as f:f.write(f"{datetime.now().isoformat()} removed={','.join(removed)}\n")

def verify_backup(path: Path) -> tuple[bool, list[str]]:
    errors=[]
    with zipfile.ZipFile(path) as z:
        manifest=json.loads(z.read("manifest.json"))
        for name, expected in manifest["files"].items():
            if hashlib.sha256(z.read(name)).hexdigest()!=expected: errors.append(name)
    return not errors, errors

def restore_backup(path: Path) -> Path:
    path=path.resolve();ok,errors=verify_backup(path)
    if not ok:raise ValueError("备份完整性校验失败："+",".join(errors))
    current=create_backup("automatic","恢复前自动备份")
    allowed_exact={"userdata/database/main.sqlite3"};allowed_dirs=("userdata/media/","userdata/source_archive/","userdata/templates/","config/")
    with tempfile.TemporaryDirectory(prefix="ckh_restore_") as td:
        temp=Path(td).resolve()
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                name=info.filename.replace("\\","/")
                if name=="manifest.json" or info.is_dir():continue
                if name not in allowed_exact and not any(name.startswith(prefix) for prefix in allowed_dirs):raise ValueError(f"备份包含不允许的路径：{name}")
                target=(temp/name).resolve()
                if temp not in target.parents:raise ValueError(f"备份包含路径穿越：{name}")
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(info))
        db=temp/"userdata"/"database"/"main.sqlite3"
        if db.exists():DB_PATH.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(db,DB_PATH)
        for rel in (Path("userdata/media"),Path("userdata/source_archive"),Path("userdata/templates"),Path("config")):
            src=temp/rel;dst=PROJECT_ROOT/rel
            if src.exists():shutil.copytree(src,dst,dirs_exist_ok=True)
    return current
