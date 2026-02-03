import os
import requests
from fastapi import FastAPI, Request
from openai import OpenAI
import logging
from datetime import datetime
import json

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(title="Agente Ângela - SUNLUX ENERGIA")

# Credenciais Z-API
ZAPI_INSTANCE = "3E1F5556754D707D83290A427663C12F"
ZAPI_TOKEN = "3679EA28835DA95A8E14D35D"

# Credenciais ClickUp
CLICKUP_API_KEY = "pk_266489071_UK216278X3QXMH0YCEKHPGHZ2601WK3R"
CLICKUP_LIST_ID = "901316247221"

# Cliente OpenAI (usa variável de ambiente OPENAI_API_KEY)
client = OpenAI()

# Mensagem padrão de fallback
FALLBACK_MSG = "Olá! Sou a Ângela da SUNLUX ENERGIA. Recebemos sua mensagem e em breve um consultor entrará em contato. Como posso ajudar?"

logger.info("="*70)
logger.info("🚀 AGENTE ÂNGELA - SUNLUX ENERGIA - INICIADO")
logger.info("="*70)


def extract_message_text(data: dict) -> str:
    """Extrai texto da mensagem de QUALQUER formato Z-API"""
    
    # Lista de todos os caminhos possíveis
    paths_to_try = [
        # Formato padrão
        ("text", "message"),
        # Formato alternativo 1
        ("message", "text"),
        ("message", "conversation"),
        ("message", "extendedTextMessage", "text"),
        # Formato alternativo 2
        ("body",),
        ("content",),
        # Formato direto
        ("text",),
        ("message",),
        # Formato de notificação
        ("data", "message"),
        ("data", "text"),
        # Formato de evento
        ("event", "message"),
        ("event", "text"),
    ]
    
    # Tentar cada caminho
    for path in paths_to_try:
        try:
            value = data
            for key in path:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    break
            
            if value and isinstance(value, str) and value.strip():
                logger.info(f"✅ Texto extraído via path: {' -> '.join(path)}")
                return value.strip()
        except:
            continue
    
    # Se não encontrou, tentar buscar recursivamente
    def find_text_recursive(obj, depth=0):
        if depth > 5:  # Limite de profundidade
            return None
        
        if isinstance(obj, dict):
            # Procurar por chaves que contenham "message" ou "text"
            for key in obj:
                if key.lower() in ["message", "text", "body", "content", "conversation"]:
                    value = obj[key]
                    if isinstance(value, str) and value.strip():
                        return value.strip()
                    elif isinstance(value, dict):
                        result = find_text_recursive(value, depth + 1)
                        if result:
                            return result
            
            # Se não encontrou, buscar recursivamente em todos os valores
            for value in obj.values():
                if isinstance(value, dict):
                    result = find_text_recursive(value, depth + 1)
                    if result:
                        return result
        
        return None
    
    result = find_text_recursive(data)
    if result:
        logger.info(f"✅ Texto extraído via busca recursiva")
        return result
    
    logger.warning("⚠️ Não foi possível extrair texto da mensagem")
    return None


