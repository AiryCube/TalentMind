import os
import asyncio
import sys

# Ajuste global para Windows: Garante suporte a subprocessos do Playwright 
# ANTES do Uvicorn inicializar seu próprio event loop
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn
import uvicorn.loops.asyncio

# Impede o Uvicorn de forçar WindowsSelectorEventLoopPolicy em background
def nop_setup(*args, **kwargs):
    pass
uvicorn.loops.asyncio.asyncio_setup = nop_setup

if __name__ == "__main__":
    # Inicia o servidor Uvicorn a partir do código
    # Sem reload=True para evitar que o worker spawne com loop diferente
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
