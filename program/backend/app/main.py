from __future__ import annotations
from datetime import datetime, date, timedelta
import base64, hashlib, json, mimetypes, secrets, shutil, uuid
from io import BytesIO
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import csv
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session
from argon2.exceptions import VerifyMismatchError
from PIL import Image

from . import models, schemas
from .ai import safe_providers, list_models, chat, capability_probe, AiError
from .backup import create_backup, verify_backup
from .config import *
from .database import Base, engine, get_db, SessionLocal
from .ocr import run_ocr
from .security import require_access, is_loopback, ph, create_session, hash_token
from .source_updater import check_sources
from .web_search import search_context, search_public_web

ensure_directories(); Base.metadata.create_all(engine)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
_scheduler=AsyncIOScheduler()
async def _scheduled_update():
    db=SessionLocal()
    try:
        due=[]
        for src in read_yaml("source_registry.yaml",{"sources":[]}).get("sources",[]):
            last=db.query(models.SourceRecord).filter_by(source_id=src["id"]).order_by(models.SourceRecord.checked_at.desc()).first()
            if not last or last.checked_at+timedelta(hours=int(src.get("interval_hours",168)))<=datetime.utcnow():due.append(src["id"])
        if due:await check_sources(db,due)
    finally:db.close()
@asynccontextmanager
async def lifespan(_app:FastAPI):
    if not _scheduler.running:
        _scheduler.add_job(_scheduled_update,"interval",hours=6,next_run_time=datetime.now()+timedelta(minutes=1),id="source_update",replace_existing=True,max_instances=1)
        _scheduler.start()
    yield
    if _scheduler.running:_scheduler.shutdown(wait=False)

