from __future__ import annotations
import hashlib,json,zipfile
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"CommunicationKnowledgeHub_v1.0.0.zip"
include_roots=[ROOT/"program",ROOT/"config",ROOT/"docs"]
private_files=[ROOT/"private"/"README_PRIVATE.txt",ROOT/"private"/"secrets.env.example"]
root_files=["setup.bat","start.bat","stop.bat","update_sources.bat","backup.bat","restore.bat","diagnose.bat","README_FIRST.txt","README.md","CHANGELOG.md","VERSION",".gitignore"]
excluded={"node_modules","__pycache__",".pytest_cache",".venv"};manifest={"version":"1.0.0","built_at":datetime.now().isoformat(),"files":{}}
empty_dirs=["runtime/python","runtime/ocr_models","runtime/browsers","runtime/node","runtime/cache","userdata/database","userdata/media/generated","userdata/media/uploaded","userdata/media/imported","userdata/media/screenshots","userdata/media/backgrounds","userdata/media/thumbnails","userdata/source_archive/postgraduate_policies","userdata/source_archive/universities","userdata/source_archive/courses","userdata/source_archive/competitions","userdata/source_archive/webpages","userdata/search_index","userdata/pending_review","userdata/ai_history","userdata/templates","userdata/logs","userdata/temp","backups/automatic","backups/manual","exports/json","exports/csv","exports/markdown","exports/images","exports/full_packages"]
with zipfile.ZipFile(OUT,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    files=[]
    for base in include_roots:
        for p in base.rglob("*"):
            if not p.is_file() or any(x in excluded for x in p.parts):continue
            if p.name=="secrets.env":continue
            if "frontend" in p.parts and "dist" not in p.parts and any(x in p.parts for x in [".vite"]):continue
            files.append(p)
    files += [p for p in private_files if p.exists()]
    files += [ROOT/x for x in root_files if (ROOT/x).exists()]
    for p in sorted(set(files)):
        arc=p.relative_to(ROOT).as_posix();data=p.read_bytes();z.writestr(arc,data);manifest["files"][arc]=hashlib.sha256(data).hexdigest()
    for d in empty_dirs:z.writestr(d.rstrip("/")+"/",b"")
    z.writestr("RELEASE_MANIFEST.json",json.dumps(manifest,ensure_ascii=False,indent=2))
print(f"packaged {len(manifest['files'])} files -> {OUT.name}")
