from __future__ import annotations
import json
from typing import Any
import httpx
from .config import read_yaml, read_private_yaml, read_secrets

class AiError(RuntimeError): pass

ALLOWED_PROVIDER_HEADERS={"x-openai-actor-authorization"}

def provider_headers(provider:dict[str,Any],key:str,content_type:bool=False) -> dict[str,str]:
    headers={"Authorization":f"Bearer {key}"}
    if content_type:headers["Content-Type"]="application/json"
    for raw_name,raw_value in (provider.get("http_headers") or {}).items():
        name=str(raw_name).strip().lower();value=str(raw_value).strip()
        if name in ALLOWED_PROVIDER_HEADERS and value and len(value)<=200 and "\r" not in value and "\n" not in value:
            headers[name]=value
    return headers

def classify_capability_status(status:int) -> str:
    if status<400:return "verified_supported"
    if status>=500 or status in {401,403,404,405,408,409,425,429}:return "test_failed"
    return "verified_unsupported"

def response_detail(status:int,body:bytes,content_type:str="") -> str:
    text=body.decode("utf-8","replace").strip()
    if "text/html" in content_type.lower() or text[:100].lower().startswith(("<!doctype html","<html")):
        return f"服务商返回 HTML 错误页（HTTP {status}）：网关、接口路由或上游服务异常，不代表模型不支持。"
    try:
        data=json.loads(text)
        error=data.get("error",{}) if isinstance(data,dict) else {}
        message=error.get("message") if isinstance(error,dict) else None
        return str(message or (data.get("message") if isinstance(data,dict) else "") or text)[:300]
    except Exception:
        return text[:300] or f"HTTP {status}"

def safe_providers() -> list[dict[str, Any]]:
    secrets = read_secrets()
    defaults = read_yaml("ai_providers.yaml", {"providers": []})
    providers = read_private_yaml("ai_providers.yaml", defaults).get("providers", [])
    clean = []
    for p in providers:
        item = dict(p)
        item["configured"] = bool(secrets.get(item.get("api_key_env", "")))
        item.pop("api_key", None)
        clean.append(item)
    return clean

def get_provider(provider_id: str) -> tuple[dict[str, Any], str]:
    provider = next((x for x in safe_providers() if x.get("id") == provider_id), None)
    if not provider: raise AiError("未找到服务商配置")
    key = read_secrets().get(provider.get("api_key_env", ""), "")
    if not key: raise AiError("该服务商尚未配置 API Key")
    return provider, key

async def list_models(provider_id: str) -> list[str]:
    p, key = get_provider(provider_id)
    base = p.get("base_url", "").rstrip("/")
    url = f"{base}/models"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, headers=provider_headers(p,key))
        r.raise_for_status()
        return [m["id"] for m in r.json().get("data", []) if isinstance(m, dict) and m.get("id")]

def map_reasoning(level: str) -> str | None:
    return {"低":"low","中":"medium","高":"high","极高":"xhigh","自动":None,"无":None}.get(level)

def _with_images(messages: list[dict[str, Any]], images: list[dict[str, str]], responses: bool) -> list[dict[str, Any]]:
    copied = [dict(message) for message in messages]
    if not images:
        return copied
    user_index = next((i for i in range(len(copied) - 1, -1, -1) if copied[i].get("role") == "user"), None)
    if user_index is None:
        raise AiError("图片请求缺少用户消息")
    text = str(copied[user_index].get("content", ""))
    if responses:
        content: list[dict[str, Any]] = [{"type": "input_text", "text": text}]
        content.extend({"type": "input_image", "image_url": image["data_url"], "detail": image["detail"]} for image in images)
    else:
        content = [{"type": "text", "text": text}]
        content.extend({"type": "image_url", "image_url": {"url": image["data_url"], "detail": image["detail"]}} for image in images)
    copied[user_index]["content"] = content
    return copied


def build_payload(
    protocol: str,
    model: str,
    messages: list[dict[str, Any]],
    max_output: int,
    reasoning: str,
    temperature: float | None,
    images: list[dict[str, str]] | None = None,
    native_web: bool = False,
) -> dict[str, Any]:
    responses = protocol == "openai_responses"
    request_messages = _with_images(messages, images or [], responses)
    if responses:
        payload: dict[str, Any] = {
            "model": model,
            "input": request_messages,
            "max_output_tokens": max_output,
            "store": False,
        }
        effort = map_reasoning(reasoning)
        if effort:
            payload["reasoning"] = {"effort": effort}
        if temperature is not None:
            payload["temperature"] = temperature
        if native_web:
            payload["tools"] = [{"type": "web_search"}]
        return payload
    payload = {"model": model, "messages": request_messages, "max_tokens": max_output}
    if temperature is not None:
        payload["temperature"] = temperature
    return payload


def _response_sources(data: Any) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    seen: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("type") == "url_citation" and value.get("url"):
                url = str(value["url"])
                if url not in seen:
                    seen.add(url)
                    sources.append({"title": str(value.get("title") or url), "url": url, "snippet": ""})
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(data.get("output", []) if isinstance(data, dict) else data)
    return sources


