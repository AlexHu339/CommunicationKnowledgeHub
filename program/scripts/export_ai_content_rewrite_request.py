from __future__ import annotations

import json
import re
from collections import OrderedDict, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "program" / "shared" / "seeds" / "knowledge_cards.json"
OUTPUT = ROOT / "exports" / "给AI的知识点通俗解释重写任务.txt"

SUBJECT_ORDER = [
    "高等数学",
    "线性代数",
    "概率论与数理统计",
    "模拟电子技术",
    "信号与系统",
    "数字系统原理与设计",
    "电磁场与电磁波",
    "通信电子线路",
    "数字信号处理",
    "信息论与编码",
    "微机原理与接口技术",
    "通信原理",
    "单片机与嵌入式系统",
    "工程通识与仪器使用",
    "电赛知识",
    "考研常识",
]


def concept_from_title(title: str) -> str:
    value = title.split("·", 1)[-1]
    return re.sub(r"：(概念轮廓|关键条件|参数影响)$", "", value).strip()


def chapter_hint(chapter: str) -> str:
    value = re.sub(r"^\d+·", "", chapter).strip()
    return re.sub(r"基础$", "", value).strip()


def build_request(cards: list[dict]) -> str:
    concepts: OrderedDict[tuple[str, str], dict] = OrderedDict()
    for card in cards:
        concept = concept_from_title(card["title"])
        key = (card["subject"], concept)
        if key not in concepts:
            concepts[key] = {
                "subject": card["subject"],
                "title": concept,
                "chapter_hint": chapter_hint(card["chapter"]),
                "canonical_id": card["id"],
                "replace_ids": [],
            }
        concepts[key]["replace_ids"].append(card["id"])

    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in concepts.values():
        grouped[item["subject"]].append(item)

    lines = [
        "通信工程知识学习网站——知识内容全面重写任务",
        "（请把本文件完整交给AI；文件编码为UTF-8）",
        "",
        "一、用户情况",
        "用户是通信工程学习者。主要学习目标包括通信工程课程、电子设计、单片机与嵌入式实践。用户希望先形成清晰、直观、能用的知识轮廓，之后再按需要深入公式和推导。",
        "",
        "二、为什么要重写",
        "当前网站名义上有1000张卡片，但实际只有406个不同主题；很多主题被机械拆成“概念轮廓、关键条件、参数影响”两三张卡，正文又强制套用“为什么存在、解决什么问题、输入、输出”等栏目。这种写法抽象、重复，也不符合所有知识点的特点。请完全忽略旧正文，只以本文件末尾的主题清单为范围重新讲解。",
        "",
        "三、写作原则",
        "1. 先把人讲懂，再考虑术语完整。假设读者学过基础课程但当前对这个概念没有清晰印象。",
        "2. 主体必须是自然、连贯、通俗的中文解释，不要把每个知识点硬拆成相同栏目。",
        "3. 只有确实能帮助理解时才增加小节。小节标题应随内容变化，例如“生活类比”“怎么看波形”“在电赛里怎么用”“容易混淆的地方”“考研报名时怎么判断”，不得每条都复制同一组标题。",
        "4. 不要使用“它是一组核心概念或方法”“先看它改变了什么”“输入—处理—输出”等空泛套话。除非该知识本身确实是系统、算法或模块，否则不要强行写输入和输出。",
        "5. 第一次出现专业词时顺手解释。抽象概念尽量配一个具体场景、数量级、波形现象、生活类比或工程动作，但不要编造不准确的类比。",
        "6. 技术内容要准确。需要公式时使用Markdown LaTeX，并紧接着用中文解释每个量和公式表达的直觉；不需要公式时不要为了显得专业而堆公式。",
        "7. 结合通信工程、电赛、单片机、仪器使用或考研的实际场景，但只在确实相关时写，不要每条强行关联电赛。",
        "8. 考研常识按完整句子解释清楚“它是什么、学生会在哪一步遇到、应看什么官方材料、常见误解是什么”。不要写输入/输出，不要编造尚未发布的2028政策、分数线或招生人数；时效性信息注明“以对应年份官方文件为准”。",
        "9. 不凑字数。普通主题通常300—700个汉字，简单主题可以更短，复杂主题可以到1000字，以真正讲清楚为准。",
        "10. 同一主题只生成一条内容，不要继续拆成“概念轮廓/关键条件/参数影响”。",
        "",
        "四、每条返回数据的格式",
        "请返回UTF-8编码的JSONL文件（每行一个完整JSON对象，不要在JSONL中加入Markdown代码围栏）。每个对象使用以下字段：",
        "",
        '{"canonical_id":"原样保留","replace_ids":["原样保留全部旧ID"],"subject":"学科","title":"简洁准确的标题","chapter":"合理章节名称","preview":"50—120字、能独立看懂的首页短解释","explanation":"自然连贯、通俗且全面的主体解释，可包含换行","sections":[{"heading":"仅在必要时使用的自定义小节标题","content":"小节正文"}],"keywords":["3至8个检索词"],"accuracy_notes":["需要核实或有适用条件时填写；没有则为空数组"]}',
        "",
        "字段要求：",
        "- canonical_id和replace_ids必须从清单原样复制，便于网站把旧重复卡合并成一条新卡。",
        "- preview不是“定义句模板”，要让用户在‘今日认识8个’页面只看这一段也能获得具体认识。",
        "- explanation是主要内容，可以直接分自然段；不要在这里重复preview。",
        "- sections允许为空数组。只有内容确实需要额外展开时才添加，数量通常0—4个。",
        "- accuracy_notes只写真实的不确定性、适用边界或需查官方文件的事项，不要虚构来源。",
        "",
        "五、交付方式",
        "清单共406个不同主题。不要在聊天消息中一次粘贴全部结果，以免被截断。建议每批处理20个主题，分别生成batch_01.jsonl、batch_02.jsonl……最后再合并为knowledge_rewrite_all.jsonl供下载。每完成一批先自行检查：ID齐全、JSON逐行可解析、没有机械模板、没有明显事实错误、没有空泛占位句。",
        "",
        "如果你认为某个标题需要更名，可以修改title；如果两个不同主题仍应合并，先分别完成内容，并在accuracy_notes中写明合并建议，不要擅自丢失任何ID。若发现重要主题缺失，请另建missing_topics.jsonl提出建议，不要混入本次406条替换结果。",
        "",
        "六、主题清单",
        f"原始卡片数：{len(cards)}；合并机械重复后主题数：{len(concepts)}。",
        "",
    ]

    serial = 0
    for subject in SUBJECT_ORDER:
        items = grouped.get(subject, [])
        lines.append(f"=== {subject}（{len(items)}个主题） ===")
        for item in items:
            serial += 1
            replace_ids = ",".join(item["replace_ids"])
            lines.append(
                f"[K{serial:03d}] canonical_id={item['canonical_id']} | "
                f"replace_ids={replace_ids} | 学科={item['subject']} | "
                f"章节参考={item['chapter_hint']} | 主题={item['title']}"
            )
        lines.append("")

    lines.extend(
        [
            "七、开始前请确认",
            "请先用一句话确认你已读取到406个主题，并说明准备从batch_01（K001—K020）开始。随后直接生成该批JSONL文件，不要再询问用户已经在本文件中给出的信息。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    cards = json.loads(SOURCE.read_text(encoding="utf-8"))
    text = build_request(cards)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text, encoding="utf-8-sig", newline="\r\n")
    unique_count = text.count("canonical_id=")
    print("created rewrite request")
    print(f"cards={len(cards)} unique_topics={unique_count}")


if __name__ == "__main__":
    main()
