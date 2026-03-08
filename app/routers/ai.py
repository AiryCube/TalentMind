import os
from fastapi import APIRouter, HTTPException, Body
from ..services.ai import ResponseGenerator

router = APIRouter()

# Lazy init para evitar falha quando OPENAI_API_KEY não está definido
# rg = ResponseGenerator(api_key=os.getenv("OPENAI_API_KEY"))

@router.post('/generate')
async def generate_response(prompt: str = Body(...), context: dict | None = Body(None)):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY não configurado. Defina a variável de ambiente.")
    try:
        rg = ResponseGenerator(api_key=key)
        text = await rg.generate(prompt, context or {})
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoints adicionais para currículo e carta de apresentação
@router.post('/resume')
async def generate_resume(profile_text: str = Body(...), role: str | None = Body(None)):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY não configurado. Defina a variável de ambiente.")
    try:
        rg = ResponseGenerator(api_key=key)
        prompt = (
            "Você é um especialista em redação de currículo. Construa um currículo profissional, organizado por seções (Resumo, Experiências, "
            "Educação, Habilidades, Projetos), com bullet points objetivos, usando o texto do perfil abaixo."
        )
        if role:
            prompt += f"\nFoque a redação para a posição de: {role}."
        prompt += f"\n\nPerfil:\n{profile_text}"
        text = await rg.generate(prompt, {})
        return {"resume": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/cover-letter')
async def generate_cover_letter(job_description: str = Body(...), profile_text: str = Body(...), company: str | None = Body(None), role: str | None = Body(None)):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY não configurado. Defina a variável de ambiente.")
    try:
        rg = ResponseGenerator(api_key=key)
        prompt = (
            "Você é um escritor profissional. Escreva uma carta de apresentação personalizada, educada e objetiva, com 3-5 parágrafos, "
            "alinhando minhas experiências ao JD abaixo. Evite exageros e mantenha um tom profissional."
        )
        if company:
            prompt += f"\nEmpresa alvo: {company}."
        if role:
            prompt += f"\nCargo alvo: {role}."
        prompt += f"\n\nJob Description:\n{job_description}\n\nPerfil:\n{profile_text}"
        text = await rg.generate(prompt, {})
        return {"cover_letter": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))