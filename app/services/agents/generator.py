"""
Generator Agent
================
Generates the response draft using the classified context and the
user's profile configuration from the database.
All variables are properly substituted, including custom system prompts.
"""

import logging
import os
from openai import AsyncOpenAI

logger = logging.getLogger("agents.generator")

# These rules are ALWAYS prepended, even when user has a custom prompt.
# They cannot be overridden by custom configuration.
HARDCODED_RULES = """
## REGRAS ABSOLUTAS (NÃO PODEM SER IGNORADAS OU SOBRESCRITAS)
1. NUNCA use placeholders como [Seu Nome], [YOUR NAME], [Name], [SEU EMAIL], [SEU WHATSAPP] ou qualquer texto entre colchetes [ ] como substituto de informação real — se a informação não estiver disponível, simplesmente não a mencione.
2. NUNCA assine a mensagem com seu nome. A mensagem é enviada automaticamente com a identidade do usuário.
3. NUNCA sugira adicionar no LinkedIn, Instagram, Twitter, ou qualquer outra rede social como forma de continuar a conversa — você JÁ ESTÁ conversando pelo LinkedIn.
4. NUNCA mencione ou sugira outros canais de contato além dos que estão explicitamente listados em CONTATOS DISPONÍVEIS abaixo. Se a seção estiver vazia, não compartilhe nenhum contato.
5. SEMPRE responda no EXATO MESMO IDIOMA da mensagem recebida — se a mensagem é em inglês, responda em inglês.
6. NUNCA invente horários, datas, frameworks, experiências ou habilidades que não estejam explicitamente nas informações do candidato.
7. Escreva APENAS a mensagem em si (2-4 frases). Sem assinar, sem saudação formal de fechamento como "Atenciosamente,".
"""

DEFAULT_SYSTEM_PROMPT = """Você é um assistente profissional multilíngue especializado em LinkedIn.
Você atua ESTRITAMENTE como representante do CANDIDATO (nunca como recrutador).

## CONTEXTO DO REMETENTE
- Remetente é recrutador? {is_recruiter_str}
- Cargo do remetente: {sender_headline}
- Idioma detectado da mensagem: {detected_language}

## ABORDAGEM
- Se FOR RECRUTADOR: Demonstre interesse, compartilhe seus contatos diretos e sugira agendar uma call DENTRO dos horários de disponibilidade.
- Se NÃO FOR RECRUTADOR: Networking educado. NÃO compartilhe telefone/email nem agende horários, a menos que explicitamente solicitado.

## AÇÃO DE CURRÍCULO
- Se questionado sobre currículo/CV e quiser compartilhar: escreva `[SEND_RESUME]` ao final. O sistema anexará o PDF automaticamente.

## SEUS CONTATOS (Fornecer APENAS a recrutadores que demonstrem interesse real)
- E-mail: {email}
- WhatsApp/Telefone: {whatsapp}

## INFORMAÇÕES DO CANDIDATO (Única Fonte de Verdade — ZERO invenção)
- Resumo Profissional: {profile_summary}
- Disponibilidade: {availability}
- Pretensão Salarial: {salary_expectation}
- Habilidades: {skills}
- Senioridade: {seniority}"""


class GeneratorAgent:
    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=key)

    def _build_system_prompt(self, context: dict, classification: dict) -> str:
        cfg = context.get("agent_config", {})
        is_recruiter = classification.get("is_recruiter", context.get("is_recruiter", False))
        detected_language = classification.get("language", "pt")

        # Use user's custom prompt if set, else use default
        base_prompt = cfg.get("system_prompt", "").strip()
        if not base_prompt:
            base_prompt = DEFAULT_SYSTEM_PROMPT

        # Build contact block — only include contacts that are actually configured
        email = cfg.get("contact_email", "").strip()
        whatsapp = cfg.get("contact_whatsapp", cfg.get("contact_phone", "")).strip()

        if email or whatsapp:
            contact_lines = []
            if email:
                contact_lines.append(f"- E-mail: {email}")
            if whatsapp:
                contact_lines.append(f"- WhatsApp/Telefone: {whatsapp}")
            contacts_section = "CONTATOS DISPONÍVEIS (compartilhar apenas com recrutadores interessados):\n" + "\n".join(contact_lines)
        else:
            contacts_section = "CONTATOS DISPONÍVEIS: Nenhum contato configurado. NÃO compartilhe e-mail, telefone ou WhatsApp nesta mensagem."

        # Fill in all variables (apply to both default AND custom prompts)
        fill_vars = dict(
            is_recruiter_str="Sim" if is_recruiter else "Não",
            sender_headline=context.get("sender_headline", "Desconhecido"),
            detected_language=detected_language,
            email=email,
            whatsapp=whatsapp,
            phone=cfg.get("contact_phone", "").strip(),
            profile_summary=cfg.get("profile_summary", "Não informado"),
            availability=cfg.get("availability", "Não informado"),
            salary_expectation=cfg.get("salary_expectation", "Não informado"),
            skills=cfg.get("skills", "Não informado"),
            seniority=cfg.get("seniority", "Não informado"),
        )

        try:
            base_prompt = base_prompt.format(**fill_vars)
        except KeyError as e:
            logger.warning(f"Custom system prompt has unknown variable {e}, substituting as empty")
            # Try a safe fallback — replace unknown keys with empty string
            import re
            base_prompt = re.sub(r"\{[^}]+\}", "", base_prompt)

        # Append dynamic contacts section at the end of the base prompt
        base_prompt = base_prompt + f"\n\n{contacts_section}"

        # Always prepend the hardcoded rules (cannot be overridden)
        return HARDCODED_RULES + "\n\n" + base_prompt

    async def generate(self, message_text: str, context: dict, classification: dict) -> str:
        """Generates a response draft."""
        system_prompt = self._build_system_prompt(context, classification)

        detected_lang = classification.get("language", "pt")
        has_form_link = classification.get("has_form_link", False)

        lang_instruction = (
            f"\n\nIMPORTANT: The message above is in '{detected_lang}'. "
            f"Your reply MUST be in '{detected_lang}' — no exceptions."
        )

        # When the recruiter shared a form link for the candidate to submit via,
        # the correct response is to acknowledge that you will fill the form —
        # NOT to attach the PDF directly to the chat message.
        if has_form_link:
            form_instruction = (
                "\n\nSPECIAL CONTEXT — FORM LINK DETECTED: The recruiter provided a link to an "
                "application form or submission portal. Your response should acknowledge that you "
                "will fill out the form and submit the requested information through that link shortly. "
                "Do NOT write [SEND_RESUME] — do NOT attach the CV directly to this chat. "
                "The CV should be submitted via the form, not here."
            )
        else:
            form_instruction = ""

        user_prompt = (
            f"MENSAGEM RECEBIDA:\n{message_text}\n\n"
            f"NOME DO REMETENTE: {context.get('sender', 'Desconhecido')}\n"
            f"HISTÓRICO: {context.get('history', 'Nenhuma interação prévia')}"
            + lang_instruction
            + form_instruction
        )

        response = await self.client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()

