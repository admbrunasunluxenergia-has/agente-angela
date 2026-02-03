import os
import logging
import json
import httpx
from fastapi import FastAPI, Request, BackgroundTasks, Response
from typing import Dict, Any

# --- CONFIGURAÇÃO DE LOGS (CRÍTICO PARA DIAGNÓSTICO ) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

app = FastAPI()

# --- CONFIGURAÇÕES E VARIÁVEIS ---
# Garante que não quebre se a variável não existir, mas avisa no log
ZAPI_INSTANCE = os.getenv("ZAPI_INSTANCE", "")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# URL da API do WhatsApp (Z-API)
API_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"

@app.on_event("startup" )
async def startup_check():
    """Verifica saúde das variáveis ao iniciar"""
    logger.info(f"🚀 INICIANDO AGENTE...")
    logger.info(f"ZAPI_INSTANCE: {'✅ Definida' if ZAPI_INSTANCE else '❌ AUSENTE'}")
    logger.info(f"ZAPI_TOKEN: {'✅ Definido' if ZAPI_TOKEN else '❌ AUSENTE'}")

# --- FUNÇÃO DE ENVIO BLINDADA ---
async def enviar_resposta(telefone: str, texto: str):
    """Envia mensagem e LOGA o resultado (Sucesso ou Erro)"""
    if not texto:
        logger.warning(f"⚠️ Tentativa de enviar texto vazio para {telefone}")
        return

    headers = {"Content-Type": "application/json"}
    payload = {"phone": telefone, "message": texto}

    try:
        async with httpx.AsyncClient( ) as client:
            logger.info(f"📤 ENVIANDO para {telefone}...")
            # Timeout de 15s para evitar travamentos
            response = await client.post(API_URL, json=payload, headers=headers, timeout=15.0)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ SUCESSO NO ENVIO: {response.json()}")
            else:
                # Loga o erro exato que a Z-API retornou
                logger.error(f"❌ ERRO API ({response.status_code}): {response.text}")
                
    except Exception as e:
        logger.error(f"❌ EXCEÇÃO DE REDE: {str(e)}")

# --- LÓGICA DE PROCESSAMENTO ---
async def processar_mensagem(payload: Dict[str, Any]):
    try:
        # Extração segura dos dados
        telefone = payload.get('phone')
        
        # Z-API pode mandar o texto direto ou dentro de um objeto
        texto_msg = payload.get('text', {}).get('message', '') if isinstance(payload.get('text'), dict) else payload.get('text', '')
        
        is_group = payload.get('isGroup', False)
        from_me = payload.get('fromMe', False)
        sender_name = payload.get('senderName', 'Usuário')

        # 1. Filtro de Ignorância (Grupos e Eu mesmo)
        if from_me:
            return 
        if is_group:
            logger.info(f"⏭️ Ignorando grupo: {telefone}")
            return

        logger.info(f"🧠 MENSAGEM RECEBIDA de {sender_name}: {texto_msg}")
        
        # --- AQUI ENTRA SUA LÓGICA DE IA ---
        # Por enquanto, um eco simples para testar o fluxo
        resposta = f"Olá {sender_name}! Recebi sua mensagem: '{texto_msg}'. O sistema está respondendo corretamente."
        # -----------------------------------
        
        await enviar_resposta(telefone, resposta)

    except Exception as e:
        logger.error(f"❌ ERRO NA LÓGICA DO AGENTE: {str(e)}")

# --- WEBHOOK (A PORTA DE ENTRADA) ---
@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        
        # LOG DE ENTRADA (Para saber se chegou)
        # logger.info(f"📩 Payload: {json.dumps(body)}") # Descomente se precisar debugar o JSON bruto
        
        # FILTRO CRÍTICO: Ignorar eventos de status (Lido, Entregue, Enviado)
        # Se processar isso como mensagem, gera loop ou erro silencioso
        if body.get('status') in ['SENT', 'DELIVERED', 'READ']:
             return Response(status_code=200)

        # Se passou pelo filtro, é mensagem ou evento relevante -> Processar em background
        background_tasks.add_task(processar_mensagem, body)
        
        return Response(status_code=200)
        
    except Exception as e:
        logger.error(f"❌ ERRO NO WEBHOOK: {str(e)}")
        return Response(status_code=200)

@app.get("/")
def health():
    return {"status": "online", "version": "fix-v1"}
