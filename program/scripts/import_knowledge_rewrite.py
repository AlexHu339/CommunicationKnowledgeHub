from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "program" / "shared" / "seeds" / "knowledge_cards.json"
ALIASES = ROOT / "program" / "shared" / "seeds" / "knowledge_card_aliases.json"


def concept_from_title(title: str) -> str:
    value = title.split("·", 1)[-1]
    return re.sub(r"：(概念轮廓|关键条件|参数影响)$", "", value).strip()


def clean_chapter(chapter: str) -> str:
    value = re.sub(r"^\d+·", "", chapter).strip()
    return re.sub(r"基础$", "", value).strip()


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {number}: invalid JSON: {exc}") from exc
        required = {
            "canonical_id", "replace_ids", "subject", "title", "chapter",
            "preview", "explanation", "sections", "keywords", "accuracy_notes",
        }
        missing = required - set(row)
        if missing:
            raise ValueError(f"line {number}: missing {sorted(missing)}")
        if not isinstance(row["replace_ids"], list) or row["canonical_id"] not in row["replace_ids"]:
            raise ValueError(f"line {number}: replace_ids must include canonical_id")
        if len(row["preview"].strip()) < 20 or len(row["explanation"].strip()) < 150:
            raise ValueError(f"line {number}: explanation is too short")
        if not isinstance(row["sections"], list) or any(
            not isinstance(item, dict) or not item.get("heading") or not item.get("content")
            for item in row["sections"]
        ):
            raise ValueError(f"line {number}: invalid sections")
        rows.append(row)
    return rows


