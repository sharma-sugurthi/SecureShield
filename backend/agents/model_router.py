"""
Model Router — Intelligent Multi-Provider LLM Client with Task-Based Routing.

5 Providers (in priority by task type):
  1. Groq       — Llama 3.3 70B, blazing fast, free (primary for text tasks)
  2. Google     — Gemini Flash, best vision model (primary for PDF parsing)
  3. xAI        — Grok, $25/mo free (primary for long-form writing)
  4. Together   — Llama 3.3 70B Turbo (reliable backup)
  5. OpenRouter — Various free models (final fallback)

Routing logic:
  - Each agent role (policy_ingestion, case_analysis, explanation, grievance)
    has its own ordered provider chain defined in config.TASK_ROUTING.
  - The router tries each provider in order until one succeeds.
  - Rate-limited (429) providers are skipped to the next in the chain.
  - If ALL providers in the chain fail, a global retry waits 60s for limits to reset.
"""

import asyncio
import httpx
import json
import logging
import re
import hashlib
import os
from config import (
    GOOGLE_API_KEY, GOOGLE_BASE_URL,
    GROQ_API_KEY, GROQ_BASE_URL,
    XAI_API_KEY, XAI_BASE_URL,
    TOGETHER_API_KEY, TOGETHER_BASE_URL,
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL,
    OPENROUTER_MODELS,
    CEREBRAS_API_KEY, CEREBRAS_BASE_URL, CEREBRAS_MODELS,
    TASK_ROUTING, DEFAULT_ROUTING,
    CACHE_DIR, ENABLE_CACHE,
)

logger = logging.getLogger(__name__)


