import os
import requests
from fastapi import FastAPI, Request
from openai import OpenAI
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

ZAPI_INSTANCE = os.getenv("ZAPI_INSTANCE") or "3E1F5556754D707D83290A427663C12F"
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# TEXTO PADRÃO GARANTIDO
FALLBACK_MESSAGE = "Olá! Sou a Ângela da SUNLUX ENERGIA. Recebemos sua mensagem e em breve um consultor entrará em contato. Como posso ajudar?"

logger.info("🚀 AGENTE ÂNGELA - SUNLUX ENERGIA")
logger.info(f"🔑 ZAPI Token: {'✅' if ZAPI_TOKEN else '❌'}")
logger.info(f"🤖 OpenAI Key: {'✅' if os.getenv('OPENAI_API_KEY') else '❌'}")

def extract_message_text(data: dict) -> str:
    paths = [
        data.get("text", {}).get("message"),
        data.get("message", {}).get("text"),
        data.get("message", {}).get("conversation"),
        data.get("body"),
        data.get("content"),
        data.get("text"),
        data.get("message")
    ]
    for path in paths:
        if path and isinstance(path, str) and path.strip():
            return path.strip()
    return None

def send_whatsapp_message(phone: str, message: str) -> dict:
    """Retorna: {"success": bool, "error_code": int|None, "error_type": str|None}"""
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"
    headers = {"Content-Type": "application/json", "Client-Token": ZAPI_TOKEN}
    payload = {"phone": phone, "message": message}
    
    logger.info(f"📤 Enviando: {message[:50]}...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        logger.info(f"📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("✅ ENVIADO")
            return {"success": True, "error_code": None, "error_type": None}
        elif response.status_code == 403:
            logger.error("❌ ERRO 403: Client-Token inválido")
            return {"success": False, "error_code": 403, "error_type": "auth"}
        else:
            logger.error(f"❌ ERRO {response.status_code}")
            return {"success": False, "error_code": response.status_code, "error_type": "api"}
    except Exception as e:
        logger.error(f"❌ EXCEÇÃO: {e}")
        return {"success": False, "error_code": None, "error_type": "network"}

@app.get("/")
def root():
    return {"status": "online", "agent": "Angela", "version": "4.0"}

@app.post("/webhook")
async def webhook(request: Request):
    logger.info("="*60)
    logger.info("🔔 WEBHOOK")
    
    try:
        data = await request.json()
        logger.info(f"📦 PAYLOAD: {json.dumps(data, indent=2)}")
        
        phone = data.get("phone") or data.get("from") or data.get("remoteJid")
        message_text = extract_message_text(data)
        from_me = data.get("fromMe", False)
        is_group = data.get("isGroup", False) or data.get("isGroupMsg", False)
        
        logger.info(f"📞 De: {phone}")
        logger.info(f"💬 Texto: {message_text}")
        logger.info(f"👤 FromMe: {from_me} | Grupo: {is_group}")
        
        # VALIDAÇÕES
        if not phone:
            logger.warning("⚠️ IGNORADO: Sem telefone")
            return {"status": "ignored", "reason": "no_phone"}
        
        if not message_text:
            logger.warning("⚠️ IGNORADO: Sem texto")
            return {"status": "ignored", "reason": "no_text"}
        
        if from_me:
            logger.warning("⚠️ IGNORADO: Mensagem própria")
            return {"status": "ignored", "reason": "from_me"}
        
        if is_group:
            logger.warning("⚠️ IGNORADO: Grupo")
            return {"status": "ignored", "reason": "group"}
        
        # VARIÁVEL DE RESPOSTA (SEMPRE DEFINIDA)
        response_text = None
        
        # TENTAR IA
        logger.info("🤖 Tentando IA...")
        try:
            completion = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "Você é Ângela, atendente da SUNLUX ENERGIA. Seja educada, breve e profissional."},
                    {"role": "user", "content": message_text}
                ],
                max_tokens=150
            )
            response_text = completion.choices[0].message.content
            logger.info(f"✅ IA OK: {response_text[:50]}...")
        except Exception as e:
            error_str = str(e)
            if "401" in error_str or "Incorrect API key" in error_str:
                logger.error("❌ IA ERRO 401: API Key inválida")
            else:
                logger.error(f"❌ IA ERRO: {error_str[:100]}")
            response_text = None
        
        # FALLBACK GARANTIDO
        if not response_text:
            response_text = FALLBACK_MESSAGE
            logger.info("💡 USANDO FALLBACK")
        
        # ENVIAR (SEMPRE TENTA)
        logger.info("📨 Enviando resposta...")
        result = send_whatsapp_message(phone, response_text)
        
        if result["success"]:
            logger.info("✅ CONCLUÍDO")
            return {"status": "ok", "sent": True, "used_fallback": response_text == FALLBACK_MESSAGE}
        else:
            # ERRO NO ENVIO
            if result["error_code"] == 403:
                logger.error("❌ FALHA CRÍTICA: Client-Token inválido no Z-API")
                return {"status": "error", "detail": "zapi_auth_failed", "error_code": 403}
            else:
                logger.error(f"❌ FALHA NO ENVIO: {result['error_type']}")
                return {"status": "error", "detail": "send_failed", "error_type": result["error_type"]}
    
    except Exception as e:
        logger.error(f"❌ ERRO GERAL: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "detail": str(e)}
    
    finally:
        logger.info("="*60)

@app.on_event("startup")
async def startup():
    logger.info("🎬 Pronto")
