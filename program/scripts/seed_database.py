from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"program"/"backend"))
from app.database import Base,engine,SessionLocal
from app.models import KnowledgeCard,UniversityProgram,Policy

seed=ROOT/"program"/"shared"/"seeds"/"knowledge_cards.json"
if not seed.exists():exec((ROOT/"program"/"scripts"/"generate_seed.py").read_text(encoding="utf-8"))
cards=json.loads(seed.read_text(encoding="utf-8"));Base.metadata.create_all(engine);db=SessionLocal()
try:
    existing={x[0] for x in db.query(KnowledgeCard.id).all()}
    for item in cards:
        if item["id"] not in existing:db.add(KnowledgeCard(**item))
    db.commit()
    official=[
      dict(school="东南大学",province="江苏",city="南京",college="信息科学与工程学院",program_code="待核实",program_name="信息与通信工程/电子信息（以当年目录为准）",degree_type="待核实",source_url="https://yzb.seu.edu.cn/",data_year=2028,missing_fields="2028招生目录尚未发布，所有考试科目、名额、分数线、学费待官方核实"),
      dict(school="南京邮电大学",province="江苏",city="南京",college="通信与信息工程学院",program_code="待核实",program_name="信息与通信工程/电子信息（以当年目录为准）",degree_type="待核实",source_url="https://yzb.njupt.edu.cn/",data_year=2028,missing_fields="2028招生目录尚未发布，所有动态字段待官方核实"),
      dict(school="上海交通大学",province="上海",city="上海",college="电子信息与电气工程学院",program_code="待核实",program_name="电子信息相关方向（以当年目录为准）",degree_type="待核实",source_url="https://yzb.sjtu.edu.cn/",data_year=2028,missing_fields="2028招生目录尚未发布，所有动态字段待官方核实"),
      dict(school="浙江大学",province="浙江",city="杭州",college="信息与电子工程学院",program_code="待核实",program_name="电子信息相关方向（以当年目录为准）",degree_type="待核实",source_url="https://grs.zju.edu.cn/yjszs/",data_year=2028,missing_fields="2028招生目录尚未发布，所有动态字段待官方核实"),
      dict(school="中国科学技术大学",province="安徽",city="合肥",college="信息科学技术学院",program_code="待核实",program_name="信息与通信工程/电子信息（以当年目录为准）",degree_type="待核实",source_url="https://yz.ustc.edu.cn/",data_year=2028,missing_fields="2028招生目录尚未发布，所有动态字段待官方核实")]
    for item in official:
        if not db.query(UniversityProgram).filter_by(school=item["school"],data_year=2028).first():db.add(UniversityProgram(**item))
    db.commit();print(f"database seeded: {len(cards)} knowledge topics")
finally:db.close()
