import os
import requests
import json
import psycopg2
from fastapi import FastAPI, Request
from openai import OpenAI
import logging

# --- Configuração de Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Inicialização do FastAPI ---
app = FastAPI()

# --- Carregamento das Variáveis de Ambiente ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Tenta ler a instância Z-API de TODAS as formas possíveis
ZAPI_INSTANCE = (
    os.getenv("ZAPI_INSTANCE") or 
    os.getenv("INSTANCIA_ZAPI") or 
    os.getenv("INSTÂNCIA_ZAPI") or
    os.getenv("ID_INSTANCIA_ZAPI") or
    os.getenv("ID_INSTÂNCIA_ZAPI") or
    "3E1F5556754D707D83290A427663C12F"  # Fallback: ID fixo
)

ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_TOKEN")

# ClickUp
CLICKUP_API_TOKEN = os.getenv("CLICKUP_API_TOKEN") or os.getenv("CLIQUE_TOKEN")
CLICKUP_LIST_ID_ATENDIMENTO = os.getenv("CLICKUP_LIST_ID_ATENDIMENTO") or os.getenv("CLICKUP_LIST_ATENDIMENTO")
CLICKUP_LIST_ID_VENDAS = os.getenv("CLICKUP_LIST_ID_VENDAS") or os.getenv("CLICKUP_LIST_FUNIL")

# Postgres
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("URL_DO_BANCO_DE_DADOS")

# --- Log de Verificação ---
logger.info("=== VERIFICAÇÃO DE VARIÁVEIS ===")
logger.info(f"OPENAI_API_KEY: {'✅ OK' if OPENAI_API_KEY else '❌ FALTANDO'}")
logger.info(f"ZAPI_INSTANCE: ✅ {ZAPI_INSTANCE}")
logger.info(f"ZAPI_TOKEN: {'✅ OK' if ZAPI_TOKEN else '❌ FALTANDO'}")
logger.info(f"CLICKUP_API_TOKEN: {'✅ OK' if CLICKUP_API_TOKEN else '⚠️  OPCIONAL'}")
logger.info(f"DATABASE_URL: {'✅ OK' if DATABASE_URL else '⚠️  OPCIONAL'}")

# --- Inicialização do Cliente OpenAI ---
client = OpenAI(api_key=OPENAI_API_KEY)

# --- Gestão de Sessão (Etapa 1) ---
conversation_history = {}

# --- Prompts dos Agentes ---
ANGELA_PROMPT = '''
Você é Ângela, a recepcionista da SUNLUX ENERGIA. Sua função é o atendimento inicial e a triagem.

REGRAS OBRIGATÓRIAS:
1. Analise a mensagem do usuário. Sua resposta DEVE ser um objeto JSON.
2. O JSON deve ter dois campos: "intent" e "response_text".
3. O campo "intent" deve ser "venda" se o usuário demonstrar qualquer interesse comercial (orçamento, comprar, instalar painel solar, economia de energia, etc.). Caso contrário, deve ser "atendimento_geral".
4. O campo "response_text" é a sua resposta amigável para o usuário.
5. NUNCA se apresente como robô ou IA. Aja como uma pessoa real.
6. Na primeira mensagem, sempre se apresente: "Olá 😊 sou a Ângela, da SUNLUX ENERGIA. Como posso te ajudar?"
7. Exemplo de resposta para interesse comercial: {"intent": "venda", "response_text": "Que ótimo! Vou te transferir para a nossa consultora de vendas, a Raquel. Ela já vai te atender."}
8. Exemplo de resposta para dúvida geral: {"intent": "atendimento_geral", "response_text": "Entendi. Sobre esse assunto, a nossa equipe responsável entrará em contato em breve."}
9. Seja educada, profissional e clara.
10. Não prometa prazos, valores ou decisões técnicas.
'''

