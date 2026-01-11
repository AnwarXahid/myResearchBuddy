from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

import httpx
from pydantic import BaseModel, ValidationError


class LLMClient(ABC):
    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    def _enforce_schema(
        self, raw_text: str, response_schema: Optional[Type[BaseModel]]
    ) -> Dict[str, Any]:
        if response_schema is None:
            return {"text": raw_text}
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON output: {exc}") from exc
        try:
            validated = response_schema.model_validate(data)
        except ValidationError as exc:
            raise ValueError(f"Schema validation failed: {exc}") from exc
        return validated.model_dump()


class GeminiClient(LLMClient):
    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
        prompt_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json" if response_schema else "text/plain",
            },
        }
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        candidate = data.get("candidates", [{}])[0]
        text = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
        try:
            return self._enforce_schema(text, response_schema)
        except ValueError:
            if response_schema is None:
                raise
            repair_prompt = (
                "Return ONLY valid JSON that matches the schema. Do not include commentary.\n"
                + text
            )
            payload["contents"][0]["parts"][0]["text"] = repair_prompt
            with httpx.Client(timeout=60) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
            candidate = data.get("candidates", [{}])[0]
            text = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
            return self._enforce_schema(text, response_schema)


class OpenAIClient(LLMClient):
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = "https://api.openai.com/v1"

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"} if response_schema else None,
        }
        with httpx.Client(timeout=60) as client:
            resp = client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        text = data["choices"][0]["message"]["content"]
        try:
            return self._enforce_schema(text, response_schema)
        except ValueError:
            if response_schema is None:
                raise
            repair_messages = messages + [
                {"role": "system", "content": "Return ONLY valid JSON."},
                {"role": "user", "content": text},
            ]
            payload["messages"] = repair_messages
            with httpx.Client(timeout=60) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
                resp.raise_for_status()
                data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return self._enforce_schema(text, response_schema)


class AnthropicClient(LLMClient):
    def __init__(self) -> None:
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.base_url = "https://api.anthropic.com/v1/messages"

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        with httpx.Client(timeout=60) as client:
            resp = client.post(self.base_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        text = data["content"][0]["text"]
        try:
            return self._enforce_schema(text, response_schema)
        except ValueError:
            if response_schema is None:
                raise
            repair_messages = messages + [
                {"role": "assistant", "content": text},
                {"role": "user", "content": "Return ONLY valid JSON."},
            ]
            payload["messages"] = repair_messages
            with httpx.Client(timeout=60) as client:
                resp = client.post(self.base_url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            text = data["content"][0]["text"]
            return self._enforce_schema(text, response_schema)


def get_client(provider: str) -> LLMClient:
    provider = provider.lower()
    if provider == "gemini":
        return GeminiClient()
    if provider == "openai":
        return OpenAIClient()
    if provider == "anthropic":
        return AnthropicClient()
    raise ValueError(f"Unknown provider: {provider}")
