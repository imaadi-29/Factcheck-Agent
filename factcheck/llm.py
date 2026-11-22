"""The AI model (LLM) wrapper. We use Google Gemini through the official google-genai SDK.

Gemini model names change often, so if no model is configured we ask the API which
"Flash" models exist and use the newest one, falling back to the next if it fails.
"""

import json
import re
import time

from google import genai
from google.genai import types

SKIP_WORDS = ("lite", "live", "tts", "image", "audio", "transcribe", "embedding",
              "omni", "thinking", "exp", "preview", "8b", "robotics", "computer")


class LLMError(Exception):
    pass


def _version_key(name: str):
    numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", name)]
    return numbers or [0.0]


_MODEL_LIST_CACHE: dict = {}   # remembered between runs so we only ask Google once


class GeminiLLM:
    def __init__(self, api_key: str, model: str = ""):
        self.client = genai.Client(api_key=api_key)
        if model:
            self.models = [model]
        else:
            key = hash(api_key)
            if key not in _MODEL_LIST_CACHE:
                _MODEL_LIST_CACHE[key] = self._discover_models()
            self.models = _MODEL_LIST_CACHE[key]
        self.active_model = self.models[0]
        self.thinking_supported = True

    def _config(self, thinking: str | None):
        """Lower 'thinking' = faster answers. Models that don't support the setting get none."""
        if thinking and self.thinking_supported:
            return types.GenerateContentConfig(
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(thinking_level=thinking),
            )
        return types.GenerateContentConfig(response_mime_type="application/json")

    def _discover_models(self) -> list[str]:
        try:
            names = []
            for m in self.client.models.list():
                actions = getattr(m, "supported_actions", None) or []
                name = (m.name or "").replace("models/", "")
                if ("generateContent" in actions and "flash" in name
                        and not any(w in name for w in SKIP_WORDS)):
                    names.append(name)
            names.sort(key=_version_key, reverse=True)
        except Exception:
            names = []
        # "gemini-flash-latest" is Google's alias for the current Flash model.
        return names[:3] + ["gemini-flash-latest"] if names else ["gemini-flash-latest"]

    def generate_json(self, prompt: str, thinking: str | None = None) -> dict:
        """Send a prompt and return the parsed JSON reply, with retries and model fallback.

        thinking: "low" or "medium" asks the model to reason less, which is much faster.
        """
        last_error = None
        for model in list(self.models):
            for attempt in range(3):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=self._config(thinking),
                    )
                    self.active_model = model
                    return _parse_json(response.text or "")
                except json.JSONDecodeError as exc:
                    last_error = exc          # malformed reply: just try again
                except Exception as exc:
                    last_error = exc
                    message = str(exc).lower()
                    if "thinking" in message and self.thinking_supported:
                        self.thinking_supported = False   # model rejects the setting: retry without it
                        continue
                    if "not found" in message or "404" in message or "limit: 0" in message:
                        break                 # this model is unavailable: try the next one
                    if "429" in message or "resource_exhausted" in message or "503" in message \
                            or "unavailable" in message or "overloaded" in message:
                        time.sleep(8 * (attempt + 1))   # rate limited / busy: wait and retry
                        continue
                    if "api key" in message or "permission" in message or "401" in message \
                            or "403" in message:
                        raise LLMError("The Gemini API key was rejected. Check GEMINI_API_KEY.") from exc
                    time.sleep(2)
        raise LLMError(f"The AI model did not respond successfully: {str(last_error)[:300]}")


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    return json.loads(text)