def prepare_catalog(batch_path: Path | None) -> tuple[int, int]:
    cards = json.loads(SEED.read_text(encoding="utf-8"))
    old_aliases = {}
    if ALIASES.exists():
        alias_doc = json.loads(ALIASES.read_text(encoding="utf-8"))
        old_aliases = {item["alias_id"]: item["canonical_id"] for item in alias_doc.get("aliases", [])}

    groups: OrderedDict[tuple[str, str], list[dict]] = OrderedDict()
    if len(cards) > 500:
        for card in cards:
            key = (card["subject"], concept_from_title(card["title"]))
            groups.setdefault(key, []).append(card)
    else:
        for card in cards:
            groups[(card["subject"], card["title"])] = [card]

    aliases = dict(old_aliases)
    canonical_cards: list[dict] = []
    for (_, concept), items in groups.items():
        card = dict(items[0])
        card["title"] = concept
        card["chapter"] = clean_chapter(card["chapter"]) or concept
        card.setdefault("explanation", "")
        card.setdefault("sections_json", "[]")
        card.setdefault("accuracy_notes_json", "[]")
        card["content_level"] = "通俗短解释+自然正文+按需小节"
        for duplicate in items[1:]:
            aliases[duplicate["id"]] = card["id"]
        canonical_cards.append(card)

    by_id = {card["id"]: card for card in canonical_cards}
    rows = load_jsonl(batch_path) if batch_path else []
    seen_replace_ids: set[str] = set()
    for row in rows:
        canonical_id = row["canonical_id"]
        card = by_id.get(canonical_id)
        if not card:
            raise ValueError(f"unknown canonical_id: {canonical_id}")
        for replace_id in row["replace_ids"]:
            expected = canonical_id if replace_id == canonical_id else aliases.get(replace_id)
            if expected != canonical_id:
                raise ValueError(f"replace_id {replace_id} does not belong to {canonical_id}")
            if replace_id in seen_replace_ids:
                raise ValueError(f"duplicate replace_id in batch: {replace_id}")
            seen_replace_ids.add(replace_id)
        card.update(
            {
                "subject": row["subject"].strip(),
                "title": row["title"].strip(),
                "chapter": row["chapter"].strip(),
                "summary": row["preview"].strip(),
                "explanation": row["explanation"].strip(),
                "sections_json": json.dumps(row["sections"], ensure_ascii=False),
                "accuracy_notes_json": json.dumps(row["accuracy_notes"], ensure_ascii=False),
                "keywords": "，".join(str(x).strip() for x in row["keywords"] if str(x).strip()),
                "creation_method": "user_ai_rewrite",
                "content_level": "通俗短解释+自然正文+按需小节",
                "content_version": max(int(card.get("content_version", 1)) + 1, 2),
                "review_status": "approved",
            }
        )

    SEED.write_text(json.dumps(canonical_cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    alias_rows = [
        {"alias_id": alias_id, "canonical_id": canonical_id}
        for alias_id, canonical_id in sorted(aliases.items())
    ]
    ALIASES.write_text(
        json.dumps({"schema_version": "2.0", "aliases": alias_rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return len(canonical_cards), len(alias_rows)


def merge_state(db, models, alias_id: str, canonical_id: str) -> None:
    source = db.get(models.LearningState, alias_id)
    if not source:
        return
    target = db.get(models.LearningState, canonical_id)
    if not target:
        target = models.LearningState(card_id=canonical_id)
        db.add(target)
        db.flush()
    rank = {"未接触": 0, "听说过": 1, "知道是什么": 2, "知道怎么用": 3, "实际使用过": 4, "掌握": 5}
    if "需要复习" in {target.status, source.status}:
        target.status = "需要复习"
    elif rank.get(source.status, 0) > rank.get(target.status, 0):
        target.status = source.status
    for field in ("favorite", "deepen_later", "current_course", "competition_use"):
        setattr(target, field, bool(getattr(target, field)) or bool(getattr(source, field)))
    target.view_count = int(target.view_count or 0) + int(source.view_count or 0)
    if source.last_viewed_at and (not target.last_viewed_at or source.last_viewed_at > target.last_viewed_at):
        target.last_viewed_at = source.last_viewed_at
    if source.review_date and (not target.review_date or source.review_date < target.review_date):
        target.review_date = source.review_date
    db.query(models.Note).filter(models.Note.card_id == alias_id).update({"card_id": canonical_id})
    db.delete(source)


def apply_database() -> tuple[int, int, int]:
    sys.path.insert(0, str(ROOT / "program" / "backend"))
    from app import models
    from app.backup import create_backup
    from app.database import SessionLocal

    create_backup("automatic", "content-v2-before-merge")
    cards = json.loads(SEED.read_text(encoding="utf-8"))
    alias_doc = json.loads(ALIASES.read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        card_columns = {column.name for column in models.KnowledgeCard.__table__.columns}
        for item in cards:
            payload = {key: value for key, value in item.items() if key in card_columns and key != "created_at"}
            existing = db.get(models.KnowledgeCard, item["id"])
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
            else:
                db.add(models.KnowledgeCard(**payload))
        db.flush()

        alias_count = 0
        for item in alias_doc.get("aliases", []):
            alias_id, canonical_id = item["alias_id"], item["canonical_id"]
            duplicate = db.get(models.KnowledgeCard, alias_id)
            if duplicate:
                merge_state(db, models, alias_id, canonical_id)
                duplicate.review_status = "merged"
            db.merge(models.KnowledgeCardAlias(alias_id=alias_id, canonical_id=canonical_id))
            alias_count += 1

        archived = 0
        for review in db.query(models.ReviewItem).filter_by(status="pending", item_type="web_update").all():
            if review.title.endswith("：新增公告"):
                review.status = "rejected"
                review.trust_level = "首次来源基线，不是具体公告"
                archived += 1
        db.commit()
        return len(cards), alias_count, archived
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", nargs="?", type=Path)
    parser.add_argument("--prepare-catalog", action="store_true")
    parser.add_argument("--apply-db", action="store_true")
    args = parser.parse_args()
    if not args.prepare_catalog and not args.apply_db:
        parser.error("choose --prepare-catalog and/or --apply-db")
    if args.prepare_catalog:
        cards, aliases = prepare_catalog(args.batch)
        print(f"catalog_cards={cards} aliases={aliases}")
    if args.apply_db:
        cards, aliases, archived = apply_database()
        print(f"database_cards={cards} aliases={aliases} archived_baselines={archived}")


if __name__ == "__main__":
    main()
