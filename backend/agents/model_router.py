"""
Model Router — Unified LLM client with Google AI Studio as primary provider.
Falls back to OpenRouter free models if Google is unavailable.
Uses Google's OpenAI-compatible API endpoint for minimal code changes.
"""

import asyncio
import httpx
import json
import logging
import re
from config import (
    GOOGLE_API_KEY, GOOGLE_BASE_URL, GOOGLE_MODELS,
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODELS,
)

logger = logging.getLogger(__name__)


class ModelRouter:
    """Routes LLM calls to Google AI Studio (primary) or OpenRouter (fallback)."""

    def __init__(self):
        self.google_key = GOOGLE_API_KEY
        self.google_url = f"{GOOGLE_BASE_URL}/chat/completions"
        self.google_models = GOOGLE_MODELS
        
        self.openrouter_key = OPENROUTER_API_KEY
        self.openrouter_url = OPENROUTER_BASE_URL
        self.openrouter_fallbacks = OPENROUTER_MODELS.get("fallback_chain", [])

    def _get_google_model(self, role: str) -> str:
        return self.google_models.get(role, "gemini-2.0-flash")

    async def _call_google(self, payload: dict) -> str | None:
        """Try multiple Gemini models (each has separate daily quota)."""
        google_models = ["gemini-2.0-flash", "gemini-2.0-flash-lite"]
        headers = {
            "Authorization": f"Bearer {self.google_key}",
            "Content-Type": "application/json",
        }
        # Use model from payload if provided and valid, otherwise use the priority list
        requested_model = payload.get("model")
        if requested_model and requested_model in google_models:
            # Move requested model to the front of the list
            google_models.remove(requested_model)
            google_models.insert(0, requested_model)
            
        for model in google_models:
            payload_copy = {**payload, "model": model}
            try:
                timeout = httpx.Timeout(connect=15.0, read=120.0, write=15.0, pool=15.0)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    logger.info(f"[ModelRouter] Google AI Studio → {model}")
                    response = await client.post(
                        self.google_url,
                        headers=headers,
                        json=payload_copy,
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        content = data["choices"][0]["message"]["content"]
                        logger.info(f"[ModelRouter] Google ✓ {model} ({len(content)} chars)")
                        return content
                    elif response.status_code == 429:
                        logger.warning(f"[ModelRouter] Google {model} rate-limited, trying next...")
                        continue
                    else:
                        logger.warning(f"[ModelRouter] Google {model} returned {response.status_code}: {response.text[:200]}")
                        continue
                        
            except httpx.TimeoutException:
                logger.warning(f"[ModelRouter] Google {model} timed out")
                continue
            except Exception as e:
                logger.warning(f"[ModelRouter] Google {model} error: {e}")
                continue
        
        return None

    async def _call_openrouter(self, payload: dict) -> str | None:
        """Try OpenRouter free models as fallback."""
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://secureshield.app",
            "X-Title": "SecureShield",
        }
        
        for i, model in enumerate(self.openrouter_fallbacks):
            payload["model"] = model
            
            for retry in range(2):
                try:
                    timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        logger.info(f"[ModelRouter] OpenRouter → {model} (attempt {retry+1})")
                        response = await client.post(
                            self.openrouter_url,
                            headers=headers,
                            json=payload,
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            content = data["choices"][0]["message"]["content"]
                            logger.info(f"[ModelRouter] OpenRouter ✓ {model} ({len(content)} chars)")
                            return content
                        elif response.status_code == 429:
                            logger.warning(f"[ModelRouter] {model} rate-limited (429)")
                            if retry == 0:
                                await asyncio.sleep(5 * (i + 1))
                                continue
                            break
                        else:
                            logger.warning(f"[ModelRouter] {model} returned {response.status_code}")
                            break
                            
                except httpx.TimeoutException:
                    logger.warning(f"[ModelRouter] {model} timed out")
                    break
                except Exception as e:
                    logger.warning(f"[ModelRouter] {model} error: {e}")
                    break
        
        return None

    async def call(
        self,
        role: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: str | None = None,
    ) -> str:
        """
        Make an LLM call. Tries Google AI Studio first, falls back to OpenRouter.
        """
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}

        # Retry up to 3 times with 60s backoff if ALL providers fail (rate limits reset per minute)
        for global_attempt in range(3):
            if global_attempt > 0:
                wait = 60 * global_attempt
                logger.info(f"[ModelRouter] All providers failed. Waiting {wait}s for rate limits to reset (attempt {global_attempt+1}/3)...")
                await asyncio.sleep(wait)

            # 1. Try Google AI Studio (fast, reliable, multiple models)
            if self.google_key:
                result = await self._call_google(payload.copy())
                if result:
                    return result
                logger.info("[ModelRouter] Google failed, trying OpenRouter fallback...")

            # 2. Fallback to OpenRouter free models
            if self.openrouter_key:
                result = await self._call_openrouter(payload.copy())
                if result:
                    return result

        raise Exception("All LLM providers failed after 3 attempts. Rate limits may need more time to reset.")

    async def call_json(
        self,
        role: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> dict:
        """Make an LLM call and parse the response as JSON."""
        raw = await self.call(
            role=role,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format="json_object",
        )

        # Clean up response
        cleaned = raw.strip()
        
        # Robust extraction: find the first { and the last }
        try:
            start_idx = cleaned.find('{')
            end_idx = cleaned.rfind('}')
            if start_idx != -1 and end_idx != -1:
                cleaned = cleaned[start_idx:end_idx + 1]
            
            # Simple repair for unterminated strings/blocks if they look truncated
            if cleaned.count('{') > cleaned.count('}'):
                cleaned += '}' * (cleaned.count('{') - cleaned.count('}'))
            
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            # Final attempt: try to find any JSON-like block if loads failed
            json_match = re.search(r'(\{.*\})', cleaned, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except:
                    pass
            
            logger.error(f"[ModelRouter] Failed to parse JSON: {e}\nRaw: {raw[:1000]}")
            raise ValueError(f"LLM returned invalid JSON: {e}")


# Singleton instance
router = ModelRouter()