RAQUEL_PROMPT = '''
Você é Raquel, a consultora de vendas especialista da SUNLUX ENERGIA. Você acaba de receber um cliente transferido pela Ângela.

REGRAS OBRIGATÓRIAS:
1. Apresente-se e agradeça o interesse. Ex: "Olá! Sou a Raquel, consultora da SUNLUX ENERGIA. A Ângela me passou seu contato. Fico feliz em ajudar! Para começarmos, pode me dizer seu nome completo e a cidade onde você mora?"
2. Seu objetivo é qualificar o lead, coletando: Nome completo, Cidade, e a necessidade principal (economia na conta de luz, sustentabilidade, etc.).
3. Seja consultiva e humana. Faça uma pergunta por vez.
4. Não prometa prazos técnicos ou valores exatos sem análise.
5. Ao coletar as informações básicas, informe: "Perfeito, [Nome]! Com essas informações, nossa equipe técnica já consegue preparar uma análise personalizada. Registrei seu contato e em breve um de nossos especialistas te chamará para detalhar a proposta. Obrigada!"
6. NUNCA se apresente como robô ou IA.
'''

# --- Funções Utilitárias ---

def send_whatsapp_message(phone: str, message: str) -> bool:
    """Envia mensagem via Z-API"""
    if not ZAPI_INSTANCE or not ZAPI_TOKEN:
        logger.error("Configuração Z-API incompleta. Mensagem não enviada.")
        return False
    
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"
    headers = {"Content-Type": "application/json", "Client-Token": ZAPI_CLIENT_TOKEN}
    payload = {"phone": phone, "message": message}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"✅ Mensagem enviada para {phone}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erro ao enviar mensagem para {phone}: {e}")
        return False


def create_clickup_task(list_id: str, task_name: str, description: str):
    """Cria uma task no ClickUp (Etapa 4)"""
    if not CLICKUP_API_TOKEN or not list_id:
        logger.warning("⚠️  ClickUp não configurado. Task não será criada.")
        return
    
    url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
    headers = {
        "Authorization": CLICKUP_API_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "name": task_name,
        "description": description
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"✅ Task criada no ClickUp: {task_name}")
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erro ao criar task no ClickUp: {e}")


def log_to_postgres(phone: str, sender: str, message: str):
    """Registra mensagem no Postgres (Etapa 5)"""
    if not DATABASE_URL:
        logger.warning("⚠️  DATABASE_URL não configurada. Log não salvo no Postgres.")
        return
    
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Verifica se a tabela existe, se não, cria
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id SERIAL PRIMARY KEY,
                phone_number VARCHAR(20),
                sender VARCHAR(10),
                message TEXT,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
        # Insere o log
        cur.execute(
            "INSERT INTO conversation_logs (phone_number, sender, message) VALUES (%s, %s, %s)",
            (phone, sender, message)
        )
        conn.commit()
        cur.close()
        logger.info(f"✅ Log salvo no Postgres: {sender} - {phone}")
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"❌ Erro ao logar no Postgres: {error}")
    finally:
        if conn is not None:
            conn.close()


def run_raquel_conversation(phone: str, user_history: list):
    """Executa conversa com a Raquel (Etapa 3)"""
    logger.info(f"🔄 Iniciando conversa com Raquel para {phone}")
    
    # Prepara mensagens para a Raquel
    messages_for_raquel = [
        {"role": "system", "content": RAQUEL_PROMPT}
    ] + user_history
    
    # Chama OpenAI
    chat_completion = client.chat.completions.create(
        messages=messages_for_raquel,
        model="gpt-4o-mini",
    )
    raquel_response = chat_completion.choices[0].message.content
    
    # Envia mensagem
    send_whatsapp_message(phone, raquel_response)
    
    # Atualiza histórico
    user_history.append({"role": "assistant", "content": raquel_response})
    conversation_history[phone] = user_history[-10:]
    
    # Log no Postgres
    log_to_postgres(phone, "raquel", raquel_response)


# --- Endpoints ---

@app.get("/")
async def root():
    """Endpoint de status"""
    return {
        "status": "online",
        "service": "Agente Ângela - SUNLUX ENERGIA",
        "openai": "✅" if OPENAI_API_KEY else "❌",
        "zapi": "✅" if ZAPI_INSTANCE and ZAPI_TOKEN else "❌",
        "clickup": "✅" if CLICKUP_API_TOKEN else "⚠️",
        "postgres": "✅" if DATABASE_URL else "⚠️"
    }


