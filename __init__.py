"""Alibaba DashScope image generation backend."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    error_response,
    resolve_aspect_ratio,
    save_url_image,
    success_response,
)

logger = logging.getLogger(__name__)

DASHSCOPE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

# Hermes aspect_ratio -> DashScope size string
_ASPECT_TO_SIZE = {
    "landscape": "1024*768",
    "square": "1024*1024",
    "portrait": "768*1024",
}


class AlibabaImageGenProvider(ImageGenProvider):
    """Alibaba DashScope Wan2.7 image generation backend."""

    @property
    def name(self) -> str:
        return "alibaba"

    @property
    def display_name(self) -> str:
        return "Alibaba DashScope"

    def is_available(self) -> bool:
        if not os.environ.get("DASHSCOPE_API_KEY"):
            return False
        try:
            import requests  # noqa: F401
        except ImportError:
            return False
        return True

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "wan2.7-image",
                "display": "Wan2.7 Image (Standard)",
                "speed": "~fast",
                "strengths": "Good general-purpose image generation",
                "price": "pay-per-use",
            },
            {
                "id": "wan2.7-image-pro",
                "display": "Wan2.7 Image Pro (Premium)",
                "speed": "~medium",
                "strengths": "Higher resolution, better prompt adherence",
                "price": "pay-per-use",
            },
        ]

    def default_model(self) -> Optional[str]:
        return "wan2.7-image"

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Alibaba DashScope",
            "badge": "paid",
            "tag": "Wan2.7 image generation via DashScope",
            "env_vars": [
                {
                    "key": "DASHSCOPE_API_KEY",
                    "prompt": "DashScope API Key",
                    "url": "https://help.aliyun.com/zh/model-studio/get-api-key",
                },
            ],
        }

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        prompt = (prompt or "").strip()
        aspect = resolve_aspect_ratio(aspect_ratio)
        if not prompt:
            return error_response(
                error="Prompt is required",
                error_type="invalid_argument",
                provider="alibaba",
                aspect_ratio=aspect,
            )

        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            return error_response(
                error="DASHSCOPE_API_KEY not set",
                error_type="auth_required",
                provider="alibaba",
                aspect_ratio=aspect,
                prompt=prompt,
            )

        size = _ASPECT_TO_SIZE.get(aspect, "1024*1024")
        payload: Dict[str, Any] = {
            "model": kwargs.get("model", "wan2.7-image"),
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ]
            },
            "parameters": {
                "size": size,
                "n": 1,
                "watermark": False,
                "thinking_mode": False,
            },
        }

        try:
            import requests
        except ImportError:
            return error_response(
                error="requests package not installed",
                error_type="missing_dependency",
                provider="alibaba",
                aspect_ratio=aspect,
                prompt=prompt,
            )

        try:
            resp = requests.post(
                DASHSCOPE_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
        except Exception as exc:
            return error_response(
                error=f"DashScope request failed: {exc}",
                error_type="api_error",
                provider="alibaba",
                aspect_ratio=aspect,
                prompt=prompt,
            )

        try:
            data = resp.json()
        except Exception as exc:
            return error_response(
                error=f"Invalid JSON response: {exc}",
                error_type="parse_error",
                provider="alibaba",
                aspect_ratio=aspect,
                prompt=prompt,
            )

        # Normalize response shape
        output = data.get("output", data)
        choices = output.get("choices", []) if isinstance(output, dict) else []
        if not choices:
            return error_response(
                error=f"No choices in response: {json.dumps(data)[:200]}",
                error_type="empty_response",
                provider="alibaba",
                aspect_ratio=aspect,
                prompt=prompt,
            )

        first = choices[0]
        message = first.get("message", {})
        content = message.get("content", [])
        image_url = None
        for item in content:
            if isinstance(item, dict) and "image" in item:
                image_url = item["image"]
                break

        if not image_url:
            return error_response(
                error="No image URL found in response",
                error_type="empty_response",
                provider="alibaba",
                aspect_ratio=aspect,
                prompt=prompt,
            )

        # Cache locally so downstream consumers don't depend on an ephemeral URL.
        try:
            saved_path = save_url_image(image_url, prefix="alibaba_wan2.7")
            image_ref = str(saved_path)
        except Exception as exc:
            logger.warning(
                "Alibaba image URL %s could not be cached (%s); returning bare URL.",
                image_url,
                exc,
            )
            image_ref = image_url

        model_id = payload.get("model", "wan2.7-image")
        return success_response(
            image=image_ref,
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
            provider="alibaba",
            extra={"size": size},
        )


def register(ctx) -> None:
    ctx.register_image_gen_provider(AlibabaImageGenProvider())
