import asyncio
import base64
import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from test_application import receipt as reviewed_receipt

import ai


def receipt():
    data = reviewed_receipt()
    data.pop("receipt_hash")
    return data


@pytest.fixture(autouse=True)
def clean_config(monkeypatch):
    for name in (
        "AI_PROVIDER",
        "AI_MODEL",
        "AI_API_KEY",
        "AI_BASE_URL",
        "AI_JSON_MODE",
        "AI_TIMEOUT_SECONDS",
        "AI_MAX_TOKENS",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def test_legacy_and_override(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "legacy-secret")
    assert ai.load_config().model == "gpt-4o-mini"
    assert ai.load_config().api_key == "legacy-secret"
    monkeypatch.setenv("AI_API_KEY", "new-secret")
    monkeypatch.setenv("AI_MODEL", "vision-model")
    config = ai.load_config()
    assert config.api_key == "new-secret"
    assert config.model == "vision-model"
    assert config.json_mode
    assert "secret" not in repr(config)
    assert "secret" not in str(ai.configuration_status())


def test_provider_credentials_are_isolated(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-only")
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setenv("AI_MODEL", "vision-model")
    with pytest.raises(ai.AIConfigurationError):
        ai.load_config()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-only")
    assert ai.load_config().api_key == "anthropic-only"
    monkeypatch.setenv("AI_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AI_BASE_URL", "http://localhost:1234/v1/")
    config = ai.load_config()
    assert config.api_key == ""
    assert config.base_url == "http://localhost:1234/v1"
    assert not config.json_mode


@pytest.mark.parametrize(
    "name,value",
    [
        ("AI_PROVIDER", "secret-invalid-provider"),
        ("AI_BASE_URL", "https://unexpected.example/v1"),
        ("AI_JSON_MODE", "yes"),
        ("AI_TIMEOUT_SECONDS", "0"),
        ("AI_TIMEOUT_SECONDS", "91"),
        ("AI_MAX_TOKENS", "invalid"),
    ],
)
def test_invalid_configuration(monkeypatch, name, value):
    monkeypatch.setenv("AI_API_KEY", "test-secret")
    monkeypatch.setenv(name, value)
    status = ai.configuration_status()
    assert not status["configured"]
    assert "secret" not in str(status)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "file:///tmp/model",
        "https://key@host/v1",
        "https://host/v1?key=secret",
        "http://host:bad/v1",
    ],
)
def test_compatible_url_validation(monkeypatch, url):
    monkeypatch.setenv("AI_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AI_MODEL", "vision-model")
    monkeypatch.setenv("AI_BASE_URL", url)
    with pytest.raises(ai.AIConfigurationError):
        ai.load_config()


def test_other_providers_require_explicit_model(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("OPENAI_MODEL", "must-not-leak")
    with pytest.raises(ai.AIConfigurationError, match="AI_MODEL"):
        ai.load_config()


@pytest.mark.parametrize("provider", ["openai", "openai_compatible"])
async def test_openai_protocol(monkeypatch, provider):
    monkeypatch.setenv("AI_PROVIDER", provider)
    monkeypatch.setenv("AI_API_KEY", "test")
    monkeypatch.setenv("AI_MODEL", "vision-model")
    if provider == "openai_compatible":
        monkeypatch.setenv("AI_BASE_URL", "https://compatible.example/v1")
    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content=json.dumps(receipt())),
                )
            ]
        )
    )
    captured = {}

    def factory(**kwargs):
        captured.update(kwargs)
        context = AsyncMock()
        context.__aenter__.return_value = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )
        return context

    monkeypatch.setattr(ai, "AsyncOpenAI", factory)
    result = await ai.extract_receipt(b"image", "image/png")
    assert result.supermarket == "mercadona"
    assert captured["max_retries"] == 0
    assert captured["base_url"] == ai.load_config().base_url
    payload = create.call_args.kwargs
    assert payload["model"] == "vision-model"
    assert ("response_format" in payload) == (provider == "openai")
    assert payload["messages"][0]["content"][0]["image_url"]["url"].startswith(
        "data:image/png;base64,"
    )


@pytest.mark.parametrize(
    "stop,code,valid,expected",
    [
        ("end_turn", 200, True, None),
        ("max_tokens", 200, True, ai.AIResponseError),
        ("end_turn", 401, True, ai.AIProviderError),
        ("end_turn", 200, False, ai.AIResponseError),
    ],
)
async def test_anthropic_protocol(monkeypatch, stop, code, valid, expected):
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setenv("AI_API_KEY", "test-secret")
    monkeypatch.setenv("AI_MODEL", "vision-model")
    requests = []

    def respond(request):
        requests.append(request)
        assert str(request.url) == "https://api.anthropic.com/v1/messages"
        assert request.headers["x-api-key"] == "test-secret"
        assert request.headers["anthropic-version"] == "2023-06-01"
        payload = json.loads(request.content)
        assert payload["model"] == "vision-model"
        source = payload["messages"][0]["content"][0]["source"]
        assert source["media_type"] == "image/png"
        assert base64.b64decode(source["data"]) == b"image"
        return httpx.Response(
            code,
            json={
                "stop_reason": stop,
                "content": [
                    {
                        "type": "text",
                        "text": "```json\n" + json.dumps(receipt()) + "\n```"
                        if valid
                        else "{}",
                    }
                ],
            },
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        ai.httpx,
        "AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(respond), **kw),
    )
    if expected:
        with pytest.raises(expected) as error:
            await ai.extract_receipt(b"image", "image/png")
        assert "test-secret" not in str(error.value)
    else:
        assert (
            await ai.extract_receipt(b"image", "image/png")
        ).supermarket == "mercadona"
    assert len(requests) == 1


async def test_total_deadline_no_fallback(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "test")
    config = replace(ai.load_config(), timeout=0.01)
    monkeypatch.setattr(ai, "load_config", lambda: config)

    async def slow(*args):
        await asyncio.sleep(5)

    read = AsyncMock(side_effect=slow)
    monkeypatch.setitem(ai.PROVIDERS, "openai", SimpleNamespace(read=read))
    with pytest.raises(ai.AIProviderError, match="tiempo"):
        await ai.extract_receipt(b"image", "image/png")
    assert read.await_count == 1
