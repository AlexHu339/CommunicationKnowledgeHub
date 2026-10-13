from __future__ import annotations
import json,collections,re,sys
from difflib import SequenceMatcher
from pathlib import Path
if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
ROOT=Path(__file__).resolve().parents[2];path=ROOT/"program"/"shared"/"seeds"/"knowledge_cards.json"
cards=json.loads(path.read_text(encoding="utf-8"));required={"id","subject","chapter","title","summary","explanation","sections_json","accuracy_notes_json","why_exists","problem_solved","intuition","inputs","outputs","common_uses","engineering_use","simple_example","misconceptions","prerequisites","related","next_steps","keywords","difficulty","content_level","source","creation_method","review_status","content_version"}
errors=[];ids=set();titles=set();counts=collections.Counter();missing_visual=missing_source=0
for i,c in enumerate(cards):
    miss=required-set(c)
    if miss:errors.append(f"{i}: missing {sorted(miss)}")
    if c.get("id") in ids:errors.append(f"duplicate id {c['id']}")
    title_key=(c.get("subject"),c.get("title"))
    if title_key in titles:errors.append(f"duplicate title in subject {c['subject']} / {c['title']}")
    if any(x in json.dumps(c,ensure_ascii=False) for x in ["TODO","TBD","待填","Lorem"]):errors.append(f"placeholder {c.get('id')}")
    if not 1<=c.get("difficulty",0)<=5:errors.append(f"difficulty {c.get('id')}")
    if len(c.get("summary",""))<25:errors.append(f"summary too short {c.get('id')}")
    ids.add(c.get("id"));titles.add(title_key);counts[c.get("subject")]+=1
    missing_visual+=not bool(c.get("visual_template"));missing_source+=not bool(c.get("source"))
similar=[]
ordered=list(titles)
for a,b in zip(ordered,ordered[1:]):
    if SequenceMatcher(None,a,b).ratio()>.94:similar.append((a,b))
alias_path=ROOT/"program"/"shared"/"seeds"/"knowledge_card_aliases.json";alias_count=len(json.loads(alias_path.read_text(encoding="utf-8")).get("aliases",[])) if alias_path.exists() else 0
rewritten=sum(bool(c.get("explanation","").strip()) for c in cards)
report={"total":len(cards),"subject_counts":dict(counts),"natural_explanations":rewritten,"rewrite_pending":len(cards)-rewritten,"merged_legacy_aliases":alias_count,"missing_visual":missing_visual,"missing_source":missing_source,"exact_duplicate_titles_within_subject":len(cards)-len(titles),"high_similarity_sample":similar[:20],"field_completeness":round(1-sum(len(required-set(c)) for c in cards)/(len(cards)*len(required)),6),"validation_errors":errors,"import_ready":not errors}
out=ROOT/"docs"/"CONTENT_STATISTICS.json";out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(1 if errors else 0)