@app.post("/webhook")
async def webhook_handler(request: Request):
    """Processa mensagens do WhatsApp via Z-API"""
    try:
        data = await request.json()
        logger.info(f"📩 Webhook recebido: {data}")
        
        # Extrai dados da mensagem
        phone = data.get("phone")
        message_text = data.get("text", {}).get("message") if isinstance(data.get("text"), dict) else data.get("text")
        from_me = data.get("fromMe", False)
        is_group = data.get("isGroup", False)
        
        # Ignora mensagens próprias e de grupos
        if not phone or not message_text or from_me or is_group:
            logger.info(f"⏭️  Mensagem ignorada - phone: {phone}, fromMe: {from_me}, isGroup: {is_group}")
            return {"status": "ignored"}
        
        # Log no Postgres (entrada do usuário)
        log_to_postgres(phone, "user", message_text)
        
        # ETAPA 1: Recupera ou inicializa histórico
        user_history = conversation_history.get(phone, [])
        user_history.append({"role": "user", "content": message_text})
        
        # Prepara mensagens para a OpenAI (Ângela)
        messages_for_openai = [
            {"role": "system", "content": ANGELA_PROMPT}
        ] + user_history
        
        # Chama OpenAI
        logger.info(f"🤖 Processando com OpenAI para {phone}...")
        chat_completion = client.chat.completions.create(
            messages=messages_for_openai,
            model="gpt-4o-mini",
        )
        
        response_text = chat_completion.choices[0].message.content
        logger.info(f"💬 Resposta da IA: {response_text}")
        
        # ETAPA 2: Processa resposta JSON da Ângela
        try:
            ia_decision = json.loads(response_text)
            intent = ia_decision.get("intent")
            angela_response = ia_decision.get("response_text")
            
            # Envia resposta da Ângela
            send_whatsapp_message(phone, angela_response)
            
            # Atualiza histórico
            user_history.append({"role": "assistant", "content": angela_response})
            conversation_history[phone] = user_history[-10:]
            
            # Log no Postgres (resposta da Ângela)
            log_to_postgres(phone, "angela", angela_response)
            
            # ETAPA 2 e 3: Lógica de Handoff
            if intent == "venda":
                logger.info(f"🔀 HANDOFF: Intenção de venda detectada para {phone}. Acionando Raquel...")
                
                # ETAPA 4: Registra no ClickUp (Vendas)
                if CLICKUP_LIST_ID_VENDAS:
                    task_description = f"Lead vindo do WhatsApp.\n\nTelefone: {phone}\n\nHistórico:\n{json.dumps(user_history, indent=2, ensure_ascii=False)}"
                    create_clickup_task(CLICKUP_LIST_ID_VENDAS, f"Novo Lead - {phone}", task_description)
                
                # Chama Raquel
                run_raquel_conversation(phone, user_history)
                
            else:
                logger.info(f"✅ Atendimento geral concluído por Ângela para {phone}")
                
                # ETAPA 4: Registra no ClickUp (Atendimento)
                if CLICKUP_LIST_ID_ATENDIMENTO:
                    task_description = f"Atendimento geral via WhatsApp.\n\nTelefone: {phone}\n\nÚltima mensagem: {message_text}\n\nResposta: {angela_response}"
                    create_clickup_task(CLICKUP_LIST_ID_ATENDIMENTO, f"Atendimento - {phone}", task_description)
            
            return {"status": "ok", "processed": True}
            
        except json.JSONDecodeError:
            logger.error("❌ Erro: Resposta da OpenAI não é JSON válido. Enviando resposta direta.")
            send_whatsapp_message(phone, response_text)
            log_to_postgres(phone, "angela", response_text)
            return {"status": "ok", "fallback": True}
    
    except Exception as e:
        logger.error(f"❌ Erro inesperado no webhook: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "detail": str(e)}
