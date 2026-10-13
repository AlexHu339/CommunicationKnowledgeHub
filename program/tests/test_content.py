import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def test_seed_schema_and_counts():
    cards=json.loads((ROOT/"program"/"shared"/"seeds"/"knowledge_cards.json").read_text(encoding="utf-8"));assert len(cards)==406
    assert len({x["id"] for x in cards})==406;assert len({(x["subject"],x["title"]) for x in cards})==406
    expected={"高等数学":20,"线性代数":16,"概率论与数理统计":20,"模拟电子技术":26,"信号与系统":30,"数字系统原理与设计":24,"电磁场与电磁波":22,"通信电子线路":24,"数字信号处理":28,"信息论与编码":22,"微机原理与接口技术":26,"通信原理":34,"单片机与嵌入式系统":26,"工程通识与仪器使用":24,"电赛知识":32,"考研常识":32}
    from collections import Counter
    assert Counter(x["subject"] for x in cards)==expected
    required={"summary","why_exists","problem_solved","intuition","inputs","outputs","common_uses","engineering_use","simple_example","misconceptions","prerequisites","related","next_steps","keywords","source"}
    assert all(all(len(str(x[k]))>=4 for k in required) for x in cards)
    assert all(all(k in x for k in ("explanation","sections_json","accuracy_notes_json")) for x in cards)
    assert sum(bool(x["explanation"].strip()) for x in cards)==406
    aliases=json.loads((ROOT/"program"/"shared"/"seeds"/"knowledge_card_aliases.json").read_text(encoding="utf-8"))["aliases"]
    assert len(aliases)==594 and len({x["alias_id"] for x in aliases})==594
