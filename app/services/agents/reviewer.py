"""
Reviewer Agent
===============
Validates the generated draft against 7 criteria before allowing it to be sent.
Uses a mix of regex checks (fast & deterministic) and one LLM check for semantic issues.
Returns: { "approved": bool, "issues": [list of found issues] }
"""

import re
import logging
import os
import json
from openai import AsyncOpenAI

logger = logging.getLogger("agents.reviewer")

# --- Regex-based checks (fast, no API call) ---

# Placeholders that must never appear (broad pattern covers all variants)
PLACEHOLDER_PATTERNS = [
    r"\[seu\s+\w+\]",        # [SEU EMAIL], [SEU NOME], [SEU WHATSAPP], etc.
    r"\[your\s+\w+\]",       # [YOUR NAME], [YOUR EMAIL], etc.
    r"\[my\s+\w+\]",         # [MY EMAIL], [MY PHONE], etc.
    r"\[name\]",
    r"\[nome\]",
    r"\[contact\]",
    r"\[contato\]",
    r"\[insert\]",
    r"\[fill\]",
    r"\[preencher\]",
]

# Social networks that should never be suggested as a contact channel
SOCIAL_CHANNEL_PATTERNS = [
    r"me adicione\b", r"add me on\b", r"adicionar no linkedin\b",
    r"adicione-me\b", r"connect on linkedin\b", r"seguir no instagram\b",
    r"no instagram\b", r"no twitter\b", r"pelo twitter\b",
    r"pelo instagram\b", r"pelo whatsapp\b.*(?!está configurado)",
]

# Recruiter-perspective phrases (agent speaking as recruiter, not candidate)
RECRUITER_PERSPECTIVE_PATTERNS = [
    r"encaminhar seu currículo\b", r"forward your resume\b",
    r"meu banco de talentos\b", r"nossa base de candidatos\b",
    r"envie seu cv\b", r"nos envie o currículo\b",
]

# Unauthorized external links (not resume links, which are handled by [SEND_RESUME])
LINK_PATTERN = r"https?://(?!app\.|www\.linkedin\.com)[\w\-\.]+\.[a-z]{2,}"

MAX_CHARS = 800


def _detect_language_simple(text: str) -> str:
    """Very lightweight language detection by checking common words."""
    text_lower = text.lower()
    pt_words = ["você", "obrigado", "olá", "oi", "bom dia", "estou", "para", "pela", "pelo"]
    en_words = ["hello", "hi ", "thanks", "thank you", "i am", "please", "your", "we are"]
    es_words = ["hola", "gracias", "estoy", "mucho", "por favor", "usted"]

    pt_score = sum(1 for w in pt_words if w in text_lower)
    en_score = sum(1 for w in en_words if w in text_lower)
    es_score = sum(1 for w in es_words if w in text_lower)

    scores = {"pt": pt_score, "en": en_score, "es": es_score}
    return max(scores, key=scores.get)


class ReviewerAgent:
    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=key)

    def _regex_check(self, draft: str, original_message: str, classification: dict) -> list[str]:
        """Run all regex-based checks. Returns list of issues found."""
        issues = []
        draft_lower = draft.lower()

        # 1. Placeholder check
        for pat in PLACEHOLDER_PATTERNS:
            if re.search(pat, draft_lower):
                issues.append(f"PLACEHOLDER: Draft contains a placeholder pattern matching '{pat}'. Remove it completely.")

        # 2. Social channel check
        for pat in SOCIAL_CHANNEL_PATTERNS:
            if re.search(pat, draft_lower):
                issues.append(f"WRONG_CHANNEL: Draft suggests connecting via social media or asks to 'add on LinkedIn'. Remove this — the conversation is already on LinkedIn.")

        # 3. Recruiter perspective check
        for pat in RECRUITER_PERSPECTIVE_PATTERNS:
            if re.search(pat, draft_lower):
                issues.append(f"WRONG_PERSPECTIVE: Draft appears to speak as a recruiter ('{pat}'). Rewrite from the candidate's perspective.")

        # 4. Unauthorized links
        links = re.findall(LINK_PATTERN, draft)
        if links:
            issues.append(f"UNAUTHORIZED_LINK: Draft contains external links {links}. Remove all links unless they are explicitly part of the candidate's profile info.")

        # 5. Length check
        if len(draft) > MAX_CHARS:
            issues.append(f"TOO_LONG: Draft is {len(draft)} characters. Keep it under {MAX_CHARS}.")

        # 6. Language check
        expected_lang = classification.get("language", "pt")
        detected_in_draft = _detect_language_simple(draft)
        # Only flag if we have a clear mismatch between en and pt/es
        if expected_lang == "en" and detected_in_draft == "pt":
            issues.append(f"WRONG_LANGUAGE: The original message is in English but the draft appears to be in Portuguese. Rewrite in English.")
        elif expected_lang in ("pt", "es") and detected_in_draft == "en" and len(draft) > 100:
            # Only flag for longer texts to avoid false positives with English loanwords
            issues.append(f"WRONG_LANGUAGE: The original message is in '{expected_lang}' but the draft appears to be in English.")

        return issues

    async def review(self, draft: str, original_message: str, classification: dict, config: dict) -> dict:
        """
        Reviews the draft and returns:
        { "approved": bool, "issues": [list of strings] }
        """
        issues = self._regex_check(draft, original_message, classification)

        # LLM-based language check (more reliable than keyword heuristics)
        expected_lang = classification.get("language", "")
        if expected_lang:
            lang_issue = await self._llm_language_check(draft, expected_lang)
            if lang_issue:
                issues.append(lang_issue)

        if issues:
            logger.warning(f"Reviewer found {len(issues)} issue(s): {issues}")
            return {"approved": False, "issues": issues}

        # All checks passed
        logger.info("Reviewer approved the draft.")
        return {"approved": True, "issues": []}

    async def _llm_language_check(self, draft: str, expected_lang: str) -> str | None:
        """Uses the LLM to definitively check if the draft is in the correct language."""
        try:
            prompt = (
                f"Is the following text written in '{expected_lang}' language? "
                f"Answer with only 'yes' or 'no'.\n\nTEXT:\n{draft}"
            )
            response = await self.client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=5,
            )
            answer = response.choices[0].message.content.strip().lower()
            if answer.startswith("no"):
                return (
                    f"WRONG_LANGUAGE: The original message is in '{expected_lang}' but the draft "
                    f"is written in a different language. Rewrite entirely in '{expected_lang}'."
                )
        except Exception as e:
            logger.warning(f"LLM language check failed: {e}")
        return None
