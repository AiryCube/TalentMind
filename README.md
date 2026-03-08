# 🤖 Agente Autônomo LinkedIn (FastAPI + Playwright + OpenAI)

Um agente autônomo baseado em Inteligência Artificial desenvolvido para gerenciar e interagir automaticamente com a sua caixa de entrada do LinkedIn. A solução utiliza automação de navegador (Playwright), um backend em Python (FastAPI), processamento de linguagem natural (OpenAI GPT-4o) e um Dashboard robusto e moderno (HTML/Vanilla CSS) para visualização e configurações.

---

## 🚀 Funcionalidades Principais

- **Automação de Login e Scraper (Stealth):** Usa Contextos Persistentes do Playwright para se manter logado na plataforma do LinkedIn, acessando conversas de até 90 dias atrás (configurável).
- **Leitura Inteligente de Mensagens:** Identifica o contexto, recorta mensagens não respondidas, identifica idiomas e dados como "Headline / Cargo" do remetente, extraindo-os para contextualização da IA.
- **Filtro de "Self-reply":** O agente reconhece respostas já feitas pelo perfil do usuário ("Vinicius Figueiredo", "Eu") e **ignora magicamente** tais mensagens, evitando envios repetidos.
- **Integração Avançada OpenAI:** Usa Prompts customizáveis do Sistema onde a IA:
  - Responde **sempre no mesmo idioma** da mensagem original.
  - Atua de duas maneiras distintas: Se for **Recrutamento**, fornecerá contatos e link para agenda. Se for **Networking**, apenas interagirá gentilmente.
  - Sem alucinação (Zero-Hallucination): Só usa a verdade se alimentada no perfil e currículo.
- **Agendador Automático (Cron):** Configure pela tela de Configurações o horário de início e o intervalo (2h, 4h, 8h, 12h ou 24h) para que o agente rode sozinho. O backend usa um `asyncio.create_task` em background que verifica as configurações salvas a cada 60 segundos e dispara automaticamente.
- **Relógio ao Vivo no Dashboard:** Data e hora atual exibidas em tempo real na barra superior da interface.
- **Dashboard UI Premium Web:**
  - Painel com Tema Dinâmico.
  - Visualizador do "Log de Interações".
  - Parametrizações editáveis live: `Prompt da IA`, config salarial, formato de trabalho, e tempo em experiência pregressa.
  - Central de Anexos: Carregue seu PDF de Currículo pelo painel web.
- **Ação "[SEND_RESUME]":** A IA foi instruída a retornar a tag `[SEND_RESUME]` caso o recrutador explicitamente peça um currículo. Quando isso acontece, o backend localiza o arquivo PDF upado no dashboard e o envia fisicamente no chat usando Playwright Automation.

---

## 🏗️ Arquitetura e Estrutura do Projeto

O projeto adota uma arquitetura modularizada focada no **Backend Python (FastAPI)** como o grande maestro, controlando rotas HTTP, banco de dados e as threads assíncronas de Browser.

```text
.
├── app/
│   ├── config.py           # Gestão das chaves .env e paths
│   ├── database.py         # Conexão com SQLite e inicialização
│   ├── models.py           # Definições SQLModel (Logs, Perfil, Mensagens)
│   ├── routers/
│   │   ├── config.py       # API para Salvar Prompts e Envio de PDFs de Currículo
│   │   ├── linkedin.py     # Fluxo web: Login Async Playwright 
│   │   ├── logs.py         # Histórico de Atividades enviadas ao Dashboard
│   │   ├── messages.py     # Lógica central: buscar -> classificar LLM -> responder
│   │   └── profile.py      # Extração (Draft) do perfil do Linkedin via DOM
│   └── services/
│       ├── browser.py      # Core de Automação Playwright (DOM Inspect, Clicks, Send Keys, Send Resume)
│       ├── openai.py       # Integração com GPT, extração do Prompt Padrão e injeção do Currículo
│       └── scheduler.py    # Loop asyncio em background: verifica config e dispara o agente automaticamente
├── data/
│   └── data.db             # Banco de Dados Local (SQLite)
├── public/                 # Assets Servidos Específicos para o Frontend (Dashboard)
│   ├── index.html          # Dashboard Principal (Glassmorphism / Premium UI)
│   ├── index.css           # Vanilla CSS (Configurado sem Tailwind)
│   └── script.js           # Orquestração do Frontend e chamadas REST API Axios-like
├── run.py                  # Entrypoint Centralizador do Servidor Uvicorn
├── requirements.txt        # Dependências PyPI do projeto
└── .env                    # Credenciais Variáveis Secretas
```

