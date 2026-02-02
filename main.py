import os
import requests
from fastapi import FastAPI, Request, HTTPException
from openai import OpenAI
import logging

# --- Configuração de Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Inicialização do FastAPI ---
app = FastAPI()

# --- Carregamento das Variáveis de Ambiente ---
# Usando os nomes EXATOS como aparecem no Railway (com suporte para variações)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ZAPI_INSTANCE = os.getenv("INSTÂNCIA_ZAPI") or os.getenv("INSTANCIA_ZAPI") or os.getenv("ZAPI_INSTANCE")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_TOKEN")

# --- Verificação de Variáveis Essenciais ---
if not all([OPENAI_API_KEY, ZAPI_INSTANCE, ZAPI_TOKEN, ZAPI_CLIENT_TOKEN]):
    logger.error("ERRO CRÍTICO: Uma ou mais variáveis de ambiente não foram configuradas.")
    logger.error(f"OPENAI_API_KEY: {'OK' if OPENAI_API_KEY else 'FALTANDO'}")
    logger.error(f"ZAPI_INSTANCE: {'OK' if ZAPI_INSTANCE else 'FALTANDO'}")
    logger.error(f"ZAPI_TOKEN: {'OK' if ZAPI_TOKEN else 'FALTANDO'}")

# --- Inicialização do Cliente OpenAI ---
client = OpenAI(api_key=OPENAI_API_KEY)

# --- Persona do Agente Ângela ---
ANGELA_PROMPT = '''
Você é Ângela, a recepcionista da SUNLUX ENERGIA. 
Seu perfil é educado, humano, profissional e claro.
Sua função é o atendimento inicial.

REGRAS OBRIGATÓRIAS:
1.  NUNCA se apresente como robô ou IA. Aja sempre como uma pessoa real.
2.  Sempre inicie o PRIMEIRO contato com a frase: "Olá 😊 sou a Ângela, da SUNLUX ENERGIA. Como posso te ajudar?"
3.  NÃO tome decisões, NÃO prometa prazos, NÃO feche contratos e NÃO defina valores.
4.  Seu objetivo é entender a intenção do cliente e coletar informações básicas.
5.  Se o cliente pedir para falar com um humano, reclamar, perguntar sobre fechamento de contrato, valores ou prazos, informe que a equipe responsável entrará em contato.
'''

# --- Função para Enviar Mensagem via Z-API ---
def send_whatsapp_message(phone_number: str, message: str):
    """
    Envia uma mensagem de texto para um número de WhatsApp usando a Z-API.
    """
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"
    
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_CLIENT_TOKEN
    }
    
    payload = {
        "phone": phone_number,
        "message": message
    }
    
    try:
        logger.info(f"Enviando mensagem para {phone_number}..." )
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        logger.info(f"Resposta da Z-API: {response.json()}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao enviar mensagem via Z-API para {phone_number}: {e}")
        return None

# --- Endpoint de Status ---
@app.get("/")
def read_root():
    return {"status": "Agente Ângela Online"}

# --- Endpoint Principal (Webhook) ---
@app.post("/webhook")
async def webhook_handler(request: Request):
    """
    Recebe as mensagens do WhatsApp via Z-API, processa com a IA e responde.
    """
    try:
        data = await request.json()
        logger.info(f"Webhook recebido: {data}")

        phone = data.get("phone")
        message_text = data.get("text", {}).get("message")

        if not phone or not message_text or data.get("fromMe"):
            logger.info("Mensagem ignorada (sem texto, sem telefone ou de autoria própria).")
            return {"status": "ignored"}

        # 1. Processar com a OpenAI para obter a resposta da Ângela
        logger.info(f"Processando mensagem de {phone} com a OpenAI...")
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": ANGELA_PROMPT,
                },
                {
                    "role": "user",
                    "content": message_text,
                },
            ],
            model="gpt-4.1-mini",
        )
        
        response_text = chat_completion.choices[0].message.content
        logger.info(f"Resposta gerada pela IA: {response_text}")

        # 2. Enviar a resposta de volta para o cliente via Z-API
        send_whatsapp_message(phone, response_text)

        # 3. Retornar 200 OK para a Z-API para confirmar o recebimento
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Erro inesperado no webhook: {e}")
        return {"status": "error", "detail": str(e)}
