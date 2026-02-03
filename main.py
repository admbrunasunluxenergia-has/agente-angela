import os
import requests
from fastapi import FastAPI, Request
from openai import OpenAI
import logging
import json

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# Variáveis
ZAPI_INSTANCE = os.getenv("ZAPI_INSTANCE") or os.getenv("INSTÂNCIA_ZAPI") or "3E1F5556754D707D83290A427663C12F"
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")

# Cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logger.info("="*60)
logger.info("🚀 AGENTE ÂNGELA - SUNLUX ENERGIA")
logger.info(f"📍 ZAPI Instance: {ZAPI_INSTANCE[:20]}...")
logger.info(f"🔑 ZAPI Token: {'✅' if ZAPI_TOKEN else '❌'}")
logger.info(f"🤖 OpenAI Key: {'✅' if os.getenv('OPENAI_API_KEY') else '❌'}")
logger.info("="*60)

def extract_message_text(data: dict) -> str:
    """Extrai texto da mensagem de múltiplos formatos Z-API"""
    # Tentar múltiplos caminhos possíveis
    possible_paths = [
        data.get("text", {}).get("message"),
        data.get("message", {}).get("text"),
        data.get("message", {}).get("conversation"),
        data.get("body"),
        data.get("content"),
        data.get("text"),
        data.get("message")
    ]
    
    for path in possible_paths:
        if path and isinstance(path, str) and path.strip():
            return path.strip()
    
    return None

def send_whatsapp_message(phone: str, message: str) -> bool:
    """Envia mensagem via Z-API"""
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"
    headers = {"Content-Type": "application/json", "Client-Token": ZAPI_TOKEN}
    payload = {"phone": phone, "message": message}
    
    logger.info(f"📤 Enviando para {phone}: {message[:50]}...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        logger.info(f"📡 Z-API Status: {response.status_code}")
        logger.info(f"📡 Z-API Response: {response.text[:200]}")
        
        if response.status_code == 200:
            logger.info(f"✅ ENVIADO COM SUCESSO")
            return True
        else:
            logger.error(f"❌ Falha: {response.text[:100]}")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao enviar: {e}")
        return False

@app.get("/")
def root():
    return {"status": "online", "agent": "Angela", "version": "3.0"}

@app.post("/webhook")
async def webhook(request: Request):
    """Webhook principal"""
    logger.info("="*60)
    logger.info("🔔 WEBHOOK ACIONADO")
    
    try:
        data = await request.json()
        
        # Log do payload completo para debug
        logger.info(f"📦 PAYLOAD COMPLETO: {json.dumps(data, indent=2)}")
        
        phone = data.get("phone") or data.get("from") or data.get("remoteJid")
        message_text = extract_message_text(data)
        from_me = data.get("fromMe", False)
        is_group = data.get("isGroup", False) or data.get("isGroupMsg", False)
        
        logger.info(f"📞 De: {phone}")
        logger.info(f"💬 Mensagem: {message_text}")
        logger.info(f"👤 De mim: {from_me} | Grupo: {is_group}")
        
        # Validações
        if not phone:
            logger.warning("⚠️  IGNORADO: Sem telefone")
            return {"status": "ignored", "reason": "no_phone"}
            
        if not message_text:
            logger.warning("⚠️  IGNORADO: Sem texto")
            return {"status": "ignored", "reason": "no_text"}
            
        if from_me:
            logger.warning("⚠️  IGNORADO: Mensagem própria")
            return {"status": "ignored", "reason": "from_me"}
            
        if is_group:
            logger.warning("⚠️  IGNORADO: Mensagem de grupo")
            return {"status": "ignored", "reason": "group"}
        
        # Processar com IA
        logger.info("🤖 Processando com IA...")
        
        try:
            completion = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Você é Ângela, atendente da SUNLUX ENERGIA. Seja educada, breve e profissional. Use emojis moderados."
                    },
                    {
                        "role": "user",
                        "content": message_text
                    }
                ],
                max_tokens=150
            )
            
            response_text = completion.choices[0].message.content
            logger.info(f"💡 Resposta IA: {response_text[:80]}...")
            
        except Exception as e:
            logger.error(f"❌ Erro na IA: {e}")
            # Fallback: resposta padrão
            response_text = "Olá! Sou a Ângela da SUNLUX ENERGIA. Como posso te ajudar? 😊"
            logger.info("💡 Usando resposta padrão")
        
        # Enviar resposta
        logger.info("📨 Iniciando envio...")
        success = send_whatsapp_message(phone, response_text)
        
        if success:
            logger.info("✅ ATENDIMENTO CONCLUÍDO")
            return {"status": "ok", "sent": True}
        else:
            logger.error("❌ FALHA NO ENVIO")
            return {"status": "error", "detail": "send_failed"}
    
    except Exception as e:
        logger.error(f"❌ ERRO GERAL: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "detail": str(e)}
    
    finally:
        logger.info("="*60)

@app.on_event("startup")
async def startup():
    logger.info("🎬 Sistema pronto - Aguardando mensagens...")
