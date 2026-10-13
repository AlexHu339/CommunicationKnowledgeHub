from __future__ import annotations
import hashlib, json, re
from datetime import datetime
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from .config import ARCHIVE_DIR, read_yaml
from .models import ReviewItem, SourceRecord

async def check_sources(db: Session, selected: list[str] | None = None) -> list[dict]:
    registry = read_yaml("source_registry.yaml", {"sources": []}).get("sources", [])
    if selected: registry=[s for s in registry if s.get("id") in selected]
    results=[]
    async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers={"User-Agent":"CommunicationKnowledgeHub/1.0 personal-study"}) as client:
        for src in registry:
            try:
                try:
                    r=await client.get(src["url"]); r.raise_for_status(); html=r.text; final_url=str(r.url)
                except Exception:
                    from playwright.async_api import async_playwright
                    async with async_playwright() as pw:
                        browser=await pw.chromium.launch(headless=True);page=await browser.new_page()
                        await page.goto(src["url"],wait_until="domcontentloaded",timeout=30000);html=await page.content();final_url=page.url;await browser.close()
                soup=BeautifulSoup(html,"html.parser")
                for x in soup(["script","style","noscript"]): x.decompose()
                text=re.sub(r"\s+"," ",soup.get_text(" ",strip=True))
                digest=hashlib.sha256(text.encode("utf-8")).hexdigest()
                previous=db.query(SourceRecord).filter_by(source_id=src["id"]).order_by(SourceRecord.id.desc()).first()
                status="无变化" if previous and previous.content_hash==digest else ("新增公告" if not previous else "正文变化")
                folder=ARCHIVE_DIR/"webpages"/src["id"]; folder.mkdir(parents=True,exist_ok=True)
                snap=folder/f"{datetime.now():%Y%m%d_%H%M%S}_{digest[:8]}.html"
                if status!="无变化": snap.write_text(html,encoding="utf-8")
                db.add(SourceRecord(source_id=src["id"],url=final_url,title=soup.title.string.strip() if soup.title and soup.title.string else src["name"],content_hash=digest,status=status,snapshot_path=str(snap) if snap.exists() else previous.snapshot_path))
                if previous and status in {"新增公告","正文变化"}:
                    db.add(ReviewItem(item_type="web_update",title=f"{src['name']}：{status}",payload_json=json.dumps({"source":src,"excerpt":text[:5000]},ensure_ascii=False),source_url=final_url,source_snapshot=str(snap),status="pending"))
                db.commit(); results.append({"id":src["id"],"name":src["name"],"status":status})
            except Exception as exc:
                db.rollback(); results.append({"id":src.get("id"),"name":src.get("name"),"status":"检查失败","error":str(exc)[:200]})
    return results
