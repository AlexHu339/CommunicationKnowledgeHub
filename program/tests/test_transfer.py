import io,json

def test_export_has_schema_and_no_secrets(client):
    r=client.post("/api/data/export/json",json={});assert r.status_code==200
    path=r.json()["path"];data=json.loads(open(path,encoding="utf-8").read());assert data["schema_version"]=="1.0";assert len(data["cards"])>=406;assert "TEST_SECRET_NOT_REAL" not in json.dumps(data)

def test_import_never_overwrites_and_queues_new(client):
    existing=client.get("/api/cards?limit=1&mode=random").json()[0];new={k:v for k,v in existing.items() if k not in {"state","created_at"}};new["id"]="safe-import-test";new["title"]="安全导入测试卡"
    package={"schema_version":"1.0","cards":[existing,new]};raw=json.dumps(package,ensure_ascii=False).encode()
    r=client.post("/api/data/import",files={"file":("cards.json",raw,"application/json")});assert r.status_code==200;body=r.json();assert body["overwritten"]==0;assert body["queued"]==1;assert len(body["conflicts"])==1
