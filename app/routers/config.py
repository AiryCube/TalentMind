"""
Router de configuração do agente.
Permite ao usuário configurar parâmetros como disponibilidade,
pretensão salarial, contatos, perfil profissional e preferências.
"""
import logging
import os
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from ..services.store import StoreService

logger = logging.getLogger(__name__)

router = APIRouter()

store = StoreService()

# Ensure data directory exists for the resume
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

class ConfigUpdate(BaseModel):
    key: str
    value: str

class AlertCreate(BaseModel):
    alert_type: str  # "interview", "followup", "reminder"
    title: str
    description: Optional[str] = None
    scheduled_at: Optional[str] = None  # ISO 8601
    metadata: Optional[str] = None  # JSON string


# ─── Alertas (ANTES de /{key} para evitar conflito) ──────────────

@router.get("/alerts/list")
async def get_alerts():
    """Retorna todos os alertas ativos"""
    alerts = store.get_all_alerts()
    return {"alerts": alerts}


@router.post("/alerts/create")
async def create_alert(alert: AlertCreate):
    """Cria um novo alerta"""
    alert_id = store.create_alert(
        alert_type=alert.alert_type,
        title=alert.title,
        description=alert.description,
        scheduled_at=alert.scheduled_at,
        metadata=alert.metadata,
    )
    return {"id": alert_id, "status": "created"}


@router.delete("/alerts/{alert_id}")
async def dismiss_alert(alert_id: int):
    """Remove/dismiss um alerta"""
    store.dismiss_alert(alert_id)
    return {"id": alert_id, "status": "dismissed"}


# ─── Configurações em batch ──────────────────────────────────────

@router.get("/all")
async def get_all_config():
    """Retorna todas as configurações do agente"""
    configs = store.get_all_config()
    return {"config": configs}


@router.put("/save")
async def set_config(update: ConfigUpdate):
    """Define ou atualiza uma configuração"""
    store.set_config(update.key, update.value)
    return {"key": update.key, "value": update.value, "status": "saved"}


@router.put("/save-batch")
async def set_config_batch(updates: list[ConfigUpdate]):
    """Define múltiplas configurações de uma vez"""
    for u in updates:
        store.set_config(u.key, u.value)
    return {"updated": len(updates), "status": "saved"}


@router.get("/get/{key}")
async def get_config(key: str):
    """Retorna uma configuração específica"""
    value = store.get_config(key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Configuração '{key}' não encontrada")
    return {"key": key, "value": value}


# ─── Currículo ──────────────────────────────────────────────────

@router.post("/resume")
async def upload_resume(file: UploadFile = File(...)):
    """Faz upload do currículo do usuário"""
    try:
        # Pega a extensão original do arquivo
        ext = os.path.splitext(file.filename)[1]
        save_path = os.path.join(DATA_DIR, f"resume{ext}")
        
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Salva a extensão no config para o bot saber qual arquivo buscar
        store.set_config("resume_ext", ext)
        
        return {"status": "success", "filename": file.filename, "message": "Currículo salvo com sucesso e pronto para envio pela IA."}
    except Exception as e:
        logger.error(f"Erro no upload do currículo: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao salvar arquivo")

@router.get("/resume/status")
async def get_resume_status():
    """Verifica se há um currículo anexado no servidor"""
    ext = store.get_config("resume_ext")
    if ext:
        save_path = os.path.join(DATA_DIR, f"resume{ext}")
        if os.path.exists(save_path):
            file_size = os.path.getsize(save_path)
            return {"has_resume": True, "extension": ext, "size_bytes": file_size}
    return {"has_resume": False}
