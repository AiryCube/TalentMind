import os
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pathlib import Path

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Ajuste para Windows: garantir suporte a subprocessos no asyncio (Playwright)
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Carregar variáveis de ambiente do .env na raiz do projeto
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

from .routers import linkedin, ai, calendar, messages, config  # noqa: E402

app = FastAPI(
    title="LinkedIn Recruiter Agent",
    description="Agente de IA para interação automática com recrutadores no LinkedIn",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(linkedin.router, prefix="/linkedin", tags=["LinkedIn"])
app.include_router(ai.router, prefix="/ai", tags=["AI"])
app.include_router(calendar.router, prefix="/google", tags=["Google Calendar"])
app.include_router(messages.router, prefix="/messages", tags=["Messages"])
app.include_router(config.router, prefix="/config", tags=["Configuration"])

# Servir dashboard estático
public_dir = Path(__file__).resolve().parents[1] / "public"
if public_dir.exists():
    app.mount("/", StaticFiles(directory=str(public_dir), html=True), name="static")