async def chat(
    provider_id: str,
    model: str,
    messages: list[dict[str, Any]],
    max_output: int,
    reasoning: str,
    temperature: float | None,
    images: list[dict[str, str]] | None = None,
    native_web: bool = False,
) -> tuple[str, dict[str, Any]]:
    p, key = get_provider(provider_id)
    base = p.get("base_url", "").rstrip("/")
    headers = provider_headers(p,key,content_type=True)
    protocol = p.get("protocol", "openai_chat_completions")
    payload = build_payload(protocol, model, messages, max_output, reasoning, temperature, images, native_web)
    url = f"{base}/{'responses' if protocol == 'openai_responses' else 'chat/completions'}"
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code >= 400:
            raise AiError(f"API 请求失败（HTTP {r.status_code}）：{response_detail(r.status_code,r.content,r.headers.get('content-type',''))}")
        data = r.json()
    if protocol == "openai_responses":
        text = data.get("output_text") or "".join(c.get("text", "") for o in data.get("output", []) for c in o.get("content", []) if c.get("type") in {"output_text","text"})
    else:
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})
    result_usage: dict[str, Any] = {
        "input": usage.get("input_tokens", usage.get("prompt_tokens", 0)),
        "output": usage.get("output_tokens", usage.get("completion_tokens", 0)),
    }
    if protocol == "openai_responses":
        result_usage["web_sources"] = _response_sources(data)
    return text, result_usage

async def capability_probe(provider_id:str,model:str,capability:str,reasoning:str="低") -> dict[str,Any]:
    p,key=get_provider(provider_id);base=p.get("base_url","").rstrip("/");responses=p.get("protocol")=="openai_responses";url=f"{base}/{'responses' if responses else 'chat/completions'}";headers=provider_headers(p,key,content_type=True)
    tiny_png="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2nE0AAAAASUVORK5CYII="
    if capability=="web_search" and not responses:
        return {"capability":capability,"status":"verified_unsupported","detail":"Chat Completions 兼容协议没有标准原生联网工具；本站仍可使用后端公开网页检索。","may_cost":False}
    if responses:
        payload:dict[str,Any]={"model":model,"input":"只回复 OK","max_output_tokens":16,"store":False}
        if capability=="stream":payload["stream"]=True
        elif capability=="json":payload.update({"input":"返回字段 ok=true","text":{"format":{"type":"json_schema","name":"probe","strict":True,"schema":{"type":"object","properties":{"ok":{"type":"boolean"}},"required":["ok"],"additionalProperties":False}}}})
        elif capability=="image":payload["input"]=[{"role":"user","content":[{"type":"input_text","text":"这是一张程序内置测试图，只回复 OK"},{"type":"input_image","image_url":tiny_png}]}]
        elif capability=="reasoning":payload["reasoning"]={"effort":map_reasoning(reasoning) or "low"}
        elif capability=="tools":payload.update({"input":"调用 probe 工具","tools":[{"type":"function","name":"probe","description":"能力测试","parameters":{"type":"object","properties":{},"additionalProperties":False}}],"tool_choice":"required"})
        elif capability=="max_output":payload["max_output_tokens"]=1
        elif capability=="web_search":payload.update({"input":"搜索 OpenAI 官方网站，只回复 OK","tools":[{"type":"web_search"}]})
    else:
        payload={"model":model,"messages":[{"role":"user","content":"只回复 OK"}],"max_tokens":16}
        if capability=="stream":payload["stream"]=True
        elif capability=="json":payload.update({"messages":[{"role":"user","content":"返回字段 ok=true 的 JSON"}],"response_format":{"type":"json_object"}})
        elif capability=="image":payload["messages"]=[{"role":"user","content":[{"type":"text","text":"这是一张程序内置测试图，只回复 OK"},{"type":"image_url","image_url":{"url":tiny_png,"detail":"low"}}]}]
        elif capability=="reasoning":payload["reasoning_effort"]=map_reasoning(reasoning) or "low"
        elif capability=="tools":payload.update({"messages":[{"role":"user","content":"调用 probe 工具"}],"tools":[{"type":"function","function":{"name":"probe","description":"能力测试","parameters":{"type":"object","properties":{}}}}],"tool_choice":"required"})
        elif capability=="max_output":payload["max_tokens"]=1
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            async with client.stream("POST",url,headers=headers,json=payload) as r:
                body=(await r.aread())[:1000];status=r.status_code;content_type=r.headers.get("content-type","")
        return {"capability":capability,"status":classify_capability_status(status),"http_status":status,"detail":response_detail(status,body,content_type),"may_cost":True,"uses_builtin_image":capability=="image"}
    except Exception as e:return {"capability":capability,"status":"test_failed","detail":str(e)[:300],"may_cost":True,"uses_builtin_image":capability=="image"}
