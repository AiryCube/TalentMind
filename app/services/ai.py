"""
ResponseGenerator — Multi-Agent Orchestrator
=============================================
Pipeline: Classifier → Generator → Reviewer → Corrector (≤2 retries)

If a draft fails review and cannot be corrected in 2 attempts,
the method returns None so the caller can skip sending.
"""

import logging
import os
from openai import AsyncOpenAI
from .agents.classifier import ClassifierAgent
from .agents.generator import GeneratorAgent
from .agents.reviewer import ReviewerAgent
from .agents.corrector import CorrectorAgent

logger = logging.getLogger("response_generator")

MAX_CORRECTION_ATTEMPTS = 2


class ResponseGenerator:
    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("OPENAI_API_KEY")
        self.classifier = ClassifierAgent(api_key=key)
        self.generator = GeneratorAgent(api_key=key)
        self.reviewer = ReviewerAgent(api_key=key)
        self.corrector = CorrectorAgent(api_key=key)

    async def generate(self, message_text: str, context: dict) -> str | None:
        """
        Runs the full multi-agent pipeline.
        Returns the approved message text, or None if quality cannot be ensured.
        """
        sender_headline = context.get("sender_headline", "")

        # ── Step 1: Classify the incoming message ─────────────────
        logger.info("Step 1/4: Classifying message...")
        classification = await self.classifier.classify(message_text, sender_headline)

        # Override `is_recruiter` in classification with the existing heuristic if classifier disagrees
        # The existing heuristic from messages.py is more reliable for well-known recruiter keywords
        context_is_recruiter = context.get("is_recruiter", False)
        if context_is_recruiter:
            classification["is_recruiter"] = True

        # ── Step 2: Generate the draft ────────────────────────────
        logger.info("Step 2/4: Generating draft...")
        draft = await self.generator.generate(message_text, context, classification)
        logger.info(f"Draft generated ({len(draft)} chars): {draft[:80]}...")

        # ── Step 3 + 4: Review → Correct loop ─────────────────────
        config = context.get("agent_config", {})

        for attempt in range(MAX_CORRECTION_ATTEMPTS + 1):
            logger.info(f"Step 3/4: Reviewing draft (attempt {attempt + 1})...")
            review_result = await self.reviewer.review(draft, message_text, classification, config)

            if review_result["approved"]:
                logger.info("✅ Draft approved by Reviewer.")
                return draft

            issues = review_result["issues"]
            logger.warning(f"❌ Reviewer rejected draft. Issues: {issues}")

            if attempt >= MAX_CORRECTION_ATTEMPTS:
                logger.error(
                    f"Draft could not be approved after {MAX_CORRECTION_ATTEMPTS} correction attempts. "
                    f"Skipping this message to avoid sending bad content."
                )
                return None

            # ── Step 4: Correct and retry ─────────────────────────
            logger.info(f"Step 4/4: Correcting draft (attempt {attempt + 1}/{MAX_CORRECTION_ATTEMPTS})...")
            corrected = await self.corrector.correct(draft, issues, message_text, classification)

            if corrected is None:
                logger.error("Corrector failed to produce output. Skipping message.")
                return None

            draft = corrected

        # Should never reach here
        return None