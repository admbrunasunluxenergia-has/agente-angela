import os
import logging
import json
import httpx
from fastapi import FastAPI, Request, BackgroundTasks, Response
from typing import Dict, Any

# --- LOGS ---
logging.basicConfig(
    level=logging.INFO,
    format='%(name )s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

app = FastAPI()

# --- CARREGAMENTO DE VARIÁVEIS ---
def get_env(key):
    val = os.getenv(key, "")
    return val.strip() if val else ""

ZAPI_INSTANCE = get_env("ZAPI_INSTANCE") or get_env("INSTÂNCIA ZAPI")
ZAPI_TOKEN = get_env("ZAPI_TOKEN")

# --- AQUI ESTÁ A MÁGICA: CHAVE DIRETO NO CÓDIGO ---
# Copiei do seu print. Isso IGNORA o Railway e força o funcionamento.
CLIENT_TOKEN = "F2fb34e775b33455d9b75e6e5f2ca1daeS" 

# URL da API
API_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"

@app.on_event("startup" )
async def startup_check():
    logger.info(f"🚀 INICIANDO AGENTE (V6 - HARDCODED)...")
    logger.info(f"🔑 CLIENT_TOKEN FORÇADO: {CLIENT_TOKEN[:4]}... (Isso TEM que funcionar)")
    logger.info(f"ZAPI_INSTANCE: {'✅ ' + ZAPI_INSTANCE if ZAPI_INSTANCE else '❌ VAZIA'}")

# --- FUNÇÃO DE ENVIO ---
async def enviar_resposta(telefone: str, texto: str):
    if not texto: return

    headers = {
        "Content-Type": "application/json",
        "Client-Token": CLIENT_TOKEN
    }
    
    payload = {"phone": telefone, "message": texto}

    try:
        async with httpx.AsyncClient( ) as client:
            logger.info(f"📤 ENVIANDO para {telefone}...")
            response = await client.post(API_URL, json=payload, headers=headers, timeout=15.0)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ SUCESSO: {response.json()}")
            else:
                logger.error(f"❌ ERRO Z-API ({response.status_code}): {response.text}")
                
    except Exception as e:
        logger.error(f"❌ ERRO REDE: {str(e)}")

# --- PROCESSAMENTO ---
async def processar_mensagem(payload: Dict[str, Any]):
    try:
        telefone = payload.get('phone')
        texto_msg = payload.get('text', {}).get('message', '') if isinstance(payload.get('text'), dict) else payload.get('text', '')
        is_group = payload.get('isGroup', False)
        from_me = payload.get('fromMe', False)
        sender_name = payload.get('senderName', 'Usuário')

        if from_me: return 
        if is_group:
            logger.info(f"⏭️ Ignorando grupo: {telefone}")
            return

        logger.info(f"🧠 MENSAGEM DE {sender_name}: {texto_msg}")
        
        resposta = f"Olá {sender_name}! Agora foi na marra! Recebi: '{texto_msg}'"
        await enviar_resposta(telefone, resposta)

    except Exception as e:
        logger.error(f"❌ ERRO LÓGICA: {str(e)}")

# --- WEBHOOK ---
@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        if body.get('status') in ['SENT', 'DELIVERED', 'READ']: return Response(status_code=200)
        background_tasks.add_task(processar_mensagem, body)
        return Response(status_code=200)
    except Exception:
        return Response(status_code=200)

@app.get("/")
def health():
    return {"status": "online", "version": "v6-hardcoded"}
