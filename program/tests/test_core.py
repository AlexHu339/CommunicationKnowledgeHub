from __future__ import annotations
import zipfile
from app.database import SessionLocal
from app.models import ReviewItem

def test_health_and_exact_seed(client):
    data=client.get("/api/health").json();assert data["status"]=="ok";assert data["cards"]==406

def test_each_batch_has_eight_and_no_ai_usage(client):
    before=client.get("/api/ai/usage").json();cards=client.get("/api/cards?mode=random&limit=8").json();after=client.get("/api/ai/usage").json();assert len(cards)==8;assert before==after

def test_state_note_and_search_persist(client):
    card=client.get("/api/cards?mode=random&limit=1").json()[0];cid=card["id"]
    r=client.put(f"/api/cards/{cid}/state",json={"status":"知道怎么用","favorite":True,"viewed":True});assert r.status_code==200
    assert client.get(f"/api/cards/{cid}").json()["state"]["favorite"] is True
    n=client.post("/api/notes",json={"card_id":cid,"title":"卷积实验笔记","content":"改变输入后观察输出波形"});assert n.status_code==200
    result=client.get("/api/search?q=卷积实验笔记").json();assert len(result["notes"])==1

def test_favorites_filter(client):
    rows=client.get("/api/cards?mode=favorites&limit=100").json();assert rows;assert all(x["state"]["favorite"] for x in rows)

def test_upload_rejects_executable(client):
    r=client.post("/api/media/upload",files={"file":("bad.exe",b"MZ","application/octet-stream")});assert r.status_code==415

def test_provider_api_never_returns_key(client):
    text=client.get("/api/ai/providers").text;assert "TEST_SECRET_NOT_REAL" not in text;assert "configured" in text

def test_review_accepts_complete_card(client):
    db=SessionLocal();base=client.get("/api/cards?limit=1&mode=random").json()[0];payload={k:v for k,v in base.items() if k not in {"state","created_at"}};payload["id"]="review-test-card";payload["title"]="审核流程测试知识卡";payload["review_status"]="pending";import json
    item=ReviewItem(item_type="knowledge_card",title=payload["title"],payload_json=json.dumps(payload,ensure_ascii=False));db.add(item);db.commit();db.refresh(item);iid=item.id;db.close()
    r=client.post(f"/api/reviews/{iid}/action",json={"action":"accept","trust_level":"已人工审核"});assert r.status_code==200
    assert client.get("/api/cards/review-test-card").status_code==200

def test_backup_excludes_secrets(client):
    path=client.post("/api/backups",json={}).json()["path"]
    with zipfile.ZipFile(path) as z:assert all("secret" not in n.lower() for n in z.namelist())

def test_backup_restore_layout_and_path_safety(client):
    import os
    from pathlib import Path
    from app.backup import create_backup,restore_backup
    root=Path(os.environ["CKH_ROOT"]);sample=root/"userdata"/"media"/"uploaded"/"restore-proof.txt";sample.parent.mkdir(parents=True,exist_ok=True);sample.write_text("可恢复",encoding="utf-8")
    path=create_backup("manual","恢复自动测试")
    with zipfile.ZipFile(path) as z:assert "userdata/media/uploaded/restore-proof.txt" in z.namelist()
    sample.unlink();restore_backup(path);assert sample.read_text(encoding="utf-8")=="可恢复"
