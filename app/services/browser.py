import os
import asyncio
import hashlib
import re
import logging
from datetime import datetime, timedelta
from typing import Optional
from playwright.async_api import async_playwright

# Configurar logger
logger = logging.getLogger(__name__)

# Configurar política de loop de eventos para Windows
if os.name == 'nt':  # Windows
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

class BrowserService:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def ensure_initialized(self, retry_on_failure=True):
        """Garante que o navegador está inicializado, com opção de retry"""
        try:
            logger.debug("Iniciando ensure_initialized")
            # Verifica se já temos uma página válida
            if self.page and not self.page.is_closed():
                logger.debug("Página já está válida, retornando True")
                # Tenta navegar para about:blank para garantir que a página está responsiva
                try:
                    await self.page.goto("about:blank", timeout=5000)
                    return True
                except Exception as navigation_error:
                    logger.warning(f"Página não responsiva - tentando reiniciar: {navigation_error}")
                    return await self.restart_browser()
            
            logger.debug("Página não está válida, reinicializando tudo")
            # Se não temos página válida, reinicializa tudo
            if self.context:
                logger.debug("Fechando contexto existente")
                try:
                    await self.context.close()
                except:
                    pass
            if self.browser:
                logger.debug("Fechando navegador existente")
                try:
                    await self.browser.close()
                except:
                    pass
            if self.playwright:
                logger.debug("Parando playwright existente")
                try:
                    await self.playwright.stop()
                except:
                    pass
            
            logger.debug("Iniciando nova instância do Playwright")
            import asyncio
            loop = asyncio.get_running_loop()
            logger.error(f">>>>> DEBUG: CURRENT RUNNING LOOP TYPE IS: {type(loop)} <<<<<")
            with open("debug_log.txt", "a", encoding="utf-8") as f:
                f.write(f"DEBUG LOOP TYPE: {type(loop)}\n")
            
            # Configurar política de loop de eventos para Windows antes de inicializar o Playwright
            if os.name == 'nt':  # Windows
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
            # Inicialização básica
            self.playwright = await async_playwright().start()
            user_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".browser_profile"))
            logger.debug(f"Usando diretório de perfil: {user_data_dir}")
            os.makedirs(user_data_dir, exist_ok=True)
            
            # Configurações básicas para o navegador
            browser_args = [
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--disable-default-apps',
                '--disable-extensions'
            ]
            
            try:
                # Usar launch normal em vez de launch_persistent_context para evitar o bug do user-data-dir
                self.browser = await self.playwright.chromium.launch(
                    headless=False,
                    args=browser_args
                )
                logger.debug("Navegador criado com sucesso")
                
                # Criar contexto normal com viewport
                self.context = await self.browser.new_context(viewport={'width': 1920, 'height': 1080})
                logger.debug("Contexto do navegador criado com sucesso")
                
            except Exception as context_error:
                logger.error(f"ERRO ao criar contexto do navegador: {context_error}")
                with open("debug_log.txt", "a", encoding="utf-8") as f:
                    f.write(f"DEBUG: ERRO contexto navegador: {context_error}\n")
                return False
            
            try:
                self.page = await self.context.new_page()
                logger.debug("Nova página criada com sucesso")
            except Exception as page_error:
                logger.error(f"ERRO ao criar nova página: {page_error}")
                with open("debug_log.txt", "a", encoding="utf-8") as f:
                    f.write(f"DEBUG: ERRO criar página: {page_error}\n")
                return False
            
            # Configurar headers realistas
            try:
                await self.page.set_extra_http_headers({
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0'
                })
                logger.debug("Headers HTTP configurados com sucesso")
            except Exception as headers_error:
                logger.warning(f"AVISO: Não foi possível configurar headers HTTP: {headers_error}")
                # Continua mesmo com erro nos headers - não é crítico
            
            logger.debug("Nova página criada com sucesso e configurações stealth aplicadas")
            
            # Verificação adicional: garante que a página está realmente acessível
            if not self.page or self.page.is_closed():
                logger.error("Página criada mas não está acessível!")
                return False
                
            logger.debug(f"Página verificada - URL: {self.page.url}, Fechada: {self.page.is_closed()}")
            return True
        except Exception as e:
            logger.error(f"Erro em ensure_initialized: {e}")
            import traceback
            with open("debug_log.txt", "a", encoding="utf-8") as f:
                f.write(f"DEBUG: Erro em ensure_initialized: {e}\n")
                f.write(f"DEBUG: Traceback completo: {traceback.format_exc()}\n")
            if retry_on_failure:
                logger.warning(f"Falha na inicialização, tentando reiniciar: {e}")
                return await self.restart_browser()
            else:
                return False

    async def restart_browser(self):
        """Reinicia completamente o navegador"""
        try:
            if self.browser:
                await self.browser.close()
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            if self.page and not self.page.is_closed():
                await self.page.close()
            self.playwright = None
            self.browser = None
            self.context = None
            self.page = None
            result = await self.ensure_initialized(retry_on_failure=False)
            return result
        except Exception as e:
            logger.error(f"Erro ao reiniciar navegador: {e}")
            return False

    async def is_logged_in(self) -> bool:
        """Verifica se está logado no LinkedIn"""
        try:
            await self.ensure_initialized()
            
            # Verifica se a página está acessível
            if not self.page or self.page.is_closed():
                return False
            
            # Obtém URL atual
            url = self.page.url or ''
            
            # Se está na página de login, não está logado
            if 'linkedin.com/login' in url:
                return False
            
            # Verifica se há campos de login visíveis
            login_field = await self.page.query_selector('input[name="session_key"], input#username')
            if login_field:
                return False
            
            # Verifica elementos que indicam login bem-sucedido
            nav_element = await self.page.query_selector('nav.global-nav, .msg-overlay-list-bubble')
            if nav_element:
                return True
            
            # Fallback: verifica URL geral do LinkedIn (não sendo página de login)
            return 'linkedin.com' in url and '/login' not in url
            
        except Exception as e:
            logger.warning(f"Erro ao verificar login: {e}")
            return False

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Realiza login no LinkedIn. Retorna True se bem-sucedido."""
        try:
            # Primeiro verifica se já está logado
            if await self.is_logged_in():
                print("DEBUG: Já está logado, pulando processo de login")
                return True
            
            # Se não está logado, tenta navegar para a página de login
            try:
                await self.page.goto('https://www.linkedin.com/login', wait_until='domcontentloaded', timeout=15000)
            except Exception as nav_err:
                print(f"DEBUG: Navegação para login falhou: {nav_err}")
                # Continua mesmo com erro de navegação - pode já estar em página válida
            
            # Verifica novamente se está logado após tentativa de navegação
            if await self.is_logged_in():
                print("DEBUG: Logado após tentativa de navegação")
                return True
            
            # Se chegou aqui, realmente precisa fazer login
            try:
                await self.page.bring_to_front()
            except Exception:
                pass
            # Tenta fechar banner de cookies, se existir
            try:
                cookie_selectors = [
                    'button:has-text("Aceitar")',
                    'button:has-text("Accept")',
                    'button[aria-label*="Accept"]',
                    'button[aria-label*="Aceitar"]',
                    '[data-test-global-alert-accept]'
                ]
                for cs in cookie_selectors:
                    btn = await self.page.query_selector(cs)
                    if btn:
                        await btn.click()
                        break
            except Exception:
                pass
            # Seletores alternativos (LinkedIn muda atributos com frequência)
            username_selectors = ['input[id="username"]', 'input[name="session_key"]', 'input[autocomplete="username"]', 'input[type="email"]', '#organic-div input[type="text"]']
            password_selectors = ['input[id="password"]', 'input[name="session_password"]']
            # Aguarda algum campo de usuário aparecer; se não, tenta rotas alternativas
            try:
                await self.page.wait_for_selector(', '.join(username_selectors), timeout=8000)
            except Exception:
                # Gera debug antes de tentar rotas alternativas
                try:
                    logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
                    os.makedirs(logs_dir, exist_ok=True)
                    await self.page.screenshot(path=os.path.join(logs_dir, 'login_page_before_retry.png'))
                    html = await self.page.content()
                    with open(os.path.join(logs_dir, 'login_page_before_retry.html'), 'w', encoding='utf-8') as f:
                        f.write(html)
                except Exception:
                    pass
                # Tenta a rota antiga
                try:
                    await self.page.goto('https://www.linkedin.com/uas/login', wait_until='domcontentloaded', timeout=10000)
                    await self.page.wait_for_selector(', '.join(username_selectors), timeout=6000)
                except Exception:
                    # Gera debug antes de tentar home
                    try:
                        logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
                        os.makedirs(logs_dir, exist_ok=True)
                        await self.page.screenshot(path=os.path.join(logs_dir, 'login_page_before_home.png'))
                        html = await self.page.content()
                        with open(os.path.join(logs_dir, 'login_page_before_home.html'), 'w', encoding='utf-8') as f:
                            f.write(html)
                    except Exception:
                        pass
                    # Tenta ir para a home e clicar em Sign in
                    await self.page.goto('https://www.linkedin.com/', wait_until='domcontentloaded', timeout=10000)
                    try:
                        # Links comuns de sign in
                        signin_selectors = [
                            'a[href*="/login"]',
                            'a[aria-label*="Sign in"]',
                            'a[data-test-global-nav-link="sign-in"]',
                            'a.nav__button-secondary:has-text("Sign in")',
                            'a.nav__button-secondary:has-text("Entrar")'
                        ]
                        for ss in signin_selectors:
                            link = await self.page.query_selector(ss)
                            if link:
                                await link.click()
                                break
                        await self.page.wait_for_selector(', '.join(username_selectors), timeout=8000)
                    except Exception:
                        # Debug: salvar screenshot e HTML antes de falhar
                        try:
                            logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
                            os.makedirs(logs_dir, exist_ok=True)
                            await self.page.screenshot(path=os.path.join(logs_dir, 'login_page.png'))
                            html = await self.page.content()
                            with open(os.path.join(logs_dir, 'login_page.html'), 'w', encoding='utf-8') as f:
                                f.write(html)
                            print(f"DEBUG: Screenshot e HTML salvos em {logs_dir}")
                        except Exception as debug_err:
                            print(f"DEBUG ERROR: Falha ao salvar arquivos de debug: {debug_err}")
                        raise Exception('Campo de usuário não encontrado na página de login do LinkedIn')
            # Preenche usuário
            filled_user = False
            for sel in username_selectors:
                el = await self.page.query_selector(sel)
                if el:
                    await self.page.fill(sel, username)
                    filled_user = True
                    break
            if not filled_user:
                # Tenta buscar dentro de iframes
                try:
                    for frame in self.page.frames:
                        el = await frame.query_selector(', '.join(username_selectors))
                        if el:
                            await el.fill(username)
                            filled_user = True
                            break
                except Exception:
                    pass
            if not filled_user:
                # Debug: salvar screenshot e HTML antes de falhar
                try:
                    logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
                    os.makedirs(logs_dir, exist_ok=True)
                    await self.page.screenshot(path=os.path.join(logs_dir, 'login_page.png'))
                    html = await self.page.content()
                    with open(os.path.join(logs_dir, 'login_page.html'), 'w', encoding='utf-8') as f:
                        f.write(html)
                except Exception:
                    pass
                raise Exception('Campo de usuário não encontrado na página de login do LinkedIn')
            # Preenche senha
            filled_pass = False
            for sel in password_selectors:
                el = await self.page.query_selector(sel)
                if el:
                    await self.page.fill(sel, password)
                    filled_pass = True
                    break
            if not filled_pass:
                # Tenta dentro de iframes
                try:
                    for frame in self.page.frames:
                        el = await frame.query_selector(', '.join(password_selectors))
                        if el:
                            await el.fill(password)
                            filled_pass = True
                            break
                except Exception:
                    pass
            if not filled_pass:
                # Debug de falha de senha
                try:
                    logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
                    os.makedirs(logs_dir, exist_ok=True)
                    await self.page.screenshot(path=os.path.join(logs_dir, 'login_password_missing.png'))
                except Exception:
                    pass
                raise Exception('Campo de senha não encontrado na página de login do LinkedIn')
            # Clica enviar (com fallback)
            submit_selectors = ['button[type="submit"]', '[data-id="sign-in-form__submit-btn"]', '[aria-label="Sign in"]']
            clicked = False
            for sel in submit_selectors:
                btn = await self.page.query_selector(sel)
                if btn:
                    await btn.click()
                    clicked = True
                    break
            if not clicked:
                # Fallback: Enter
                await self.page.keyboard.press('Enter')
            # Aguarda navegação para feed/messaging/checkpoint ou intervenção do usuário (CAPTCHA/2FA)
            import re as _re
            try:
                await self.page.wait_for_url(_re.compile(r"https://www\\.linkedin\\.com/(feed|messaging|login-submit|checkpoint)"), timeout=20000)
            except Exception:
                await self.page.wait_for_timeout(3000)
            # Loop de verificação por até 180s para permitir 2FA/CAPTCHA manual
            total_ms = 0
            while total_ms <= 180000:
                if await self.is_logged_in():
                    return True
                # Se estiver em checkpoint, aguarda usuário resolver
                # Mantém a aba ativa
                try:
                    await self.page.bring_to_front()
                except Exception:
                    pass
                await self.page.wait_for_timeout(2000)
                total_ms += 2000
            raise Exception('Login não confirmado após aguardar 180s. Pode haver CAPTCHA, 2FA ou credenciais inválidas.')
        except Exception as e:
            # Debug extra: salvar URL atual
            try:
                logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
                os.makedirs(logs_dir, exist_ok=True)
                with open(os.path.join(logs_dir, 'login_out.txt'), 'a', encoding='utf-8') as f:
                    f.write(f"[{asyncio.get_running_loop().time()}] ERRO LOGIN: {str(e)}\n")
                    try:
                        f.write(f"URL: {self.page.url}\n")
                    except Exception:
                        pass
            except Exception:
                pass
            # Propaga com mensagem clara para aparecer no detail do 500
            raise Exception(f"Falha no login do LinkedIn: {e}")

    async def is_logged_in(self) -> bool:
        try:
            # Primeiro verifica se a página está acessível
            if not self.page or self.page.is_closed():
                return False
            url = self.page.url or ''
            # Se estamos explícitamente na tela de login
            if 'linkedin.com/login' in url:
                return False
            # Se estamos em uma página de mensagens, assume logado (evita falsos negativos)
            if '/messaging/' in url:
                return True
            # Se existem campos de login na página atual
            if await self.page.query_selector('input[name="session_key"], input#username'):
                return False
            # Sinais comuns de sessão ativa
            if await self.page.query_selector('nav.global-nav, #global-nav, a[href*="/messaging/"], [data-test-global-nav-link]'):
                return True
            # Se o container de mensagens existe, também é sinal de sessão
            if await self.page.query_selector('.msg-conversations-container__conversations-list, [data-conversation-id]'):
                return True
        except Exception:
            pass
        return False

    def _parse_timestamp(self, text: Optional[str]) -> Optional[datetime]:
        # Tenta ISO 8601 direto
        if not text:
            return None
        text = text.strip()
        # Tenta atributo datetime como ISO
        try:
            # Normaliza Z -> +00:00 quando possível
            if text.endswith('Z'):
                return datetime.fromisoformat(text.replace('Z', '+00:00')).replace(tzinfo=None)
            return datetime.fromisoformat(text)
        except Exception:
            pass
        # Tenta formatos simples AAAA-MM-DD HH:MM
        try:
            return datetime.strptime(text, '%Y-%m-%d %H:%M')
        except Exception:
            pass
        try:
            return datetime.strptime(text, '%Y-%m-%d')
        except Exception:
            pass
        # Tenta padrões relativos comuns (pt/en)
        m = re.search(r'(\d+)\s*(minute|min|minutos?)\s*(ago|atr[aá]s)', text, re.I)
        if m:
            return datetime.utcnow() - timedelta(minutes=int(m.group(1)))
        m = re.search(r'(\d+)\s*(hour|hora|horas)\s*(ago|atr[aá]s)', text, re.I)
        if m:
            return datetime.utcnow() - timedelta(hours=int(m.group(1)))
        m = re.search(r'(\d+)\s*(day|dia|dias)\s*(ago|atr[aá]s)', text, re.I)
        if m:
            return datetime.utcnow() - timedelta(days=int(m.group(1)))
        m = re.search(r'(\d+)\s*(week|semana|semanas)\s*(ago|atr[aá]s)', text, re.I)
        if m:
            return datetime.utcnow() - timedelta(weeks=int(m.group(1)))
        m = re.search(r'(\d+)\s*(month|m[eê]s|meses)\s*(ago|atr[aá]s)', text, re.I)
        if m:
            # Aproxima mês como 30 dias
            return datetime.utcnow() - timedelta(days=30*int(m.group(1)))
        return None

    async def fetch_messages(self, days_limit: int = 90):
        # Verifica se está logado ANTES de navegar
        if not await self.is_logged_in():
            raise Exception('Não autenticado no LinkedIn. Use POST /linkedin/login primeiro.')
        
        # Só navega para mensagens se não estiver já em uma página de mensagens
        current_url = self.page.url or ''
        if '/messaging/' not in current_url:
            # Usa navegação stealth para evitar bloqueios
            success = await self.navigate_stealth('https://www.linkedin.com/messaging/')
            if not success:
                logger.warning("Navegação stealth falhou, tentando navegação direta")
                await self.page.goto('https://www.linkedin.com/messaging/', wait_until='domcontentloaded')
        
        # Aguarda lista de conversas com tolerância aumentada - usando sleep explícito
        await self.page.wait_for_timeout(8000)
        
        # Tenta obter o nome do próprio usuário para verificar se a mensagem foi respondida
        my_name = "Eu"
        try:
            me_img = await self.page.query_selector('.global-nav__me-photo')
            if me_img:
                alt_txt = await me_img.get_attribute('alt')
                if alt_txt:
                    my_name = alt_txt.strip()
        except Exception:
            pass

        conversations = await self.page.query_selector_all('.msg-conversation-listitem, .msg-conversations-container__convo-item')
        result = []
        cutoff = datetime.utcnow() - timedelta(days=days_limit)
        
        # Limita para evitar muito processamento
        for i, c in enumerate(conversations[:15]):
            try:
                # Clica na conversa para carregar as mensagens
                await c.click()
                await self.page.wait_for_timeout(1500)  # Delay aumentado
                
                # Pega o ID da conversa da URL
                current_url = self.page.url
                import re
                match = re.search(r'/messaging/thread/([^/]+)', current_url)
                cid = match.group(1) if match else f"conv_{i}_{datetime.utcnow().timestamp()}"
                
                msgs = await self.page.query_selector_all('.msg-s-message-list__event')
                if not msgs:
                    continue
                
                last = msgs[-1]
                text = (await last.inner_text()) or ''
                
                # Extrair Headline / Cargo do remetente
                headline_el = await self.page.query_selector('h2.msg-thread__thread-details-subtitle, .msg-thread__thread-details-role, .msg-thread__topcard h2, .msg-entity-lockup__entity-info')
                headline = await headline_el.inner_text() if headline_el else ""
                
                # Timestamp heurístico
                ts_el = await last.query_selector('time')
                ts_val = None
                if ts_el:
                    ts_val = await ts_el.get_attribute('datetime')
                    if not ts_val:
                        ts_val = await ts_el.inner_text()
                if not ts_val:
                    # Outros seletores comuns
                    ts2 = await last.query_selector('.msg-s-message-list__time-stamp, .msg-s-message-group__timestamp, .msg-s-message-list__time-heading')
                    if ts2:
                        ts_val = await ts2.inner_text()
                
                ts_dt = self._parse_timestamp(ts_val) if ts_val else None
                if ts_dt and ts_dt < cutoff:
                    # Ignora mensagens antigas
                    continue
                
                # Criar um ID único baseado no texto + cid
                uid = hashlib.sha1(f"{cid}|{text}".encode('utf-8')).hexdigest()[:16]
                
                # Extrair nome do remetente
                sender_el = await last.query_selector('.msg-s-message-group__profile-link, .msg-s-message-group__name, .msg-s-event-listitem__link img')
                if sender_el:
                    tag = await sender_el.evaluate('el => el.tagName.toLowerCase()')
                    if tag == 'img':
                        sender = await sender_el.get_attribute('alt')
                    else:
                        sender = await sender_el.inner_text()
                else:
                    sender = 'Desconhecido'
                
                sender_name = sender.strip() if sender else 'Desconhecido'
                
                # Tratar vazamento de texto no nome do remetente (ex: "19 DE FEV. Ver perfil de Vinicius Vinicius Figueiredo 08:12...")
                if len(sender_name) > 30 and 'Vinicius Figueiredo' in sender_name:
                    sender_name = 'Vinicius Figueiredo'
                elif len(sender_name) > 30:
                    # Tenta pegar apenas a primeira linha útil ou um pedaço curto
                    parts = sender_name.split()
                    if len(parts) > 2:
                        sender_name = f"{parts[0]} {parts[1]}"
                
                # Consideramos nova/não respondida se o remetente da última msg não for o usuário
                is_unreplied = (
                    sender_name != my_name and 
                    sender_name != 'Eu' and 
                    sender_name != 'Me' and 
                    'Vinicius Figueiredo' not in sender_name and
                    my_name not in sender_name
                )
                
                result.append({
                    "id": uid,
                    "conversation_id": cid,
                    "text": text.strip(),
                    "sender": sender_name,
                    "sender_headline": headline.strip(),
                    "is_unreplied": is_unreplied,
                    "timestamp": (ts_dt.isoformat() if ts_dt else (ts_val.strip() if ts_val else None))
                })
                
                # Pequeno delay entre conversas para parecer humano
                await self.page.wait_for_timeout(800)
                
            except Exception as e:
                logger.warning(f"Erro ao processar conversa index {i}: {e}")
                # Ignora conversas problemáticas e continua
                continue
        
        return result

    async def reply(self, conversation_id: str, text: str):
        # Vai direto para a URL da thread se tivermos o URN real!
        if conversation_id.startswith("2-") or conversation_id.startswith("urn:li:"):
            url = f"https://www.linkedin.com/messaging/thread/{conversation_id}/"
            await self.navigate_stealth(url)
            await self.page.wait_for_timeout(2000)
        else:
            # Fallback para tentar navegar para /messaging/ e achar pelo data-conversation-id (legado)
            await self.page.goto('https://www.linkedin.com/messaging/')
            await self.page.wait_for_timeout(2000)
            conv = await self.page.query_selector(f'[data-conversation-id="{conversation_id}"]')
            if conv:
                await conv.click()
                await self.page.wait_for_timeout(1500)
                
        # Procura a caixa de texto usando os seletores modernos
        textbox = await self.page.query_selector('.msg-form__contenteditable[role="textbox"], div[role="textbox"]')
        if textbox:
            # Verifica se o bot decidiu enviar currículo
            send_resume = "[SEND_RESUME]" in text
            if send_resume:
                text = text.replace("[SEND_RESUME]", "").strip()
                
            await textbox.fill(text)
            await self.page.wait_for_timeout(500)
            
            # Executa a ação de upload do arquivo de currículo
            if send_resume:
                try:
                    import os
                    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
                    # Encontrar a extensão atual do resume lendo o banco indiretamente, ou testando
                    resume_path = None
                    for ext in [".pdf", ".doc", ".docx"]:
                        test_path = os.path.join(data_dir, f"resume{ext}")
                        if os.path.exists(test_path):
                            resume_path = test_path
                            break
                            
                    if resume_path:
                        # No LinkedIn, o botão de anexo geralmente tem input type file oculto
                        file_input = await self.page.query_selector('input[type="file"]')
                        if file_input:
                            await file_input.set_input_files(resume_path)
                            await self.page.wait_for_timeout(2500)  # Aguarda upload visual
                            logger.info(f"Currículo anexado com sucesso: {resume_path}")
                        else:
                            logger.error("Falha ao localizar o input de anexo no chat do LinkedIn.")
                except Exception as e:
                    logger.error(f"Erro ao tentar anexar currículo: {e}")
            
            # Tenta clicar no botão de enviar
            send_btn = await self.page.query_selector('.msg-form__send-button')
            if send_btn and await send_btn.is_enabled():
                await send_btn.click()
            else:
                await self.page.keyboard.press('Enter')
            
            await self.page.wait_for_timeout(1500)
            return True
        else:
            logger.error("Caixa de texto de resposta não encontrada.")
            return False

    async def navigate_stealth(self, url: str, timeout: int = 30000):
        """
        Navegação gradual com técnicas anti-detecção para evitar bloqueios do LinkedIn
        """
        try:
            # Primeiro vai para uma página neutra para "quebrar" padrões de navegação
            await self.page.goto('https://www.google.com', wait_until='domcontentloaded', timeout=10000)
            await self.page.wait_for_timeout(2000)  # Delay humano
            
            # Depois vai para a página inicial do LinkedIn
            await self.page.goto('https://www.linkedin.com/feed', wait_until='domcontentloaded', timeout=15000)
            await self.page.wait_for_timeout(3000)  # Delay humano maior
            
            # Finalmente navega para o destino final
            await self.page.goto(url, wait_until='domcontentloaded', timeout=timeout)
            await self.page.wait_for_timeout(1000)  # Pequeno delay final
            
            return True
            
        except Exception as e:
            logger.warning(f"Navegação stealth falhou: {e}")
            # Fallback para navegação direta
            try:
                await self.page.goto(url, wait_until='domcontentloaded', timeout=timeout)
                return True
            except Exception:
                return False

    async def scrape_profile(self, url: Optional[str] = None):
        target = url or 'https://www.linkedin.com/in/me/'
        
        # Usa navegação stealth para evitar bloqueios
        success = await self.navigate_stealth(target)
        if not success:
            raise Exception("Falha na navegação para o perfil")
            
        # Tenta aguardar o conteúdo principal do perfil
        await self.page.wait_for_timeout(2000)
        profile = {}
        # Nome/Headline
        try:
            name_el = await self.page.query_selector('main h1')
            profile['name'] = (await name_el.inner_text()).strip() if name_el else None
        except Exception:
            profile['name'] = None
        try:
            headline_el = await self.page.query_selector('main .text-body-medium, main .pv-text-details__left-panel div')
            profile['headline'] = (await headline_el.inner_text()).strip() if headline_el else None
        except Exception:
            profile['headline'] = None
        # Coleta seções por título (About/Experiência/Educação/Skills)
        async def extract_section(keywords: list[str]) -> Optional[str]:
            sections = await self.page.query_selector_all('section')
            for s in sections:
                try:
                    t = (await s.inner_text()) or ''
                    for kw in keywords:
                        if kw.lower() in t.lower():
                            return t.strip()
                except Exception:
                    continue
            return None
        profile['about'] = await extract_section(['About', 'Sobre'])
        profile['experience'] = await extract_section(['Experience', 'Experiência'])
        profile['education'] = await extract_section(['Education', 'Formação'])
        profile['skills'] = await extract_section(['Skills', 'Competências'])
        return profile

    async def reply_with_ember_id(self, ember_id: str, text: str):
        """
        Método alternativo para responder usando ember ID das conversas
        """
        try:
            # Verifica se está logado
            if not await self.is_logged_in():
                raise Exception('Não autenticado no LinkedIn')
            
            # Navega para mensagens se necessário
            current_url = self.page.url or ''
            if '/messaging/' not in current_url:
                await self.page.goto('https://www.linkedin.com/messaging/', wait_until='domcontentloaded', timeout=15000)
            
            # Aguarda a página carregar
            await self.page.wait_for_timeout(3000)
            
            # Procura pelo elemento da conversa usando o ember ID
            conversation_selector = f'#{ember_id}'
            conversation_element = await self.page.query_selector(conversation_selector)
            
            if not conversation_element:
                logger.error(f"Conversa com ID {ember_id} não encontrada")
                return False
            
            # Clica na conversa
            await conversation_element.click()
            await self.page.wait_for_timeout(2000)
            
            # Procura pelo campo de texto da mensagem
            text_selectors = [
                '.msg-form__contenteditable',
                '[data-placeholder="Escreva uma mensagem..."]',
                '.msg-form__msg-content-container--scrollable .ql-editor',
                'div[role="textbox"]'
            ]
            
            text_element = None
            for selector in text_selectors:
                try:
                    text_element = await self.page.wait_for_selector(selector, timeout=5000)
                    if text_element:
                        break
                except:
                    continue
            
            if not text_element:
                logger.error("Campo de texto da mensagem não encontrado")
                return False
            
            # Limpa o campo e digita a mensagem
            await text_element.click()
            await self.page.keyboard.press('Control+a')
            await text_element.fill(text)
            await self.page.wait_for_timeout(1000)
            
            # Envia a mensagem (Enter)
            await self.page.keyboard.press('Enter')
            await self.page.wait_for_timeout(2000)
            
            logger.info(f"Mensagem enviada com sucesso para conversa {ember_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para {ember_id}: {e}")
            return False