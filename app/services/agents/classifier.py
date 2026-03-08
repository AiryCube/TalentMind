"""
Classifier Agent
=================
Analyzes the incoming LinkedIn message and returns structured context:
language, intent, and what the sender is asking for.
Uses temperature=0 for deterministic classification.
"""

import json
import logging
import os
from openai import AsyncOpenAI

logger = logging.getLogger("agents.classifier")

CLASSIFIER_PROMPT = """You are a message classification engine. Analyze the LinkedIn message below and return a JSON object with EXACTLY these fields:

{
  "language": "<ISO 639-1 code, e.g. 'pt', 'en', 'es', 'fr'>",
  "intent": "<one of: 'recruitment', 'networking', 'sales', 'spam', 'unknown'>",
  "asks_for_cv": <true|false>,
  "asks_for_schedule": <true|false>,
  "asks_for_contacts": <true|false>,
  "is_recruiter": <true|false>
}

Rules:
- Detect language from the actual words used, not from the sender's name.
- is_recruiter = true if the message or sender's headline suggests they are recruiting or from HR/talent.
- asks_for_cv = true if they mention resume, CV, currículo, portfolio.
- asks_for_schedule = true if they mention call, meeting, reunião, agenda, horário, disponibilidade.
- asks_for_contacts = true if they ask for email, phone, WhatsApp, contato.
- Return ONLY valid JSON, no markdown, no explanation.
"""


class ClassifierAgent:
    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=key)

    async def classify(self, message_text: str, sender_headline: str = "") -> dict:
        """Returns a classification dict for the given message."""
        try:
            user_content = f"SENDER HEADLINE: {sender_headline}\n\nMESSAGE:\n{message_text}"
            response = await self.client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": CLASSIFIER_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0,
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)
            logger.info(f"Classification result: {result}")
            return result
        except Exception as e:
            logger.warning(f"Classifier failed, using defaults: {e}")
            return {
                "language": "pt",
                "intent": "unknown",
                "asks_for_cv": False,
                "asks_for_schedule": False,
                "asks_for_contacts": False,
                "is_recruiter": False,
            }
