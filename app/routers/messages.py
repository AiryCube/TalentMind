import os
import logging
from fastapi import APIRouter, HTTPException
from ..services.browser import BrowserService
from ..services.ai import ResponseGenerator
from ..services.store import StoreService
from .linkedin import get_browser_service

logger = logging.getLogger(__name__)

router = APIRouter()

store = StoreService(db_url=os.getenv("DATABASE_URL", "sqlite:///./data.db"))


async def _process_messages_internal():
    """Shared logic for processing messages — used by both the API endpoint and the scheduler."""
    browser = await get_browser_service()
    
    # ── Auto-login se não autenticado ───────────────────────────
    try:
        logged = await browser.is_logged_in()
    except Exception:
        logged = False
    
    if not logged:
        email = os.getenv("LINKEDIN_EMAIL")
        password = os.getenv("LINKEDIN_PASSWORD")
        if email and password:
            logger.info("Sessão não autenticada — iniciando login automático...")
            try:
                await browser.login(email, password)
                logger.info("Login automático concluído.")
            except Exception as login_err:
                logger.error(f"Falha no login automático: {login_err}")
                return {"processed": [], "error": "Não foi possível autenticar no LinkedIn automaticamente. Faça login manualmente pelo Dashboard."}
        else:
            return {"processed": [], "error": "Credenciais do LinkedIn não configuradas no .env."}
    # ────────────────────────────────────────────────────────────
    
    messages = await browser.fetch_messages(days_limit=90)
    logger.info(f"MESSAGES EXTRACTED: {len(messages)}")
    results = []
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        logger.error("OPENAI_API_KEY not set, skipping agent run.")
        return {"processed": []}
    rg = ResponseGenerator(api_key=key)

    # Carrega configurações salvas no banco
    config_dict = {}
    try:
        for row in store.cursor.execute("SELECT key, value FROM config").fetchall():
            config_dict[row[0]] = row[1]
    except Exception:
        pass

    for m in messages:
        if store.is_already_replied(m["id"]):
            continue
        if not m.get("is_unreplied", True):
            continue

        headline = m.get("sender_headline", "")
        is_recruiter = any(kw in headline.lower() for kw in [
            "recrut", "recruit", "rh", "hr", "talent", "headhunter", "acquisition", "aquisition"
        ])

        text = await rg.generate(m["text"], {
            "sender": m.get("sender"),
            "sender_headline": headline,
            "is_recruiter": is_recruiter,
            "history": store.get_conversation(m["id"]),
            "agent_config": config_dict
        })

        # ── Quality gate: pipeline returned None = message was rejected ──
        if text is None:
            logger.warning(f"Message {m['id']} from {m.get('sender')} was REJECTED by the review pipeline. Skipping send.")
            results.append({"id": m["id"], "status": "quality_rejected"})
            continue

        ok = await browser.reply(m["conversation_id"], text)
        if ok:
            store.save_message(m["id"], m["sender"], m["text"], text)
            results.append({"id": m["id"], "status": "replied"})
    return {"processed": results}


@router.get("/")
async def list_messages():
    """Lista todas as mensagens recentes do LinkedIn"""
    browser = await get_browser_service()
    messages = await browser.fetch_messages()
    return {"messages": messages}


@router.post("/process")
async def process_messages():
    """Processa mensagens não respondidas gerando respostas com IA"""
    return await _process_messages_internal()


@router.get("/history")
async def get_message_history():
    """Retorna histórico completo de mensagens processadas (do banco de dados)"""
    rows = store.get_all_messages()
    return {"messages": rows, "total": len(rows)}