import os
import logging
import json
import httpx
from fastapi import FastAPI, Request, BackgroundTasks, Response
from typing import Dict, Any

# --- LOGS SIMPLIFICADOS ---
logging.basicConfig(
    level=logging.INFO,
    format='%(name )s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

app = FastAPI()

# --- CONFIGURAÇÕES E VARIÁVEIS (BLINDAGEM) ---
# Tenta pegar o nome padrão (ZAPI_INSTANCE) OU o nome com acento (INSTÂNCIA ZAPI)
ZAPI_INSTANCE = os.getenv("ZAPI_INSTANCE") or os.getenv("INSTÂNCIA ZAPI") or ""
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN", "")
CLIENT_TOKEN = os.getenv("CLIENT_TOKEN", "")

# URL da API do WhatsApp (Z-API)
API_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"

@app.on_event("startup" )
async def startup_check():
    logger.info(f"🚀 INICIANDO AGENTE (V4 - FLEXÍVEL)...")
    
    # Loga qual variável foi encontrada para debug
    if os.getenv("ZAPI_INSTANCE"):
        logger.info("Usando variável: ZAPI_INSTANCE")
    elif os.getenv("INSTÂNCIA ZAPI"):
        logger.info("Usando variável: INSTÂNCIA ZAPI")
    else:
        logger.error("❌ Nenhuma variável de Instância encontrada!")

    logger.info(f"ID DA INSTÂNCIA: {'✅ Carregado' if ZAPI_INSTANCE else '❌ VAZIO'}")
    logger.info(f"ZAPI_TOKEN: {'✅ Definido' if ZAPI_TOKEN else '❌ AUSENTE'}")
    logger.info(f"CLIENT_TOKEN: {'✅ Definido' if CLIENT_TOKEN else '⚠️ NÃO DEFINIDO'}")

# --- FUNÇÃO DE ENVIO ---
async def enviar_resposta(telefone: str, texto: str):
    if not texto:
        return

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
                logger.info(f"✅ SUCESSO NO ENVIO: {response.json()}")
            else:
                logger.error(f"❌ ERRO API ({response.status_code}): {response.text}")
                
    except Exception as e:
        logger.error(f"❌ EXCEÇÃO DE REDE: {str(e)}")

# --- LÓGICA DE PROCESSAMENTO ---
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

        logger.info(f"🧠 MENSAGEM RECEBIDA de {sender_name}: {texto_msg}")
        
        # --- RESPOSTA DE TESTE ---
        resposta = f"Olá {sender_name}! Conexão estabelecida com sucesso. Recebi: '{texto_msg}'"
        
        await enviar_resposta(telefone, resposta)

    except Exception as e:
        logger.error(f"❌ ERRO NA LÓGICA DO AGENTE: {str(e)}")

# --- WEBHOOK ---
@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        
        if body.get('status') in ['SENT', 'DELIVERED', 'READ']:
             return Response(status_code=200)

        background_tasks.add_task(processar_mensagem, body)
        return Response(status_code=200)
        
    except Exception as e:
        logger.error(f"❌ ERRO NO WEBHOOK: {str(e)}")
        return Response(status_code=200)

@app.get("/")
def health():
    return {"status": "online", "version": "fix-v4-flexible-vars"}
