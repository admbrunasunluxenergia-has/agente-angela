import os
import requests
from fastapi import FastAPI, Request
from openai import OpenAI
import logging

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Variáveis de ambiente
ZAPI_INSTANCE = os.getenv("ZAPI_INSTANCE") or os.getenv("INSTÂNCIA_ZAPI") or "3E1F5556754D707D83290A427663C12F"
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")

# Cliente OpenAI (usa API do Manus pré-configurada)
client = OpenAI()

logger.info("="*50)
logger.info("🚀 AGENTE ÂNGELA INICIADO")
logger.info(f"📍 ZAPI_INSTANCE: {ZAPI_INSTANCE[:20]}...")
logger.info(f"🔑 ZAPI_TOKEN: {'✅ Configurado' if ZAPI_TOKEN else '❌ FALTANDO'}")
logger.info("="*50)

def send_whatsapp_message(phone: str, message: str) -> bool:
    """Envia mensagem via Z-API com logs detalhados"""
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_TOKEN
    }
    payload = {
        "phone": phone,
        "message": message
    }
    
    logger.info(f"📤 Tentando enviar para {phone}")
    logger.info(f"📝 Mensagem: {message[:50]}...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        logger.info(f"📡 Status HTTP: {response.status_code}")
        logger.info(f"📡 Resposta Z-API: {response.text[:200]}")
        
        if response.status_code == 200:
            logger.info(f"✅ MENSAGEM ENVIADA COM SUCESSO para {phone}")
            return True
        else:
            logger.error(f"❌ FALHA NO ENVIO: Status {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ ERRO AO ENVIAR: {str(e)}")
        return False

@app.get("/")
def root():
    """Endpoint de status"""
    logger.info("📍 GET / - Health check")
    return {
        "status": "online",
        "agent": "Angela - Sunlux Energia",
        "version": "1.0"
    }

@app.post("/webhook")
async def webhook(request: Request):
    """Webhook principal - recebe mensagens do WhatsApp"""
    
    logger.info("="*50)
    logger.info("🔔 WEBHOOK ACIONADO!")
    
    try:
        # Recebe o payload
        data = await request.json()
        logger.info(f"📦 Payload recebido: {str(data)[:200]}...")
        
        # Extrai dados
        phone = data.get("phone")
        text_obj = data.get("text", {})
        message_text = text_obj.get("message") if isinstance(text_obj, dict) else str(text_obj)
        from_me = data.get("fromMe", False)
        is_group = data.get("isGroup", False)
        
        logger.info(f"📞 Telefone: {phone}")
        logger.info(f"💬 Mensagem: {message_text}")
        logger.info(f"👤 De mim: {from_me}")
        logger.info(f"👥 É grupo: {is_group}")
        
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
            return {"status": "ignored", "reason": "is_group"}
        
        # Processa com IA
        logger.info("🤖 Processando com IA...")
        
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Você é Ângela, atendente da SUNLUX ENERGIA. Seja educada, breve e profissional."
                },
                {
                    "role": "user",
                    "content": message_text
                }
            ]
        )
        
        response_text = completion.choices[0].message.content
        logger.info(f"💡 Resposta gerada: {response_text[:100]}...")
        
        # Envia resposta
        success = send_whatsapp_message(phone, response_text)
        
        if success:
            logger.info("✅ ATENDIMENTO CONCLUÍDO COM SUCESSO")
            return {"status": "ok", "processed": True}
        else:
            logger.error("❌ FALHA NO ENVIO DA RESPOSTA")
            return {"status": "error", "detail": "send_failed"}
    
    except Exception as e:
        logger.error(f"❌ ERRO NO WEBHOOK: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "detail": str(e)}
    
    finally:
        logger.info("="*50)

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("🎬 FastAPI iniciado - Aguardando webhooks...")
