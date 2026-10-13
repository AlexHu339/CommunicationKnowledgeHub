from datetime import date
from typing import Any, Literal
from pydantic import BaseModel, Field, HttpUrl, field_validator

LearningStatus = Literal["未接触","听说过","知道是什么","知道怎么用","实际使用过","掌握","需要复习"]

class StateUpdate(BaseModel):
    status: LearningStatus | None = None
    favorite: bool | None = None
    deepen_later: bool | None = None
    current_course: bool | None = None
    competition_use: bool | None = None
    review_date: date | None = None
    viewed: bool = False

class NoteInput(BaseModel):
    card_id: str | None = None
    title: str = Field(default="个人笔记", max_length=200)
    content: str = Field(min_length=1, max_length=50000)

class ProviderSave(BaseModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    display_name: str = Field(min_length=1, max_length=80)
    protocol: Literal["openai_chat_completions","openai_responses"]
    base_url: str
    api_key: str | None = Field(default=None, min_length=8)
    api_key_env: str
    models: list[dict[str, Any]] = Field(default_factory=list)
    http_headers: dict[str, str] = Field(default_factory=dict)

    @field_validator("http_headers")
    @classmethod
    def validate_http_headers(cls, value: dict[str, str]) -> dict[str, str]:
        allowed={"x-openai-actor-authorization"}
        clean:dict[str,str]={}
        for raw_name,raw_value in value.items():
            name=raw_name.strip().lower();header_value=raw_value.strip()
            if name not in allowed:raise ValueError(f"不允许的自定义请求头：{raw_name}")
            if not header_value or len(header_value)>200 or "\r" in header_value or "\n" in header_value:raise ValueError("自定义请求头值无效")
            clean[name]=header_value
        return clean

class ChatInput(BaseModel):
    conversation_id: str | None = None
    provider_id: str
    model: str
    message: str = Field(min_length=1, max_length=50000)
    card_id: str | None = None
    include_card: bool = True
    selected_note_ids: list[int] = Field(default_factory=list)
    reasoning: str = "自动"
    max_output: int = Field(default=1200, ge=64, le=16000)
    temperature: float | None = Field(default=None, ge=0, le=2)
    image_asset_ids: list[int] = Field(default_factory=list, max_length=4)
    image_detail: Literal["auto","low","high"] = "low"
    allow_web: bool = False
    consent: bool = False

class LoginInput(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=8, max_length=200)

class ReviewAction(BaseModel):
    action: Literal["accept","reject","draft"]
    edited_payload: dict[str, Any] | None = None
    trust_level: str | None = None

class SourceCheckInput(BaseModel):
    source_ids: list[str] | None = None

class GenerateCardInput(BaseModel):
    subject: str = Field(min_length=2, max_length=80)
    topic: str = Field(min_length=2, max_length=160)
    provider_id: str
    model: str
    consent: bool = False

class CapabilityTestInput(BaseModel):
    model: str
    capability: Literal["text","stream","json","image","reasoning","tools","max_output","web_search"]
    reasoning: str = "低"
