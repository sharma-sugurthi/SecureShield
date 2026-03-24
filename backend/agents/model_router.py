"""
Model Router — Unified OpenRouter client with automatic model selection.
Each agent role maps to the best free model for its task.
Falls back to DeepSeek V3 if the primary model fails.
"""

import httpx
import json
import logging
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, MODELS

logger = logging.getLogger(__name__)


class ModelRouter:
    """Routes LLM calls to the best free model per agent role via OpenRouter."""

    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.base_url = OPENROUTER_BASE_URL
        self.models = MODELS
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://secureshield.app",
            "X-Title": "SecureShield",
        }

    def _get_model(self, role: str) -> str:
        """Get the model ID for a given agent role."""
        return self.models.get(role, self.models["fallback"])

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
        Make an LLM call routed to the right model for the given role.
        
        Args:
            role: Agent role key from config (policy_ingestion, case_analysis, explanation)
            system_prompt: System message for the LLM
            user_prompt: User message / input data
            temperature: Sampling temperature (low = deterministic)
            max_tokens: Maximum response tokens
            response_format: If "json_object", request JSON mode
            
        Returns:
            The LLM response text content.
        """
        model = self._get_model(role)
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}

        # Try primary model, fall back to deepseek if it fails
        for attempt_model in [model, self.models["fallback"]]:
            payload["model"] = attempt_model
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        self.base_url,
                        headers=self.headers,
                        json=payload,
                    )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    logger.info(f"[ModelRouter] {role} → {attempt_model} ✓")
                    return content
                else:
                    error_detail = response.text
                    logger.warning(
                        f"[ModelRouter] {attempt_model} returned {response.status_code}: {error_detail}"
                    )
                    if attempt_model == model and model != self.models["fallback"]:
                        logger.info(f"[ModelRouter] Falling back to {self.models['fallback']}")
                        continue
                    raise Exception(
                        f"LLM call failed: {response.status_code} — {error_detail}"
                    )

            except httpx.TimeoutException:
                logger.warning(f"[ModelRouter] {attempt_model} timed out")
                if attempt_model == model and model != self.models["fallback"]:
                    logger.info(f"[ModelRouter] Falling back to {self.models['fallback']}")
                    continue
                raise Exception("LLM call timed out on all models")

        raise Exception("All model attempts failed")

    async def call_json(
        self,
        role: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> dict:
        """
        Make an LLM call and parse the response as JSON.
        Handles cases where the model wraps JSON in markdown code blocks.
        """
        raw = await self.call(
            role=role,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format="json_object",
        )

        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"[ModelRouter] Failed to parse JSON: {e}\nRaw: {raw[:500]}")
            raise ValueError(f"LLM returned invalid JSON: {e}")


# Singleton instance
router = ModelRouter()
