from fastapi.testclient import TestClient
from app.main import app

def test_lan_requires_login_and_session(client):
    client.post("/api/auth/setup",json={"username":"lanuser","password":"StrongPass2028"})
    with TestClient(app,client=("192.168.1.20",50000)) as lan:
        assert lan.get("/api/dashboard").status_code==401
        login=lan.post("/api/auth/login",json={"username":"lanuser","password":"StrongPass2028"})
        if login.status_code==401:
            login=lan.post("/api/auth/login",json={"username":"learner","password":"StrongPass2028"})
        assert login.status_code==200
        token=login.json()["token"]
        assert lan.get("/api/dashboard",headers={"Authorization":f"Bearer {token}"}).status_code==200
