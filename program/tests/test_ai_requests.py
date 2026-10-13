from __future__ import annotations

import base64
from io import BytesIO

import pytest
from PIL import Image

from app.ai import build_payload, capability_probe, classify_capability_status, map_reasoning, provider_headers, response_detail
from app.config import write_yaml


def test_responses_payload_uses_store_false_xhigh_images_and_web():
    payload=build_payload(
        "openai_responses","gpt-test",[{"role":"user","content":"分析图片"}],800,"极高",None,
        images=[{"data_url":"data:image/png;base64,AAAA","detail":"high"}],native_web=True,
    )
    assert payload["store"] is False
    assert payload["reasoning"]=={"effort":"xhigh"}
    assert payload["tools"]==[{"type":"web_search"}]
    content=payload["input"][0]["content"]
    assert content[0]=={"type":"input_text","text":"分析图片"}
    assert content[1]["type"]=="input_image"
    assert content[1]["detail"]=="high"


def test_chat_completions_image_shape_and_reasoning_mapping():
    payload=build_payload(
        "openai_chat_completions","deepseek-test",[{"role":"user","content":"看图"}],500,"极高",0.2,
        images=[{"data_url":"data:image/jpeg;base64,AAAA","detail":"low"}],
    )
    assert "store" not in payload
    assert payload["messages"][0]["content"][1]=={
        "type":"image_url","image_url":{"url":"data:image/jpeg;base64,AAAA","detail":"low"}
    }
    assert map_reasoning("极高")=="xhigh"


def test_provider_compatibility_header_is_whitelisted():
    headers=provider_headers({"http_headers":{"x-openai-actor-authorization":"local-image-extension","Authorization":"evil"}},"secret",True)
    assert headers["Authorization"]=="Bearer secret"
    assert headers["x-openai-actor-authorization"]=="local-image-extension"
    assert headers["Content-Type"]=="application/json"


def test_gateway_errors_are_test_failed_not_unsupported():
    assert classify_capability_status(200)=="verified_supported"
    assert classify_capability_status(400)=="verified_unsupported"
    assert classify_capability_status(502)=="test_failed"
    detail=response_detail(502,b"<!DOCTYPE html><html>bad gateway</html>","text/html")
    assert "不代表模型不支持" in detail


@pytest.mark.asyncio
async def test_chat_completions_native_web_is_not_falsely_claimed():
    result=await capability_probe("deepseek","any-model","web_search")
    assert result["status"]=="verified_unsupported"
    assert result["may_cost"] is False
    assert "后端公开网页检索" in result["detail"]


def _png_bytes() -> bytes:
    target=BytesIO()
    Image.new("RGB",(2,2),(49,214,196)).save(target,format="PNG")
    return target.getvalue()


def test_chat_endpoint_passes_real_image_and_backend_search(client,monkeypatch):
    write_yaml("ai_providers.yaml",{"providers":[{
        "id":"deepseek","display_name":"DeepSeek","protocol":"openai_chat_completions",
        "base_url":"https://api.deepseek.com","api_key_env":"DEEPSEEK_API_KEY",
        "models":[{"id":"deepseek-test","image_input":"verified_supported","web_search":"verified_unsupported"}],
    }]})
    upload=client.post("/api/media/upload",files={"file":("probe.png",_png_bytes(),"image/png")})
    assert upload.status_code==200
    asset_id=upload.json()["id"]
    captured={}

    async def fake_search(query):
        assert query=="联网分析这张图"
        return [{"title":"测试来源","url":"https://example.com/source","snippet":"公开摘要"}]

    async def fake_chat(provider_id,model,messages,max_output,reasoning,temperature,images=None,native_web=False):
        captured.update({"messages":messages,"images":images,"native_web":native_web})
        return "完成",{"input":12,"output":3}

    monkeypatch.setattr("app.main.search_public_web",fake_search)
    monkeypatch.setattr("app.main.chat",fake_chat)
    response=client.post("/api/ai/chat",json={
        "provider_id":"deepseek","model":"deepseek-test","message":"联网分析这张图",
        "reasoning":"极高","max_output":256,"image_asset_ids":[asset_id],"image_detail":"high",
        "allow_web":True,"consent":True,
    })
    assert response.status_code==200,response.text
    body=response.json()
    assert body["network_mode"]=="backend_public_search"
    assert body["web_sources"][0]["url"]=="https://example.com/source"
    assert body["sent_attachments"]
    assert captured["native_web"] is False
    assert captured["images"][0]["detail"]=="high"
    data_url=captured["images"][0]["data_url"]
    assert data_url.startswith("data:image/png;base64,")
    assert base64.b64decode(data_url.split(",",1)[1])==_png_bytes()
    assert any("测试来源" in str(message["content"]) for message in captured["messages"])
