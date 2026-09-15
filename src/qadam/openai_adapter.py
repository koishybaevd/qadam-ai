from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


RESPONSES_URL = "https://api.openai.com/v1/responses"


class OpenAIIntentClassifier:
    """Classify an intent without allowing the model to supply service facts."""

    def __init__(self, api_key: str, model: str, timeout: float = 12.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @classmethod
    def from_environment(cls) -> OpenAIIntentClassifier | None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "").strip()
        if not api_key or not model:
            return None
        return cls(api_key=api_key, model=model)

    def classify(
        self,
        message: str,
        locale: str,
        services: list[dict[str, Any]],
    ) -> tuple[str | None, float] | None:
        candidates = [
            {
                "id": service["id"],
                "title": service["title"][locale],
                "keywords": service["keywords"][locale],
            }
            for service in services
        ]
        allowed_ids = [candidate["id"] for candidate in candidates]
        schema = {
            "type": "object",
            "properties": {
                "service_id": {
                    "type": ["string", "null"],
                    "enum": [*allowed_ids, None],
                },
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["service_id", "confidence"],
            "additionalProperties": False,
        }
        body = {
            "model": self.model,
            "store": False,
            "instructions": (
                "Classify the user's intent into exactly one supplied service ID. "
                "Return null when none fits. Do not answer the request and do not infer service facts."
            ),
            "input": json.dumps(
                {"locale": locale, "message": message, "candidates": candidates},
                ensure_ascii=False,
            ),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "qadam_intent_match",
                    "strict": True,
                    "schema": schema,
                }
            },
            "max_output_tokens": 120,
        }

        try:
            response = self._post(body)
            result = json.loads(_extract_output_text(response))
            service_id = result.get("service_id")
            confidence = float(result.get("confidence", 0))
            if service_id not in {*allowed_ids, None}:
                return None
            return service_id, max(0.0, min(confidence, 1.0))
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            RESPONSES_URL,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            # Do not expose response bodies: they may contain request details.
            raise OSError(f"OpenAI API returned HTTP {error.code}") from error


def _extract_output_text(response: dict[str, Any]) -> str:
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return str(content["text"])
    raise ValueError("The response did not contain output text")