---

## ⚙️ Pré-requisitos Funcionais

Para rodar esta aplicação no **VS Code** ou na IDE de preferência, você precisa ter:

1. **Python 3.10+** ou superior instalado localmente no sistema `(Variável de Ambientes PATH configuradas)`.
2. **Navegador Chromium Instalado pelo Playwright:** Para orquestração nativa.
3. Conta Premium (ou Free) válida no **LinkedIn** (Não use MFA/2FA, ou a automação exigirá log in manual).
4. Uma **API Key ativa da OpenAI**.

---

## 💻 Instruções de Instalação e Execução (No VS Code / Terminal)

Nenhum terminal deve rodar Node.js neste projeto. Tudo foi refatorado para ser `100% Python`.

### Passo 1: Clone ou abra o projeto no VS Code
Inicie o terminal integrado do VS Code `(Ctrl + \`) ou equivalente no Windows PowerShell.

### Passo 2: Crie e ative um Ambiente Virtual (VENV)
Isso impede conflitos de bibliotecas na sua máquina Windows/Linux.

```powershell
# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
# Mac / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### Passo 3: Instale as Dependências do Projeto e Playwright
Com o `.venv` ativado, rode:

```bash
pip install -r requirements.txt
playwright install chromium
```

### Passo 4: Configure as Variáveis de Ambiente
Crie um arquivo chamado `.env` na raiz do projeto contendo as seguintes credenciais obrigatórias:

```env
OPENAI_API_KEY=sk-xxxx-sua-chave-aqui-xxxxx
LINKEDIN_EMAIL=seu-email@gmail.com
LINKEDIN_PASSWORD=sua-senha-super-secreta
DAYS_LIMIT=90
```
> O arquivo de log ou as imagens de debug irão ignorar falhas de `.env` se criadas depois, portanto confira seus dados corretamente.

### Passo 5: Inicialize o Backend
Rodaremos a aplicação usando o script central de `run.py`.

```powershell
python run.py
```
*A API será levantada no endereço Localhost: `http://127.0.0.1:5373`*

### Passo 6: Acesse o Dashboard e Utilize
1. Abra o navegador em: **[http://localhost:5373](http://localhost:5373)**.
2. Acesse a guia **"Configurações"**. Atualize seu Painel de Prompts da IA e as Informações Salariais se necessário. 
3. Caso já queira enviar currículos automaticamente nos bate-papos, **faça o upload do PDF** pela inteface "Enviar Currículo Web".
4. Vá em **"Login Automático"**, caso não esteja logado, e assista a magia do background acontecer.
5. Cancele e reinicie se houverem erros, ou simplesmente clique em **"Forçar Busca de Mensagens"** no Dash Central para varrer todas as mensagens em sua aba *"Inbox"* de até *90 dias* atrás que o Remetente não corresponda a *"Eu / Seu Sobrenome"*.

---

## 🛠️ Trilha de Debugging Ativa

Caso as automações parem de enviar respostas (porque a rede social LinkedIn mudou suas Tags classes de HTML DOM periodicamente):
- Consulte a tag `# Logs & Debugging` no `.gitignore` onde centralizamos logs. O app cria imagens de print (`debug_linkedin.png`) no diretório do projeto ativamente caso uma classe CSS não carregue a mensagem dentro de 15 segundos da "SPA" page hydration (Hydration Check Failure).
- No componente `browser.py`, o Agente usufrui de tolerância a exceções (`TimeoutError`), de modo que pule uma conversa errada sem derrubar as 14 sub-sequenciais.

---
> 🚀 *Solução desenhada sob forte uso ético profissional.*