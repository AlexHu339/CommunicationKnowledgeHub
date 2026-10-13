def test_local_access_without_login(client):assert client.get("/api/dashboard").status_code==200
def test_password_setup_uses_hash(client):
    r=client.post("/api/auth/setup",json={"username":"learner","password":"StrongPass2028"});assert r.status_code in {200,409}
    from app.database import SessionLocal
    from app.models import UserAccount
    db=SessionLocal();u=db.query(UserAccount).first();assert u and "StrongPass2028" not in u.password_hash and u.password_hash.startswith("$argon2");db.close()

