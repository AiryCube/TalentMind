import logging
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from ..services.browser import BrowserService

logger = logging.getLogger(__name__)


class BrowserStatusResponse(BaseModel):
    """Modelo de resposta para o endpoint de status do navegador"""
    status: str
    detail: str
    is_logged_in: bool | None = None
    page_url: str | None = None


class ReplyEmberRequest(BaseModel):
    ember_id: str
    message: str


router = APIRouter()

# Singleton do BrowserService
_browser_service_instance = None


async def get_browser_service():
    """Obtém a instância do BrowserService com inicialização lazy"""
    global _browser_service_instance

    if _browser_service_instance is None:
        logger.info("Criando nova instância do BrowserService")
        _browser_service_instance = BrowserService()
        try:
            initialized = await _browser_service_instance.ensure_initialized()
            if not initialized:
                logger.error("Falha na inicialização do BrowserService")
                _browser_service_instance = None
                raise Exception("Falha na inicialização do navegador")
        except Exception as e:
            logger.error(f"Erro durante inicialização do BrowserService: {e}")
            _browser_service_instance = None
            raise

    return _browser_service_instance


@router.post("/login")
async def login_linkedin(email: str | None = None, password: str | None = None):
    try:
        browser_service = await get_browser_service()
        if await browser_service.is_logged_in():
            return {"success": True, "already_logged_in": True, "detail": "Já autenticado no LinkedIn"}
        email = email or os.getenv("LINKEDIN_EMAIL")
        password = password or os.getenv("LINKEDIN_PASSWORD")
        if not email or not password:
            raise HTTPException(status_code=400, detail="Credenciais do LinkedIn não fornecidas.")
        success = await browser_service.login(email, password)
        return {"success": success}
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if any(kw in msg for kw in ("Login não confirmado", "CAPTCHA", "2FA")):
            return JSONResponse(status_code=202, content={
                "success": False,
                "requires_interaction": True,
                "detail": msg,
            })
        raise HTTPException(status_code=500, detail=msg)


@router.get("/messages")
async def get_messages():
    browser_service = await get_browser_service()
    try:
        msgs = await browser_service.fetch_messages()
        return {"messages": msgs}
    except Exception as e:
        msg = str(e)
        if "Não autenticado" in msg:
            raise HTTPException(status_code=401, detail=msg)
        raise HTTPException(status_code=500, detail=msg)


@router.get("/messages/last-week")
async def get_messages_last_week():
    browser_service = await get_browser_service()
    try:
        msgs = await browser_service.fetch_messages(days_limit=7)
        return {"messages": msgs}
    except Exception as e:
        msg = str(e)
        if "Não autenticado" in msg:
            raise HTTPException(status_code=401, detail=msg)
        raise HTTPException(status_code=500, detail=msg)


@router.post("/reply")
async def reply_to_message(conversation_id: str, text: str):
    browser_service = await get_browser_service()
    try:
        success = await browser_service.reply(conversation_id, text)
        if success:
            return {"status": "success", "message": "Mensagem enviada"}
        return {"status": "error", "message": "Falha ao enviar mensagem"}
    except Exception as e:
        msg = str(e)
        if "Não autenticado" in msg:
            raise HTTPException(status_code=401, detail=msg)
        raise HTTPException(status_code=500, detail=msg)


@router.post("/reply-ember")
async def reply_message_ember(request: ReplyEmberRequest):
    """Envia mensagem usando ember ID da conversa"""
    browser_service = await get_browser_service()
    try:
        success = await browser_service.reply_with_ember_id(request.ember_id, request.message)
        if success:
            return {"status": "success", "message": f"Mensagem enviada para {request.ember_id}"}
        return {"status": "error", "message": f"Falha ao enviar para {request.ember_id}"}
    except Exception as e:
        msg = str(e)
        if "Não autenticado" in msg:
            raise HTTPException(status_code=401, detail=msg)
        raise HTTPException(status_code=500, detail=msg)


@router.get("/profile")
async def get_profile(url: str | None = None):
    browser_service = await get_browser_service()
    try:
        profile = await browser_service.scrape_profile(url)
        return {"profile": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contacts")
async def get_contacts():
    """Lista contatos únicos extraídos das mensagens"""
    browser_service = await get_browser_service()
    try:
        messages = await browser_service.fetch_messages(days_limit=365)
        contacts = {}
        for msg in messages:
            sender = msg.get("sender", "Desconhecido")
            if sender != "Desconhecido" and sender not in contacts:
                contacts[sender] = {
                    "name": sender,
                    "last_message": (msg.get("text", "")[:100] + "...") if msg.get("text") else "",
                    "last_timestamp": msg.get("timestamp"),
                    "conversation_id": msg.get("conversation_id"),
                }
        contacts_list = sorted(contacts.values(), key=lambda x: x["last_timestamp"] or "", reverse=True)
        return {"contacts": contacts_list, "total": len(contacts_list)}
    except Exception as e:
        msg = str(e)
        if "Não autenticado" in msg:
            raise HTTPException(status_code=401, detail=msg)
        raise HTTPException(status_code=500, detail=msg)


@router.get("/status", response_model=BrowserStatusResponse)
async def check_browser_status():
    """Verifica o status do navegador"""
    try:
        browser_service = await get_browser_service()
        if browser_service.page is None or browser_service.page.is_closed():
            return BrowserStatusResponse(status="error", detail="Página do navegador não está acessível")
        is_logged_in = await browser_service.is_logged_in()
        return BrowserStatusResponse(
            status="success",
            detail="Navegador funcionando corretamente",
            is_logged_in=is_logged_in,
            page_url=str(browser_service.page.url),
        )
    except Exception as e:
        return BrowserStatusResponse(status="error", detail=f"Erro ao verificar status: {str(e)}")