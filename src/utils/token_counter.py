from __future__ import annotations

import importlib
import logging
import math
from typing import Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)


class TokenCounter:
    """Unified token counting for memory budgets."""

    def __init__(self, llm: Optional[BaseChatModel], fallback_chars_per_token: int = 3):
        self.llm = llm
        self.fallback_ratio = max(1, fallback_chars_per_token)
        self._get_num_tokens = self._resolve_get_num_tokens(llm)
        self._anthropic_count_tokens = self._resolve_anthropic_count_tokens()

    def count(self, text: str) -> int:
        if not text:
            return 0

        if self._get_num_tokens is not None:
            try:
                return max(0, int(self._get_num_tokens(text)))
            except Exception:
                logger.debug("LLM tokenizer failed; falling back to heuristic token estimate.", exc_info=True)

        if self._looks_like_anthropic_llm(self.llm) and self._anthropic_count_tokens is not None:
            try:
                return max(0, int(self._anthropic_count_tokens(text)))
            except Exception:
                logger.debug("Anthropic tokenizer failed; falling back to heuristic token estimate.", exc_info=True)

        return self._fallback_count(text, chars_per_token=4 if self._looks_like_anthropic_llm(self.llm) else self.fallback_ratio)

    def count_from_api_usage(self, response: Any) -> int:
        usage = self._extract_usage_dict(response)
        if not usage:
            return 0

        total = self._as_int(usage.get("total_tokens"))
        if total is not None:
            return total

        input_tokens = self._as_int(usage.get("input_tokens"))
        if input_tokens is None:
            input_tokens = self._as_int(usage.get("prompt_tokens"))
        if input_tokens is None:
            input_tokens = self._as_int(usage.get("prompt_token_count"))

        output_tokens = self._as_int(usage.get("output_tokens"))
        if output_tokens is None:
            output_tokens = self._as_int(usage.get("completion_tokens"))
        if output_tokens is None:
            output_tokens = self._as_int(usage.get("completion_token_count"))

        if input_tokens is None and output_tokens is None:
            return 0
        return max(0, (input_tokens or 0) + (output_tokens or 0))

    def _fallback_count(self, text: str, chars_per_token: int) -> int:
        if not text:
            return 0
        return max(1, math.ceil(len(text) / max(1, chars_per_token)))

    def _resolve_get_num_tokens(self, llm: Optional[BaseChatModel]):
        candidate = self._unwrap_bound_llm(llm)
        for model in (llm, candidate):
            if model is None:
                continue
            fn = getattr(model, "get_num_tokens", None)
            if callable(fn):
                return fn
        return None

    def _resolve_anthropic_count_tokens(self):
        try:
            module = importlib.import_module("anthropic")
        except Exception:
            return None
        fn = getattr(module, "count_tokens", None)
        if callable(fn):
            return fn
        return None

    def _looks_like_anthropic_llm(self, llm: Optional[BaseChatModel]) -> bool:
        if llm is None:
            return False
        candidate = self._unwrap_bound_llm(llm)
        identity_parts = []
        for model in (llm, candidate):
            if model is None:
                continue
            identity_parts.extend(
                [
                    model.__class__.__name__,
                    str(getattr(model, "model_name", "")),
                    str(getattr(model, "model", "")),
                    str(getattr(model, "base_url", "")),
                ]
            )
        identity = " ".join(part.lower() for part in identity_parts if part)
        return "anthropic" in identity or "claude" in identity

    def _unwrap_bound_llm(self, llm: Any) -> Any:
        current = llm
        seen: set[int] = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            next_bound = getattr(current, "bound", None)
            if next_bound is None:
                break
            current = next_bound
        return current

    def _extract_usage_dict(self, response: Any) -> dict[str, Any]:
        candidates = []
        if isinstance(response, dict):
            candidates.append(response.get("token_usage"))
            candidates.append(response.get("usage"))
        metadata = getattr(response, "response_metadata", None)
        if isinstance(metadata, dict):
            candidates.append(metadata.get("token_usage"))
            candidates.append(metadata.get("usage"))
        usage_metadata = getattr(response, "usage_metadata", None)
        if isinstance(usage_metadata, dict):
            candidates.append(usage_metadata)

        for item in candidates:
            if isinstance(item, dict):
                return item
        return {}

    def _as_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