def send_whatsapp(phone: str, message: str) -> bool:
    """Envia mensagem via Z-API"""
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"
    
    payload = {
        "phone": phone,
        "message": message
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        logger.info(f"📤 Enviando mensagem para {phone}")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        logger.info(f"📡 Z-API Response: {response.status_code}")
        logger.info(f"📡 Z-API Body: {response.text[:200]}")
        
        if response.status_code == 200:
            logger.info("✅ Mensagem enviada com sucesso")
            return True
        else:
            logger.error(f"❌ Erro ao enviar: {response.status_code} - {response.text[:200]}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Exceção ao enviar mensagem: {str(e)}")
        return False


def create_clickup_task(name: str, description: str, phone: str) -> bool:
    """Cria tarefa no ClickUp"""
    url = f"https://api.clickup.com/api/v2/list/{CLICKUP_LIST_ID}/task"
    
    headers = {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": name,
        "description": description,
        "tags": ["whatsapp", "angela"],
        "priority": 3
    }
    
    try:
        logger.info(f"📝 Criando tarefa no ClickUp: {name}")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            task_id = response.json().get("id")
            logger.info(f"✅ Tarefa criada: {task_id}")
            return True
        else:
            logger.error(f"❌ Erro ao criar tarefa: {response.status_code} - {response.text[:200]}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Exceção ao criar tarefa: {str(e)}")
        return False


def get_ai_response(user_message: str) -> str:
    """Obtém resposta da IA"""
    try:
        logger.info("🤖 Consultando OpenAI...")
        
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": """Você é Ângela, atendente virtual da SUNLUX ENERGIA.

Sua função:
- Atender clientes com educação e profissionalismo
- Responder perguntas sobre energia solar
- Coletar informações básicas (nome, interesse)
- Ser breve e objetiva
- Usar emojis com moderação

Empresa: SUNLUX ENERGIA - Soluções em Energia Solar"""
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        response = completion.choices[0].message.content
        logger.info(f"✅ Resposta da IA obtida: {response[:50]}...")
        return response
        
    except Exception as e:
        logger.error(f"❌ Erro na OpenAI: {str(e)}")
        return None


@app.get("/")
def root():
    """Health check"""
    return {
        "status": "online",
        "agent": "Angela",
        "company": "SUNLUX ENERGIA",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/webhook")
async def webhook(request: Request):
    """Recebe webhooks do Z-API"""
    
    logger.info("="*70)
    logger.info("🔔 WEBHOOK RECEBIDO")
    
    try:
        # Receber dados
        data = await request.json()
        
        # Log do payload completo (formatado)
        logger.info("📦 PAYLOAD COMPLETO:")
        logger.info(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Extrair informações básicas
        phone = data.get("phone") or data.get("from") or data.get("remoteJid")
        from_me = data.get("fromMe", False)
        is_group = data.get("isGroup", False)
        
        # Extrair texto da mensagem (ultra-robusto)
        message_text = extract_message_text(data)
        
        logger.info(f"📞 Telefone: {phone}")
        logger.info(f"💬 Mensagem: {message_text}")
        logger.info(f"👤 De mim: {from_me} | Grupo: {is_group}")
        
        # Validações
        if from_me:
            logger.info("⚠️ Ignorado: mensagem própria")
            return {"status": "ignored", "reason": "from_me"}
        
        if is_group:
            logger.info("⚠️ Ignorado: mensagem de grupo")
            return {"status": "ignored", "reason": "group"}
        
        if not phone:
            logger.warning("⚠️ Ignorado: sem telefone")
            return {"status": "ignored", "reason": "no_phone"}
        
        if not message_text:
            logger.warning("⚠️ Ignorado: sem texto")
            logger.warning("⚠️ PAYLOAD NÃO RECONHECIDO - Envie este log para análise")
            return {"status": "ignored", "reason": "no_text"}
        
        # Processar mensagem
        logger.info("🔄 Processando mensagem...")
        
        # Tentar obter resposta da IA
        ai_response = get_ai_response(message_text)
        
        # Se IA falhar, usar fallback
        if not ai_response:
            logger.warning("⚠️ IA falhou, usando fallback")
            ai_response = FALLBACK_MSG
        
        # Enviar resposta
        sent = send_whatsapp(phone, ai_response)
        
        if not sent:
            logger.error("❌ Falha ao enviar mensagem")
            return {"status": "error", "detail": "send_failed"}
        
        # Criar tarefa no ClickUp
        task_name = f"Atendimento WhatsApp - {phone}"
        task_description = f"""**Telefone:** {phone}
**Mensagem:** {message_text}
**Resposta:** {ai_response}
**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""
        
        create_clickup_task(task_name, task_description, phone)
        
        logger.info("✅ ATENDIMENTO CONCLUÍDO COM SUCESSO")
        logger.info("="*70)
        
        return {
            "status": "success",
            "phone": phone,
            "message_sent": True,
            "clickup_task_created": True
        }
        
    except Exception as e:
        logger.error(f"❌ ERRO GERAL: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "detail": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
