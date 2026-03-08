"""
Corrector Agent
================
Receives a draft that the Reviewer rejected, along with the list of issues,
and asks the LLM to fix ONLY the listed issues without changing the rest.
Maximum 2 correction attempts. Returns the corrected text or None if failed.
"""

import logging
import os
from openai import AsyncOpenAI

logger = logging.getLogger("agents.corrector")

CORRECTOR_SYSTEM = """You are a message quality corrector. You will receive:
1. A LinkedIn message draft that has been REJECTED due to specific issues.
2. The list of issues found.

Your task: Fix ONLY the listed issues. Do not change the tone, language, or content otherwise.

ABSOLUTE RULES (never violate):
- NEVER use placeholders like [Seu Nome], [YOUR NAME], [Name].
- NEVER suggest connecting via social networks (you are already on LinkedIn).
- NEVER sign the message with a name.
- ALWAYS use the same language as the original message if a language issue is listed.
- Return ONLY the corrected message text, nothing else.
"""


class CorrectorAgent:
    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=key)

    async def correct(
        self,
        draft: str,
        issues: list[str],
        original_message: str,
        classification: dict,
    ) -> str | None:
        """
        Attempts to fix the draft. Returns corrected text, or None if correction fails.
        """
        issues_text = "\n".join(f"- {i}" for i in issues)
        detected_lang = classification.get("language", "pt")

        user_prompt = (
            f"ORIGINAL MESSAGE (for context and language reference):\n{original_message}\n\n"
            f"DRAFT TO FIX:\n{draft}\n\n"
            f"ISSUES FOUND:\n{issues_text}\n\n"
            f"IMPORTANT: The reply MUST be in '{detected_lang}' language.\n"
            f"Fix the issues above and return only the corrected message."
        )

        try:
            response = await self.client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": CORRECTOR_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=500,
            )
            corrected = response.choices[0].message.content.strip()
            logger.info(f"Corrector produced a fixed draft ({len(corrected)} chars).")
            return corrected
        except Exception as e:
            logger.error(f"Corrector failed: {e}")
            return None