app=FastAPI(title="通信工程知识地图",version="1.0.0",docs_url="/api/docs",lifespan=lifespan)
cfg=read_yaml("app.yaml",{})
app.add_middleware(CORSMiddleware,allow_origins=cfg.get("allowed_origins",["http://127.0.0.1:5173","http://localhost:5173"]),allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

def card_dict(c, state=None):
    data={x.name:getattr(c,x.name) for x in c.__table__.columns}
    try:data["sections"]=json.loads(c.sections_json or "[]")
    except (TypeError,json.JSONDecodeError):data["sections"]=[]
    try:data["accuracy_notes"]=json.loads(c.accuracy_notes_json or "[]")
    except (TypeError,json.JSONDecodeError):data["accuracy_notes"]=[]
    data["state"]={x.name:getattr(state,x.name) for x in state.__table__.columns} if state else {"status":"未接触","favorite":False,"view_count":0}
    return data

def canonical_card_id(card_id:str,db:Session)->str:
    alias=db.get(models.KnowledgeCardAlias,card_id)
    return alias.canonical_id if alias else card_id

def ensure_daily_backup(db:Session):
    key="last_daily_backup";row=db.get(models.AppSetting,key);today=date.today().isoformat()
    if not row or row.value!=today:
        create_backup("automatic","每日首次有效数据修改前")
        if not row:row=models.AppSetting(key=key,value=today);db.add(row)
        else:row.value=today

@app.get("/api/health")
def health(request:Request,db:Session=Depends(get_db)):
    return {"status":"ok","version":"1.0.0","mode":"local" if is_loopback(request) else "lan","database_ready":DB_PATH.exists(),"cards":db.query(models.KnowledgeCard).filter_by(review_status="approved").count(),"ocr_available":__import__("importlib").util.find_spec("paddleocr") is not None,"setup_complete":db.get(models.AppSetting,"setup_complete") is not None}

@app.get("/api/dashboard",dependencies=[Depends(require_access)])
def dashboard(db:Session=Depends(get_db)):
    return {"cards":db.query(models.KnowledgeCard).filter_by(review_status="approved").count(),"subjects":db.query(models.KnowledgeCard.subject).distinct().count(),"viewed":db.query(models.LearningState).filter(models.LearningState.view_count>0).count(),"mastered":db.query(models.LearningState).filter_by(status="掌握").count(),"reviews_due":db.query(models.LearningState).filter(or_(models.LearningState.status=="需要复习",models.LearningState.review_date<=date.today())).count(),"favorites":db.query(models.LearningState).filter_by(favorite=True).count(),"pending":db.query(models.ReviewItem).filter_by(status="pending").count()}

@app.get("/api/subjects",dependencies=[Depends(require_access)])
def subjects(db:Session=Depends(get_db)):
    rows=db.query(models.KnowledgeCard.subject,func.count()).filter_by(review_status="approved").group_by(models.KnowledgeCard.subject).all(); return [{"name":x,"count":n} for x,n in rows]

@app.get("/api/cards",dependencies=[Depends(require_access)])
def cards(subject:str|None=None,mode:str="new",limit:int=8,offset:int=0,db:Session=Depends(get_db)):
    limit=max(1,min(limit,100)); q=db.query(models.KnowledgeCard).outerjoin(models.LearningState,models.KnowledgeCard.id==models.LearningState.card_id).filter(models.KnowledgeCard.review_status=="approved")
    if subject:q=q.filter(models.KnowledgeCard.subject==subject)
    if mode=="new":q=q.filter(or_(models.LearningState.card_id==None,models.LearningState.view_count==0)).order_by(func.random())
    elif mode=="consolidate":q=q.filter(models.LearningState.view_count>0,models.LearningState.status.notin_(["掌握"])).order_by(models.LearningState.last_viewed_at.asc())
    elif mode=="review":q=q.filter(or_(models.LearningState.status=="需要复习",models.LearningState.review_date<=date.today())).order_by(models.LearningState.review_date.asc())
    elif mode=="competition":q=q.filter(or_(models.KnowledgeCard.competition_relevant==True,models.LearningState.competition_use==True)).order_by(func.random())
    elif mode=="favorites":q=q.filter(models.LearningState.favorite==True).order_by(models.LearningState.updated_at.desc())
    else:q=q.order_by(func.random())
    result=[]
    for c in q.offset(offset).limit(limit).all(): result.append(card_dict(c,db.get(models.LearningState,c.id)))
    return result

@app.get("/api/cards/{card_id}",dependencies=[Depends(require_access)])
def card_detail(card_id:str,db:Session=Depends(get_db)):
    card_id=canonical_card_id(card_id,db);c=db.get(models.KnowledgeCard,card_id)
    if not c or c.review_status!="approved":raise HTTPException(404,"知识卡不存在")
    rels=db.query(models.Relationship).filter(or_(models.Relationship.source_id==card_id,models.Relationship.target_id==card_id)).all()
    data=card_dict(c,db.get(models.LearningState,card_id)); data["relationships"]=[{"source_id":r.source_id,"target_id":r.target_id,"type":r.relation_type} for r in rels]; data["notes"]=[{"id":n.id,"title":n.title,"content":n.content,"updated_at":n.updated_at} for n in db.query(models.Note).filter_by(card_id=card_id).all()]; return data

@app.put("/api/cards/{card_id}/state",dependencies=[Depends(require_access)])
def update_state(card_id:str,payload:schemas.StateUpdate,db:Session=Depends(get_db)):
    card_id=canonical_card_id(card_id,db)
    if not db.get(models.KnowledgeCard,card_id):raise HTTPException(404,"知识卡不存在")
    ensure_daily_backup(db);row=db.get(models.LearningState,card_id) or models.LearningState(card_id=card_id); db.add(row)
    for k,v in payload.model_dump(exclude_none=True,exclude={"viewed"}).items():setattr(row,k,v)
    if payload.viewed: row.view_count=(row.view_count or 0)+1; row.last_viewed_at=datetime.utcnow()
    db.commit(); return {x.name:getattr(row,x.name) for x in row.__table__.columns}

@app.get("/api/notes",dependencies=[Depends(require_access)])
def notes(q:str|None=None,db:Session=Depends(get_db)):
    query=db.query(models.Note); query=query.filter(or_(models.Note.title.contains(q),models.Note.content.contains(q))) if q else query; return [{x.name:getattr(n,x.name) for x in n.__table__.columns} for n in query.order_by(models.Note.updated_at.desc()).all()]

@app.post("/api/notes",dependencies=[Depends(require_access)])
def add_note(p:schemas.NoteInput,db:Session=Depends(get_db)):
    ensure_daily_backup(db);n=models.Note(**p.model_dump());db.add(n);db.commit();db.refresh(n);return {"id":n.id}

@app.put("/api/notes/{note_id}",dependencies=[Depends(require_access)])
def edit_note(note_id:int,p:schemas.NoteInput,db:Session=Depends(get_db)):
    n=db.get(models.Note,note_id)
    if not n:raise HTTPException(404,"笔记不存在")
    ensure_daily_backup(db)
    for k,v in p.model_dump().items():setattr(n,k,v)
    db.commit();return {"ok":True}

@app.delete("/api/notes/{note_id}",dependencies=[Depends(require_access)])
def delete_note(note_id:int,db:Session=Depends(get_db)):
    n=db.get(models.Note,note_id)
    if n:db.delete(n);db.commit()
    return {"ok":True}

@app.get("/api/search",dependencies=[Depends(require_access)])
def search(q:str,limit:int=50,db:Session=Depends(get_db)):
    term=f"%{q.strip()}%"; cards=db.query(models.KnowledgeCard).filter(models.KnowledgeCard.review_status=="approved",or_(models.KnowledgeCard.title.like(term),models.KnowledgeCard.summary.like(term),models.KnowledgeCard.keywords.like(term),models.KnowledgeCard.subject.like(term))).limit(limit).all(); notes=db.query(models.Note).filter(or_(models.Note.title.like(term),models.Note.content.like(term))).limit(20).all(); policies=db.query(models.Policy).filter(or_(models.Policy.title.like(term),models.Policy.original_text.like(term))).limit(20).all(); return {"cards":[card_dict(c,db.get(models.LearningState,c.id)) for c in cards],"notes":[{"id":n.id,"title":n.title,"content":n.content} for n in notes],"policies":[{"id":p.id,"title":p.title,"institution":p.institution} for p in policies]}

@app.get("/api/graph",dependencies=[Depends(require_access)])
def graph(subject:str|None=None,limit:int=120,db:Session=Depends(get_db)):
    q=db.query(models.KnowledgeCard).filter_by(review_status="approved"); q=q.filter_by(subject=subject) if subject else q; cs=q.limit(min(limit,300)).all(); ids={c.id for c in cs}; rel=db.query(models.Relationship).filter(models.Relationship.source_id.in_(ids),models.Relationship.target_id.in_(ids)).all(); return {"nodes":[{"id":c.id,"name":c.title,"subject":c.subject} for c in cs],"links":[{"source":r.source_id,"target":r.target_id,"type":r.relation_type} for r in rel]}

@app.get("/api/reviews",dependencies=[Depends(require_access)])
def reviews(status:str="pending",db:Session=Depends(get_db)):
    return [{x.name:getattr(r,x.name) for x in r.__table__.columns} for r in db.query(models.ReviewItem).filter_by(status=status).order_by(models.ReviewItem.created_at.desc()).all()]

@app.post("/api/reviews/{item_id}/action",dependencies=[Depends(require_access)])
def review_action(item_id:int,p:schemas.ReviewAction,db:Session=Depends(get_db)):
    r=db.get(models.ReviewItem,item_id)
    if not r:raise HTTPException(404,"审核项不存在")
    ensure_daily_backup(db);r.trust_level=p.trust_level or r.trust_level
    if p.action=="reject":r.status="rejected"
    elif p.action=="draft":r.status="draft"
    else:
        payload=p.edited_payload or json.loads(r.payload_json)
        if r.item_type=="knowledge_card":
            if "sections" in payload and "sections_json" not in payload:payload["sections_json"]=json.dumps(payload.pop("sections"),ensure_ascii=False)
            if "accuracy_notes" in payload and "accuracy_notes_json" not in payload:payload["accuracy_notes_json"]=json.dumps(payload.pop("accuracy_notes"),ensure_ascii=False)
            payload.setdefault("explanation",payload.get("why_exists",payload.get("summary","")))
            payload.setdefault("sections_json","[]");payload.setdefault("accuracy_notes_json","[]")
            required={"id","subject","chapter","title","summary","explanation"}
            missing=required-set(payload)
            if missing:raise HTTPException(422,f"候选知识卡缺少字段：{','.join(sorted(missing))}")
            payload["review_status"]="approved";db.merge(models.KnowledgeCard(**{k:v for k,v in payload.items() if k in {x.name for x in models.KnowledgeCard.__table__.columns}}))
        r.status="accepted"
    db.commit();return {"ok":True,"status":r.status}

@app.get("/api/ai/providers",dependencies=[Depends(require_access)])
def providers():return safe_providers()

@app.put("/api/ai/providers/{provider_id}",dependencies=[Depends(require_access)])
def save_provider(provider_id:str,p:schemas.ProviderSave):
    if provider_id!=p.id:raise HTTPException(400,"服务商ID不一致")
    defaults=read_yaml("ai_providers.yaml",{"providers":[]});data=read_private_yaml("ai_providers.yaml",defaults); arr=data.setdefault("providers",[]); clean=p.model_dump(exclude={"api_key"}); found=next((i for i,x in enumerate(arr) if x.get("id")==provider_id),None)
    if found is None:arr.append(clean)
    else:arr[found]=clean
    write_private_yaml("ai_providers.yaml",data)
    if p.api_key:set_secret(p.api_key_env,p.api_key)
    return {"ok":True,"configured":bool(p.api_key or read_secrets().get(p.api_key_env))}

@app.post("/api/ai/providers/{provider_id}/models",dependencies=[Depends(require_access)])
async def sync_models(provider_id:str):
    try:return {"models":await list_models(provider_id),"notice":"仅同步模型ID；能力仍为未测试"}
    except Exception as e:raise HTTPException(400,str(e))

@app.post("/api/ai/providers/{provider_id}/test",dependencies=[Depends(require_access)])
async def test_provider(provider_id:str,model:str):
    try:
        answer,usage=await chat(provider_id,model,[{"role":"user","content":"只回复 OK"}],16,"无",0);return {"ok":True,"answer":answer,"usage":usage,"may_cost":True}
    except Exception as e:raise HTTPException(400,str(e))

@app.post("/api/ai/providers/{provider_id}/capability-test",dependencies=[Depends(require_access)])
async def capability_test(provider_id:str,p:schemas.CapabilityTestInput):
    return await capability_probe(provider_id,p.model,p.capability,p.reasoning)

def enforce_ai_limits(db:Session,provider_id:str,model_id:str,max_output:int):
    prices=read_yaml("pricing.yaml",{});limits=prices.get("limits",{});now=datetime.utcnow();today=now.replace(hour=0,minute=0,second=0,microsecond=0);month=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    if max_output>int(limits.get("max_output_tokens") or 8000):raise HTTPException(429,"超过单次最大输出限制")
    daily=db.query(models.AiUsage).filter(models.AiUsage.created_at>=today).count();monthly=db.query(models.AiUsage).filter(models.AiUsage.created_at>=month).count()
    if daily>=int(limits.get("daily_calls") or 50):raise HTTPException(429,"已达到每日 AI 调用次数上限")
    if monthly>=int(limits.get("monthly_calls") or 500):raise HTTPException(429,"已达到每月 AI 调用次数上限")

def build_context(db:Session,p:schemas.ChatInput,conversation_id:str):
    messages=[{"role":"system","content":"你是通信工程学习助手。准确、诚实、分层解释；不确定时明确说明。不要输出隐藏推理过程。"}]
    conv=db.get(models.AiConversation,conversation_id)
    if conv and conv.context_strategy=="summary_recent" and conv.summary:messages.append({"role":"system","content":"先前对话摘要："+conv.summary[:3000]})
    history=[] if conv and conv.context_strategy=="none" else db.query(models.AiMessage).filter_by(conversation_id=conversation_id).order_by(models.AiMessage.id.desc()).limit(10).all(); messages += [{"role":x.role,"content":x.content} for x in reversed(history)]
    if p.include_card and p.card_id:
        c=db.get(models.KnowledgeCard,p.card_id)
        if c:messages.append({"role":"system","content":f"当前知识卡：{c.subject}/{c.title}\n{c.summary}\n{c.problem_solved}\n{c.engineering_use}"})
    if p.selected_note_ids:
        ns=db.query(models.Note).filter(models.Note.id.in_(p.selected_note_ids)).all();messages.append({"role":"system","content":"用户明确选择的笔记：\n"+"\n".join(n.content for n in ns)})
    messages.append({"role":"user","content":p.message});return messages

def load_ai_images(db:Session,asset_ids:list[int],detail:str) -> tuple[list[dict[str,str]],list[str]]:
    if not asset_ids:return [],[]
    ordered_ids=list(dict.fromkeys(asset_ids))
    if len(ordered_ids)>4:raise HTTPException(422,"一次最多发送4张图片")
    rows={a.id:a for a in db.query(models.MediaAsset).filter(models.MediaAsset.id.in_(ordered_ids)).all()}
    images:list[dict[str,str]]=[];names:list[str]=[]
    media_root=MEDIA_DIR.resolve()
    for asset_id in ordered_ids:
        asset=rows.get(asset_id)
        if not asset:raise HTTPException(404,f"图片资源 {asset_id} 不存在")
        path=Path(asset.local_path).resolve()
        if media_root not in path.parents or not path.is_file():raise HTTPException(422,f"图片资源 {asset_id} 的本地路径无效")
        data=path.read_bytes()
        if len(data)>10*1024*1024:raise HTTPException(413,f"图片资源 {asset_id} 超过单张10MB云端发送限制")
        try:
            with Image.open(BytesIO(data)) as probe:
                image_format=(probe.format or "").upper();probe.verify()
        except Exception as exc:
            raise HTTPException(415,f"图片资源 {asset_id} 不是有效图片") from exc
        mime={"PNG":"image/png","JPEG":"image/jpeg","WEBP":"image/webp"}.get(image_format)
        if not mime:raise HTTPException(415,f"图片资源 {asset_id} 的格式不支持云端视觉分析，请转为 PNG、JPEG 或 WebP")
        images.append({"data_url":f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}","detail":detail})
        names.append(f"媒体 #{asset_id}（{image_format}，{len(data)//1024+1}KB）")
    return images,names

@app.post("/api/ai/chat",dependencies=[Depends(require_access)])
async def ai_chat(p:schemas.ChatInput,db:Session=Depends(get_db)):
    if not p.consent:raise HTTPException(412,"请先确认本次发送内容摘要和费用")
    enforce_ai_limits(db,p.provider_id,p.model,p.max_output)
    provider=next((x for x in safe_providers() if x["id"]==p.provider_id),None)
    model_cfg=next((m for m in (provider or {}).get("models",[]) if m.get("id")==p.model),{})
    if p.image_asset_ids and model_cfg.get("image_input")!="verified_supported":raise HTTPException(422,"该模型未验证支持图片，原图不会发送")
    if model_cfg.get("reasoning_tests",{}).get(p.reasoning)=="verified_unsupported":raise HTTPException(422,f"该模型已验证不支持“{p.reasoning}”思考档位")
    images,image_names=load_ai_images(db,p.image_asset_ids,p.image_detail)
    cid=p.conversation_id or str(uuid.uuid4());conv=db.get(models.AiConversation,cid)
    if not conv:conv=models.AiConversation(id=cid,title=p.message[:40]);db.add(conv);db.commit()
    messages=build_context(db,p,cid)
    native_web=bool(p.allow_web and provider and provider.get("protocol")=="openai_responses" and model_cfg.get("web_search")=="verified_supported")
    web_sources=[]
    if p.allow_web and not native_web:
        web_sources=await search_public_web(p.message)
        messages.insert(len(messages)-1,{"role":"system","content":search_context(web_sources)})
    try:
        answer,usage=await chat(p.provider_id,p.model,messages,p.max_output,p.reasoning,p.temperature,images=images,native_web=native_web)
        if native_web:web_sources=usage.get("web_sources",[])
        db.add_all([models.AiMessage(conversation_id=cid,role="user",content=p.message),models.AiMessage(conversation_id=cid,role="assistant",content=answer),models.AiUsage(provider=p.provider_id,model=p.model,feature="chat_web" if p.allow_web else "chat",reasoning=p.reasoning,input_tokens=usage["input"],output_tokens=usage["output"],image_count=len(images),success=True)])
        db.commit()
        count=db.query(models.AiMessage).filter_by(conversation_id=cid).count()
        if count>=12 and count%6==0:
            recent=db.query(models.AiMessage).filter_by(conversation_id=cid,role="user").order_by(models.AiMessage.id.desc()).limit(6).all();conv.summary="；".join(x.content[:180] for x in reversed(recent));db.commit()
        return {"conversation_id":cid,"answer":answer,"usage":{"input":usage["input"],"output":usage["output"]},"sent_context":messages,"sent_attachments":image_names,"network_mode":"provider_native" if native_web else "backend_public_search" if p.allow_web else "off","web_sources":web_sources}
    except Exception as e:
        db.add(models.AiUsage(provider=p.provider_id,model=p.model,feature="chat_web" if p.allow_web else "chat",reasoning=p.reasoning,image_count=len(images),success=False,error_code=type(e).__name__));db.commit();raise HTTPException(502,str(e))

@app.post("/api/ai/generate-card",dependencies=[Depends(require_access)])
async def generate_card(p:schemas.GenerateCardInput,db:Session=Depends(get_db)):
    if not p.consent:raise HTTPException(412,"请确认本次云端调用")
    ensure_daily_backup(db);enforce_ai_limits(db,p.provider_id,p.model,2200)
    fields=["title","chapter","preview","explanation","sections","keywords","accuracy_notes"]
    prompt=f"为通信工程学生通俗讲解一个知识主题。学科：{p.subject}，主题：{p.topic}。只输出JSON对象，字段必须包含：{','.join(fields)}。preview用50至120字讲出具体认识；explanation用自然连贯的中文全面讲懂，不要机械拆成为什么存在、输入、输出；sections是仅在确有必要时使用的heading/content对象数组；keywords和accuracy_notes是字符串数组。"
    try:
        answer,usage=await chat(p.provider_id,p.model,[{"role":"user","content":prompt}],2200,"中",0.2)
        raw=answer.strip();raw=raw[raw.find("{"):raw.rfind("}")+1];data=json.loads(raw)
        missing=[x for x in ("title","chapter","preview","explanation") if not isinstance(data.get(x),str) or len(data[x].strip())<4]
        if not isinstance(data.get("sections"),list) or not isinstance(data.get("keywords"),list) or not isinstance(data.get("accuracy_notes"),list):missing.append("数组字段")
        if missing:raise ValueError("结构化结果缺少字段："+",".join(missing))
        slug=hashlib.sha256(f"{p.subject}:{p.topic}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]
        explanation=data["explanation"].strip();payload={"id":f"ai-{slug}","subject":p.subject,"chapter":data["chapter"].strip(),"title":data["title"].strip(),"summary":data["preview"].strip(),"explanation":explanation,"sections_json":json.dumps(data["sections"],ensure_ascii=False),"accuracy_notes_json":json.dumps(data["accuracy_notes"],ensure_ascii=False),"why_exists":explanation,"problem_solved":"","intuition":"","inputs":"","outputs":"","common_uses":"","engineering_use":"","simple_example":"","misconceptions":"","prerequisites":"","related":"","next_steps":"","keywords":"，".join(str(x) for x in data["keywords"]),"difficulty":3,"content_level":"通俗短解释+自然正文+按需小节","visual_template":None,"visual_params":"{}","source":"AI生成候选；正式入库前必须人工复核并补充可靠来源","creation_method":"ai_generated","review_status":"pending","content_version":2,"competition_relevant":False}
        item=models.ReviewItem(item_type="knowledge_card",title=payload["title"],payload_json=json.dumps(payload,ensure_ascii=False),trust_level="待人工核实");db.add(item);db.add(models.AiUsage(provider=p.provider_id,model=p.model,feature="generate_card",reasoning="中",input_tokens=usage["input"],output_tokens=usage["output"],success=True));db.commit();db.refresh(item);return {"review_id":item.id,"status":"pending"}
    except Exception as e:
        db.rollback();db.add(models.AiUsage(provider=p.provider_id,model=p.model,feature="generate_card",reasoning="中",success=False,error_code=type(e).__name__));db.commit();raise HTTPException(502,f"生成失败：{e}")

@app.get("/api/ai/conversations",dependencies=[Depends(require_access)])
def conversations(q:str|None=None,db:Session=Depends(get_db)):
    query=db.query(models.AiConversation);query=query.filter(models.AiConversation.title.contains(q)) if q else query;return [{"id":x.id,"title":x.title,"summary":x.summary,"updated_at":x.updated_at} for x in query.order_by(models.AiConversation.updated_at.desc()).all()]

@app.get("/api/ai/conversations/{cid}",dependencies=[Depends(require_access)])
def conversation(cid:str,db:Session=Depends(get_db)):
    c=db.get(models.AiConversation,cid)
    if not c:raise HTTPException(404,"会话不存在")
    return {"id":c.id,"title":c.title,"messages":[{"id":m.id,"role":m.role,"content":m.content,"created_at":m.created_at} for m in db.query(models.AiMessage).filter_by(conversation_id=cid).order_by(models.AiMessage.id).all()]}

@app.delete("/api/ai/conversations/{cid}",dependencies=[Depends(require_access)])
def delete_conversation(cid:str,db:Session=Depends(get_db)):
    c=db.get(models.AiConversation,cid)
    if c:db.delete(c);db.commit()
    return {"ok":True}

@app.put("/api/ai/conversations/{cid}",dependencies=[Depends(require_access)])
def update_conversation(cid:str,body:dict,db:Session=Depends(get_db)):
    c=db.get(models.AiConversation,cid)
    if not c:raise HTTPException(404,"会话不存在")
    if "title" in body:c.title=str(body["title"])[:160]
    if body.get("context_strategy") in {"recent","summary_recent","none"}:c.context_strategy=body["context_strategy"]
    db.commit();return {"ok":True}

@app.post("/api/ai/conversations/{cid}/export",dependencies=[Depends(require_access)])
@app.get("/api/ai/conversations/{cid}/export",dependencies=[Depends(require_access)])
def export_conversation(cid:str,db:Session=Depends(get_db)):
    c=db.get(models.AiConversation,cid)
    if not c:raise HTTPException(404,"会话不存在")
    messages=db.query(models.AiMessage).filter_by(conversation_id=cid).order_by(models.AiMessage.id).all();path=EXPORT_DIR/"markdown"/f"ai_{cid}.md";path.parent.mkdir(parents=True,exist_ok=True);path.write_text(f"# {c.title}\n\n"+"\n\n".join(f"## {'用户' if x.role=='user' else 'AI'}\n\n{x.content}" for x in messages),encoding="utf-8");return {"path":str(path),"messages":len(messages),"secrets_removed":True}

@app.get("/api/ai/usage",dependencies=[Depends(require_access)])
def usage(db:Session=Depends(get_db)):
    rows=db.query(models.AiUsage).order_by(models.AiUsage.created_at.desc()).limit(500).all();return [{x.name:getattr(r,x.name) for x in r.__table__.columns} for r in rows]

ALLOWED_EXT={".png",".jpg",".jpeg",".webp",".bmp",".pdf"};MAX_UPLOAD=20*1024*1024
@app.post("/api/media/upload",dependencies=[Depends(require_access)])
async def upload(file:UploadFile=File(...),db:Session=Depends(get_db)):
    ext=Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:raise HTTPException(415,"不支持的文件类型")
    data=await file.read(MAX_UPLOAD+1)
    if len(data)>MAX_UPLOAD:raise HTTPException(413,"文件超过20MB限制")
    expected=mimetypes.guess_type("x"+ext)[0]
    if file.content_type and expected and file.content_type not in {expected,"application/octet-stream"}:raise HTTPException(415,"文件扩展名与MIME类型不一致")
    name=f"{uuid.uuid4().hex}{ext}";path=(MEDIA_DIR/"uploaded"/name).resolve()
    if MEDIA_DIR.resolve() not in path.parents:raise HTTPException(400,"非法路径")
    path.write_bytes(data);asset=models.MediaAsset(local_path=str(path));db.add(asset);db.commit();db.refresh(asset);return {"id":asset.id,"name":name,"size":len(data)}

@app.post("/api/media/{asset_id}/ocr",dependencies=[Depends(require_access)])
def ocr_asset(asset_id:int,db:Session=Depends(get_db)):
    a=db.get(models.MediaAsset,asset_id)
    if not a:raise HTTPException(404,"图片不存在")
    try:result=run_ocr(Path(a.local_path));a.ocr_text=result["text"];db.commit();return result
    except Exception as e:raise HTTPException(503,str(e))

@app.get("/api/media",dependencies=[Depends(require_access)])
def media(db:Session=Depends(get_db)):
    return [{x.name:getattr(a,x.name) for x in a.__table__.columns} for a in db.query(models.MediaAsset).order_by(models.MediaAsset.id.desc()).all()]

@app.get("/api/policies",dependencies=[Depends(require_access)])
def policies(db:Session=Depends(get_db)):
    return [{x.name:getattr(p,x.name) for x in p.__table__.columns} for p in db.query(models.Policy).order_by(models.Policy.published_date.desc()).all()]

@app.get("/api/universities",dependencies=[Depends(require_access)])
def universities(q:str|None=None,province:str|None=None,db:Session=Depends(get_db)):
    query=db.query(models.UniversityProgram);query=query.filter(or_(models.UniversityProgram.school.contains(q),models.UniversityProgram.program_name.contains(q))) if q else query;query=query.filter_by(province=province) if province else query;return [{x.name:getattr(p,x.name) for x in p.__table__.columns} for p in query.limit(100).all()]

@app.post("/api/sources/check",dependencies=[Depends(require_access)])
async def source_check(p:schemas.SourceCheckInput,db:Session=Depends(get_db)):return await check_sources(db,p.source_ids)

@app.get("/api/sources",dependencies=[Depends(require_access)])
def sources():return read_yaml("source_registry.yaml",{"sources":[]})

@app.post("/api/auth/setup")
def auth_setup(p:schemas.LoginInput,request:Request,db:Session=Depends(get_db)):
    if not is_loopback(request):raise HTTPException(403,"只能在本机设置局域网账号")
    row=db.query(models.UserAccount).first()
    if row:raise HTTPException(409,"账号已存在，请使用修改密码")
    db.add(models.UserAccount(username=p.username,password_hash=ph.hash(p.password)));db.commit();return {"ok":True}

@app.post("/api/auth/login")
def login(p:schemas.LoginInput,db:Session=Depends(get_db)):
    u=db.query(models.UserAccount).filter_by(username=p.username).first();now=datetime.utcnow()
    if not u or (u.locked_until and u.locked_until>now):raise HTTPException(429 if u else 401,"账号不存在或已暂时锁定")
    try:ph.verify(u.password_hash,p.password)
    except VerifyMismatchError:
        u.failed_attempts+=1
        if u.failed_attempts>=5:u.locked_until=now+timedelta(minutes=15);u.failed_attempts=0
        db.commit();raise HTTPException(401,"用户名或密码错误")
    u.failed_attempts=0;u.locked_until=None;token,expires=create_session(db,u.id);return {"token":token,"expires_at":expires}

@app.post("/api/auth/change-password",dependencies=[Depends(require_access)])
def change_password(p:schemas.LoginInput,request:Request,db:Session=Depends(get_db)):
    if not is_loopback(request):raise HTTPException(403,"请在本机修改密码")
    u=db.query(models.UserAccount).first()
    if not u:u=models.UserAccount(username=p.username,password_hash=ph.hash(p.password));db.add(u)
    else:u.username=p.username;u.password_hash=ph.hash(p.password)
    db.query(models.AuthSession).delete();db.commit();return {"ok":True}

@app.get("/api/settings",dependencies=[Depends(require_access)])
def get_settings(db:Session=Depends(get_db)):
    return {x.key:x.value for x in db.query(models.AppSetting).all()}

@app.put("/api/settings",dependencies=[Depends(require_access)])
def put_settings(values:dict[str,str],db:Session=Depends(get_db)):
    allowed={"setup_complete","lan_enabled","background_mode","background_id","privacy_confirmation","daily_ai_calls","monthly_ai_cost","single_max_cost","review_mode"}
    for k,v in values.items():
        if k not in allowed:continue
        row=db.get(models.AppSetting,k) or models.AppSetting(key=k,value=str(v));row.value=str(v);db.add(row)
    db.commit();return {"ok":True}

@app.post("/api/backups",dependencies=[Depends(require_access)])
def backup_now():return {"path":str(create_backup())}

@app.post("/api/data/export/{fmt}",dependencies=[Depends(require_access)])
def export_data(fmt:str,db:Session=Depends(get_db)):
    if fmt not in {"json","csv","markdown"}:raise HTTPException(400,"仅支持 json、csv、markdown")
    rows=[{x.name:getattr(c,x.name) for x in c.__table__.columns} for c in db.query(models.KnowledgeCard).filter_by(review_status="approved").all()]
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S");folder=EXPORT_DIR/("markdown" if fmt=="markdown" else fmt);folder.mkdir(parents=True,exist_ok=True);suffix="md" if fmt=="markdown" else fmt;path=folder/f"knowledge_cards_{stamp}.{suffix}"
    if fmt=="json":path.write_text(json.dumps({"schema_version":"1.0","exported_at":datetime.now().isoformat(),"cards":rows},ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    elif fmt=="csv":
        with path.open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    else:path.write_text("\n\n".join(f"# {x['title']}\n\n{x['summary']}\n\n- 学科：{x['subject']}\n- 工程用途：{x['engineering_use']}\n- 来源：{x['source']}" for x in rows),encoding="utf-8")
    return {"path":str(path),"count":len(rows),"secrets_removed":True}

@app.post("/api/data/import",dependencies=[Depends(require_access)])
async def import_data(file:UploadFile=File(...),db:Session=Depends(get_db)):
    if Path(file.filename or "").suffix.lower()!=".json":raise HTTPException(415,"当前安全导入仅接受本站 JSON 导出")
    raw=await file.read(25*1024*1024+1)
    if len(raw)>25*1024*1024:raise HTTPException(413,"导入文件超过25MB")
    try:data=json.loads(raw.decode("utf-8-sig"))
    except Exception:raise HTTPException(422,"JSON 格式无效")
    if not str(data.get("schema_version","")).startswith("1."):raise HTTPException(422,"Schema 版本不兼容")
    cards=data.get("cards")
    if not isinstance(cards,list):raise HTTPException(422,"缺少 cards 数组")
    ensure_daily_backup(db);required={"id","subject","chapter","title","summary","why_exists","problem_solved","intuition","inputs","outputs","common_uses","engineering_use","simple_example","misconceptions","prerequisites","related","next_steps","keywords","difficulty","content_level","source","content_version"};existing={x[0] for x in db.query(models.KnowledgeCard.id).all()};conflicts=[];accepted=0
    for item in cards[:5000]:
        if not isinstance(item,dict) or required-set(item):conflicts.append({"id":item.get("id") if isinstance(item,dict) else None,"reason":"字段不完整"});continue
        if item["id"] in existing:conflicts.append({"id":item["id"],"reason":"ID已存在，不覆盖"});continue
        payload={k:v for k,v in item.items() if k in {x.name for x in models.KnowledgeCard.__table__.columns}};payload.update({"review_status":"pending","creation_method":"imported"})
        db.add(models.ReviewItem(item_type="knowledge_card",title=payload["title"],payload_json=json.dumps(payload,ensure_ascii=False,default=str),trust_level="导入待审核"));accepted+=1
    db.commit();return {"queued":accepted,"conflicts":conflicts,"backup_created":True,"overwritten":0}

@app.get("/api/backups",dependencies=[Depends(require_access)])
def backups():return [{"name":p.name,"path":str(p),"size":p.stat().st_size,"modified":datetime.fromtimestamp(p.stat().st_mtime)} for p in sorted(BACKUP_DIR.rglob("*.zip"),reverse=True)]

@app.post("/api/backups/verify",dependencies=[Depends(require_access)])
def backup_verify(body:dict):
    path=Path(body.get("path","")).resolve()
    if BACKUP_DIR.resolve() not in path.parents:raise HTTPException(400,"只能验证备份目录中的文件")
    ok,errors=verify_backup(path);return {"ok":ok,"errors":errors}

@app.get("/api/diagnostics",dependencies=[Depends(require_access)])
async def diagnostics(db:Session=Depends(get_db)):
    checks=[]
    def add(name,ok,detail):checks.append({"name":name,"ok":ok,"detail":detail})
    try:db.execute(text("SELECT 1"));add("SQLite数据库",True,str(DB_PATH))
    except Exception as e:add("SQLite数据库",False,str(e))
    add("用户数据目录",USERDATA_DIR.exists(),str(USERDATA_DIR));add("OCR",__import__("importlib").util.find_spec("paddleocr") is not None,"PaddleOCR CPU")
    add("AI配置",any(p["configured"] for p in safe_providers()),"未配置不影响离线功能")
    add("知识卡",db.query(models.KnowledgeCard).count()>=900,f"{db.query(models.KnowledgeCard).count()} 条")
    return {"checks":checks,"all_ok":all(x["ok"] for x in checks if x["name"] not in {"OCR","AI配置"})}

dist=PROGRAM_DIR/"frontend"/"dist"
backgrounds_dir=MEDIA_DIR/"backgrounds"
backgrounds_dir.mkdir(parents=True,exist_ok=True)
app.mount("/user-backgrounds",StaticFiles(directory=backgrounds_dir),name="user-backgrounds")
if dist.exists():
    app.mount("/assets",StaticFiles(directory=dist/"assets"),name="assets")
    @app.get("/{path:path}")
    def spa(path:str):
        candidate=(dist/path).resolve()
        if candidate.is_file() and dist.resolve() in candidate.parents:return FileResponse(candidate)
        return FileResponse(dist/"index.html")
