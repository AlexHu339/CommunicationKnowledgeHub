from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

def now() -> datetime: return datetime.utcnow()

class KnowledgeCard(Base):
    __tablename__ = "knowledge_cards"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    subject: Mapped[str] = mapped_column(String(80), index=True)
    chapter: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(160), index=True)
    summary: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text, default="")
    sections_json: Mapped[str] = mapped_column(Text, default="[]")
    accuracy_notes_json: Mapped[str] = mapped_column(Text, default="[]")
    why_exists: Mapped[str] = mapped_column(Text)
    problem_solved: Mapped[str] = mapped_column(Text)
    intuition: Mapped[str] = mapped_column(Text)
    inputs: Mapped[str] = mapped_column(Text)
    outputs: Mapped[str] = mapped_column(Text)
    common_uses: Mapped[str] = mapped_column(Text)
    engineering_use: Mapped[str] = mapped_column(Text)
    simple_example: Mapped[str] = mapped_column(Text)
    misconceptions: Mapped[str] = mapped_column(Text)
    prerequisites: Mapped[str] = mapped_column(Text, default="")
    related: Mapped[str] = mapped_column(Text, default="")
    next_steps: Mapped[str] = mapped_column(Text)
    keywords: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    content_level: Mapped[str] = mapped_column(String(40), default="认识+理解")
    visual_template: Mapped[str | None] = mapped_column(String(80), nullable=True)
    visual_params: Mapped[str] = mapped_column(Text, default="{}")
    source: Mapped[str] = mapped_column(Text)
    creation_method: Mapped[str] = mapped_column(String(30), default="seed")
    review_status: Mapped[str] = mapped_column(String(30), default="approved", index=True)
    content_version: Mapped[int] = mapped_column(Integer, default=1)
    competition_relevant: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class LearningState(Base):
    __tablename__ = "learning_states"
    card_id: Mapped[str] = mapped_column(ForeignKey("knowledge_cards.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(30), default="未接触", index=True)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deepen_later: Mapped[bool] = mapped_column(Boolean, default=False)
    current_course: Mapped[bool] = mapped_column(Boolean, default=False)
    competition_use: Mapped[bool] = mapped_column(Boolean, default=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    last_viewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[str | None] = mapped_column(ForeignKey("knowledge_cards.id", ondelete="CASCADE"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), default="个人笔记")
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

class Relationship(Base):
    __tablename__ = "relationships"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("knowledge_cards.id", ondelete="CASCADE"), index=True)
    target_id: Mapped[str] = mapped_column(ForeignKey("knowledge_cards.id", ondelete="CASCADE"), index=True)
    relation_type: Mapped[str] = mapped_column(String(30))
    __table_args__ = (UniqueConstraint("source_id", "target_id", "relation_type"),)

class KnowledgeCardAlias(Base):
    __tablename__ = "knowledge_card_aliases"
    alias_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    canonical_id: Mapped[str] = mapped_column(ForeignKey("knowledge_cards.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class ReviewItem(Base):
    __tablename__ = "review_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_type: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(200))
    payload_json: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    diff_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    trust_level: Mapped[str] = mapped_column(String(20), default="待核实")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Policy(Base):
    __tablename__ = "policies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(240))
    institution: Mapped[str] = mapped_column(String(160))
    admission_year: Mapped[int] = mapped_column(Integer, default=2028, index=True)
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    original_text: Mapped[str] = mapped_column(Text)
    snapshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str] = mapped_column(Text)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True)
    superseded: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="approved")

class UniversityProgram(Base):
    __tablename__ = "university_programs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school: Mapped[str] = mapped_column(String(100), index=True)
    province: Mapped[str] = mapped_column(String(40), index=True)
    city: Mapped[str] = mapped_column(String(50))
    college: Mapped[str] = mapped_column(String(120))
    program_code: Mapped[str] = mapped_column(String(30))
    program_name: Mapped[str] = mapped_column(String(120))
    degree_type: Mapped[str] = mapped_column(String(20))
    research_direction: Mapped[str] = mapped_column(Text, default="未找到或待核实")
    exam_subjects: Mapped[str] = mapped_column(Text, default="未找到或待核实")
    math_type: Mapped[str] = mapped_column(String(40), default="未找到或待核实")
    english_type: Mapped[str] = mapped_column(String(40), default="未找到或待核实")
    professional_exam: Mapped[str] = mapped_column(Text, default="未找到或待核实")
    reference_books: Mapped[str] = mapped_column(Text, default="未找到或待核实")
    enrollment_plan: Mapped[str] = mapped_column(String(80), default="未找到或待核实")
    recommendation_count: Mapped[str] = mapped_column(String(80), default="未找到或待核实")
    unified_exam_slots: Mapped[str] = mapped_column(String(80), default="未找到或待核实")
    retest_line: Mapped[str] = mapped_column(String(80), default="未找到或待核实")
    retest_ratio: Mapped[str] = mapped_column(String(80), default="未找到或待核实")
    retest_subjects: Mapped[str] = mapped_column(Text, default="未找到或待核实")
    duration: Mapped[str] = mapped_column(String(40), default="未找到或待核实")
    tuition: Mapped[str] = mapped_column(String(80), default="未找到或待核实")
    scholarship: Mapped[str] = mapped_column(Text, default="未找到或待核实")
    source_url: Mapped[str] = mapped_column(Text)
    data_year: Mapped[int] = mapped_column(Integer)
    missing_fields: Mapped[str] = mapped_column(Text, default="")
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    user_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

class SourceRecord(Base):
    __tablename__ = "source_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(80), index=True)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(30))
    snapshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class AiConversation(Base):
    __tablename__ = "ai_conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str] = mapped_column(Text, default="")
    context_strategy: Mapped[str] = mapped_column(String(30), default="summary_recent")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

class AiMessage(Base):
    __tablename__ = "ai_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("ai_conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class AiUsage(Base):
    __tablename__ = "ai_usage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(60), index=True)
    model: Mapped[str] = mapped_column(String(100))
    feature: Mapped[str] = mapped_column(String(60))
    reasoning: Mapped[str] = mapped_column(String(20), default="无")
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_count: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_only: Mapped[bool] = mapped_column(Boolean, default=True)
    success: Mapped[bool] = mapped_column(Boolean)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)

class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

class UserAccount(Base):
    __tablename__ = "user_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_accounts.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)

class MediaAsset(Base):
    __tablename__ = "media_assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    local_path: Mapped[str] = mapped_column(Text)
    original_page: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(160), nullable=True)
    license: Mapped[str] = mapped_column(String(120), default="用户上传，仅本地使用")
    downloaded_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    usage_scope: Mapped[str] = mapped_column(String(120), default="个人学习")
    card_id: Mapped[str | None] = mapped_column(ForeignKey("knowledge_cards.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    ocr_text: Mapped[str] = mapped_column(Text, default="")
