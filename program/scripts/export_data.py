from __future__ import annotations
import csv,json,sqlite3,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];db=sqlite3.connect(ROOT/"userdata"/"database"/"main.sqlite3");db.row_factory=sqlite3.Row
fmt=(sys.argv[1] if len(sys.argv)>1 else "json").lower();stamp=datetime.now().strftime("%Y%m%d_%H%M%S");rows=[dict(x) for x in db.execute("select * from knowledge_cards where review_status='approved'")]
out=ROOT/"exports"/fmt/f"knowledge_cards_{stamp}.{fmt}";out.parent.mkdir(parents=True,exist_ok=True)
if fmt=="json":out.write_text(json.dumps({"schema_version":"1.0","cards":rows},ensure_ascii=False,indent=2),encoding="utf-8")
elif fmt=="csv":
    with out.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
elif fmt in {"md","markdown"}:
    out=out.with_suffix(".md");out.write_text("\n\n".join(f"# {x['title']}\n\n{x['summary']}\n\n- 学科：{x['subject']}\n- 工程用途：{x['engineering_use']}\n- 来源：{x['source']}" for x in rows),encoding="utf-8")
else:raise SystemExit("格式仅支持 json/csv/markdown")
print(out)