# --- Provider Configurations ---
PROVIDERS = {
    "google": {
        "key": GOOGLE_API_KEY,
        "url": f"{GOOGLE_BASE_URL}/chat/completions",
        "timeout": httpx.Timeout(connect=15.0, read=120.0, write=15.0, pool=15.0),
        "headers_fn": lambda key: {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    },
    "groq": {
        "key": GROQ_API_KEY,
        "url": f"{GROQ_BASE_URL}/chat/completions",
        "timeout": httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
        "headers_fn": lambda key: {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    },
    "xai": {
        "key": XAI_API_KEY,
        "url": f"{XAI_BASE_URL}/chat/completions",
        "timeout": httpx.Timeout(connect=15.0, read=120.0, write=15.0, pool=15.0),
        "headers_fn": lambda key: {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    },
    "together": {
        "key": TOGETHER_API_KEY,
        "url": f"{TOGETHER_BASE_URL}/chat/completions",
        "timeout": httpx.Timeout(connect=15.0, read=120.0, write=15.0, pool=15.0),
        "headers_fn": lambda key: {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    },
    "openrouter": {
        "key": OPENROUTER_API_KEY,
        "url": OPENROUTER_BASE_URL,
        "timeout": httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0),
        "headers_fn": lambda key: {
            "HTTP-Referer": "https://secureshield.app",
            "X-Title": "SecureShield",
        },
    },
    "cerebras": {
        "key": CEREBRAS_API_KEY,
        "url": f"{CEREBRAS_BASE_URL}/chat/completions",
        "timeout": httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
        "headers_fn": lambda key: {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    },
}


class ModelRouter:
    """Intelligent multi-provider LLM router with task-based failover chains."""

    def __init__(self):
        if ENABLE_CACHE and not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR, exist_ok=True)

    def _get_cache_path(self, payload: dict) -> str:
        """Generate a stable cache filename based on the request payload."""
        # Remove volatile fields like max_tokens or temperature if you want more hits
        dumped = json.dumps(payload, sort_keys=True)
        h = hashlib.sha256(dumped.encode()).hexdigest()
        return os.path.join(CACHE_DIR, f"{h}.json")

    def _get_from_cache(self, cache_path: str) -> str | None:
        """Read a response from the local disk cache."""
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    return json.load(f)["response"]
            except Exception:
                return None
        return None

    def _save_to_cache(self, cache_path: str, response: str):
        """Save a response to the local disk cache."""
        try:
            with open(cache_path, "w") as f:
                json.dump({"response": response}, f)
        except Exception as e:
            logger.warning(f"[ModelRouter] Cache save failed: {e}")

    async def _call_provider(
        self, provider_name: str, model: str, payload: dict
    ) -> str | None:
        """
        Call a single provider. Returns content string on success, None on failure.
        Handles rate limits (429), timeouts, and general errors gracefully.
        """
        provider = PROVIDERS.get(provider_name)
        if not provider or not provider["key"]:
            return None

        headers = provider["headers_fn"](provider["key"])
        url = provider["url"]
        timeout = provider["timeout"]
        payload_copy = {**payload, "model": model}

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"[ModelRouter] {provider_name.upper()} → {model}")
                response = await client.post(url, headers=headers, json=payload_copy)

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    logger.info(
                        f"[ModelRouter] ✓ {provider_name.upper()} {model} "
                        f"({len(content)} chars)"
                    )
                    return content

                elif response.status_code == 429:
                    logger.warning(
                        f"[ModelRouter] {provider_name.upper()} {model} "
                        f"rate-limited (429), skipping to next provider..."
                    )
                    return None

                else:
                    body = response.text[:200]
                    logger.warning(
                        f"[ModelRouter] {provider_name.upper()} {model} "
                        f"returned {response.status_code}: {body}"
                    )
                    return None

        except httpx.TimeoutException:
            logger.warning(
                f"[ModelRouter] {provider_name.upper()} {model} timed out"
            )
            return None
        except Exception as e:
            logger.warning(
                f"[ModelRouter] {provider_name.upper()} {model} error: {e}"
            )
            return None

    async def _call_openrouter_chain(self, payload: dict) -> str | None:
        """Try the full OpenRouter fallback chain (multiple free models)."""
        for model in OPENROUTER_MODELS.get("fallback_chain", []):
            result = await self._call_provider("openrouter", model, payload)
            if result:
                return result
        return None

    async def _try_routing_chain(
        self, chain: list[tuple[str, str | None]], payload: dict
    ) -> str | None:
        """
        Try each (provider, model) pair in the routing chain.
        If provider is 'openrouter' with model=None, use the full fallback chain.
        """
        for provider_name, model in chain:
            if provider_name == "openrouter" and model is None:
                result = await self._call_openrouter_chain(payload)
            else:
                result = await self._call_provider(provider_name, model, payload)

            if result:
                return result

        return None

    async def call(
        self,
        role: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: str | None = None,
        expect_json: bool = False,
    ) -> str | dict:
        """
        Make an LLM call using the intelligent task-based routing chain.

        Args:
            role: Agent role key (policy_ingestion, case_analysis, explanation, grievance)
            system_prompt: System prompt for the LLM
            user_prompt: User prompt for the LLM
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            response_format: Optional response format ("json_object")
            expect_json: If True, parse the response as JSON before returning

        Returns:
            str (or dict if expect_json=True)
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

        # --- Cache Check ---
        cache_path = self._get_cache_path(payload)
        if ENABLE_CACHE:
            cached_resp = self._get_from_cache(cache_path)
            if cached_resp:
                logger.info(f"[ModelRouter] ⚡ Cache hit for role '{role}'")
                if expect_json:
                    return self._parse_json(cached_resp)
                return cached_resp

        # Get the routing chain for this role
        chain = TASK_ROUTING.get(role, DEFAULT_ROUTING)
        logger.info(
            f"[ModelRouter] Role: '{role}' → chain: "
            f"{[f'{p}:{m}' for p, m in chain[:3]]}..."
        )

        # Global retry: if ALL providers in the chain fail, wait and retry
        for global_attempt in range(3):
            if global_attempt > 0:
                wait = 60 * global_attempt
                logger.info(
                    f"[ModelRouter] All providers failed for '{role}'. "
                    f"Waiting {wait}s for rate limits to reset "
                    f"(attempt {global_attempt + 1}/3)..."
                )
                await asyncio.sleep(wait)

            result = await self._try_routing_chain(chain, payload.copy())
            if result:
                # --- Save to Cache ---
                if ENABLE_CACHE:
                    self._save_to_cache(cache_path, result)
                
                if expect_json:
                    return self._parse_json(result)
                return result

        raise Exception(
            f"All LLM providers failed for role '{role}' after 3 global retries. "
            f"Rate limits may need more time to reset."
        )

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

        return self._parse_json(raw)

    @staticmethod
    def _parse_json(raw: str | dict) -> dict:
        """Robustly extract JSON from an LLM response string."""
        if isinstance(raw, dict):
            return raw

        cleaned = raw.strip()

        try:
            # Find the first { and the last }
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}")
            if start_idx != -1 and end_idx != -1:
                cleaned = cleaned[start_idx : end_idx + 1]

            # Simple repair for unterminated strings/blocks
            if cleaned.count("{") > cleaned.count("}"):
                cleaned += "}" * (cleaned.count("{") - cleaned.count("}"))

            return json.loads(cleaned)

        except json.JSONDecodeError as e:
            # Final attempt: regex extraction
            json_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except Exception:
                    pass

            logger.error(
                f"[ModelRouter] Failed to parse JSON: {e}\nRaw: {raw[:1000]}"
            )
            raise ValueError(f"LLM returned invalid JSON: {e}")


# Singleton instance
router = ModelRouter()
