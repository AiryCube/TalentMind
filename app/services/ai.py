import os
import asyncio
from openai import AsyncOpenAI


class ResponseGenerator:
    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=key)

    async def generate(self, message_text: str, context: dict):
        default_system_prompt = """Você é um assistente profissional multilíngue especializado em LinkedIn.
Você atua como representante direto do candidato, interagindo com pessoas de forma natural, fluida e estritamente profissional.

## REGRAS DE IDIOMA E COMUNICAÇÃO (CRÍTICAS)
- **DETECTE O IDIOMA**: A sua resposta DEVE SER OBRIGATORIAMENTE no EXATO MESMO IDIOMA em que a MENSAGEM RECEBIDA foi escrita.
- **ZERO ALUCINAÇÃO**: Baseie sua resposta APENAS e EXCLUSIVAMENTE nas informações fornecidas na seção "PERFIL RESUMIDO", "DISPONIBILIDADE" e "PRETENSÃO SALARIAL" abaixo.
- **DESCONHECIMENTO**: Se o contato fizer uma pergunta técnica ou comportamental para a qual você não tenha resposta no perfil, diga educadamente: "No momento, não tenho os detalhes de cor para te dar certeza, mas vou analisar e te retorno assim que possível."
- **SEM INVENÇÕES**: Nunca adicione frameworks, tempos de experiência ou habilidades não explícitas no perfil.

## CONTEXTO DO REMETENTE
- Remetente é recrutador? {is_recruiter_str}
- Cargo do remetente: {sender_headline}

## ABORDAGEM E PAPEL
- Se FOR RECRUTADOR: Trate com prioridade. Demonstre interesse, informe que aceitou a conexão/bate-papo. Compartilhe seus contatos diretos e sugira agendar uma call.
- Se NÃO FOR RECRUTADOR: Foco apenas em networking educado. NÃO compartilhe telefone/email nem tente agendar horários, a menos que solicitado com contexto.

## AÇÃO DE ENVIO DE CURRÍCULO
- Se (E APENAS SE) você for questionado sobre currículo (resume, CV) e quiser compartilhar, IMPRIMA A EXATA VARIÁVEL VISUALMENTE: `[SEND_RESUME]` no final da sua resposta. O sistema do robô interceptará isso e anexará o arquivo em PDF silenciosamente na conversa.

## SEUS CONTATOS (Fornecer apenas a recrutadores demonstrando interesse)
- E-mail: {email}
- WhatsApp/Telefone: {whatsapp}

## INFORMAÇÕES DO CANDIDATO (Única Fonte de Verdade)
- Resumo Profissional: {profile_summary}
- Agenda Diária: {availability}
- Faixa Salarial: {salary_expectation}

Escreva APENAS a mensagem que será enviada de volta ao contato no LinkedIn, curta (2-4 frases), educada e respeitando o limite de informações acima."""

        # Puxa o prompt customizado se o usuário preencheu no banco, senão usa o default
        system_prompt = context.get("agent_config", {}).get("system_prompt", "")
        if not system_prompt.strip():
            system_prompt = default_system_prompt

        user_prompt = f"""MENSAGEM RECEBIDA DA TRANSAÇÃO ATUAL:
{message_text}

CONTEXTO:
- Nome: {context.get('sender', 'Desconhecido')}
- Histórico anterior: {context.get('history', 'Nenhuma interação prévia registrada')}

Gere a resposta adequada seguindo rigorosamente as regras do sistema, no idioma correto."""

        # Preencher variáveis do system prompt com configurações
        config = context.get("agent_config", {})
        is_recr = context.get("is_recruiter", False)
        
        formatted_prompt = system_prompt.format(
            is_recruiter_str="Sim" if is_recr else "Não",
            sender_headline=context.get("sender_headline", "Desconhecido"),
            email=config.get("contact_email", "vftdt@gmail.com"),
            whatsapp=config.get("contact_whatsapp", "11987078196"),
            phone=config.get("contact_phone", "11987078196"),
            profile_summary=config.get("profile_summary", "Profissional de tecnologia com experiência em desenvolvimento de software"),
            availability=config.get("availability", "Disponível para reuniões em horário comercial (9h-18h), de segunda a sexta"),
            salary_expectation=config.get("salary_expectation", "Compatível com o mercado para a posição — aberto a negociação"),
        )

        response = await self.client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=500,
        )
        return response.choices[0].message.content