import os
import logging
import json
import httpx
from datetime import datetime
import pytz
from fastapi import FastAPI, Request, BackgroundTasks, Response
from typing import Dict, Any, List
from openai import OpenAI

# --- LOGS ---
logging.basicConfig(
    level=logging.INFO,
    format='%(name )s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

app = FastAPI()

# --- CONFIGURAÇÕES ---
def get_env(key):
    val = os.getenv(key, "")
    return val.strip() if val else ""

ZAPI_INSTANCE = get_env("ZAPI_INSTANCE") or get_env("INSTÂNCIA ZAPI")
ZAPI_TOKEN = get_env("ZAPI_TOKEN")

# SEU TOKEN FIXO (Não precisa mais mudar)
CLIENT_TOKEN = "F38393c3b6dc744ef84b0de693e92609eS"

# URL da Z-API
API_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"

# --- CONFIGURAÇÃO OPENAI (CÉREBRO ) ---
OPENAI_API_KEY = "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"
client_openai = OpenAI(api_key=OPENAI_API_KEY)

# --- FUNÇÃO DE SAUDAÇÃO (BOM DIA/TARDE/NOITE) ---
def get_saudacao():
    try:
        fuso = pytz.timezone('America/Sao_Paulo')
        hora = datetime.now(fuso).hour
        if 5 <= hora < 12: return "Bom dia"
        elif 12 <= hora < 18: return "Boa tarde"
        else: return "Boa noite"
    except:
        return "Olá"

# --- PERSONALIDADE DA ÂNGELA ---
def get_system_prompt():
    saudacao = get_saudacao()
    return f"""
    Você é a Ângela, assistente virtual da SUNLUX ENERGIA.
    
    INSTRUÇÕES DE COMPORTAMENTO:
    1. Sua primeira frase SEMPRE deve começar com: "{saudacao}! Eu sou a Ângela, da SUNLUX ENERGIA." (mas só na primeira mensagem da conversa).
    2. Pergunte educadamente: "Em que posso te ajudar hoje?"
    3. Se o cliente relatar um problema, dúvida técnica ou fizer um pedido, diga CLARAMENTE:
       "Vou registrar essas informações no nosso sistema e direcionar para a área competente. Logo que possível, retornaremos com a resposta."
    4. Seja breve, profissional, acolhedora e use emojis moderados (☀️, ✅, 📝).
    5. Você é inteligente: entenda o contexto da reclamação ou dúvida do cliente sobre energia solar.
    """

# Memória simples (apaga se reiniciar o server)
conversas: Dict[str, List[Dict]] = {}

# --- FUNÇÃO GPT (INTELIGÊNCIA) ---
def gerar_resposta_ia(telefone, mensagem_usuario):
    # Recupera histórico ou inicia novo
    prompt_atual = get_system_prompt()
    
    # Se não tem histórico, começa com o prompt do sistema
    if telefone not in conversas:
        conversas[telefone] = [{"role": "system", "content": prompt_atual}]
    
    historico = conversas[telefone]
    
    # Atualiza o prompt do sistema (para garantir saudação correta do horário)
    historico[0] = {"role": "system", "content": prompt_atual}
    
    # Adiciona msg do usuário
    historico.append({"role": "user", "content": mensagem_usuario})
    
    try:
        logger.info(f"🤖 Ângela pensando para {telefone}...")
        response = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=historico,
            max_tokens=350,
            temperature=0.7
        )
        
        resposta_ia = response.choices[0].message.content
        
        # Adiciona resposta da IA ao histórico
        historico.append({"role": "assistant", "content": resposta_ia})
        
        # Mantém apenas as últimas 10 mensagens
        if len(historico) > 11: 
            historico = [historico[0]] + historico[-10:]
            
        conversas[telefone] = historico
        return resposta_ia
        
    except Exception as e:
        logger.error(f"❌ ERRO OPENAI: {e}")
        return "Desculpe, a conexão oscilou um pouquinho. Pode repetir, por favor?"

# --- FUNÇÃO ENVIO WHATSAPP ---
async def enviar_resposta(telefone: str, texto: str):
    if not texto: return

    headers = {
        "Content-Type": "application/json",
        "Client-Token": CLIENT_TOKEN
    }
    
    payload = {"phone": telefone, "message": texto}

    try:
        async with httpx.AsyncClient( ) as client:
            logger.info(f"📤 ENVIANDO RESPOSTA para {telefone}...")
            response = await client.post(API_URL, json=payload, headers=headers, timeout=20.0)
            if response.status_code not in [200, 201]:
                logger.error(f"❌ ERRO Z-API ({response.status_code}): {response.text}")
            else:
                logger.info("✅ Mensagem enviada com sucesso!")
    except Exception as e:
        logger.error(f"❌ ERRO ENVIO: {e}")

# --- PROCESSAMENTO ---
async def processar_mensagem(payload: Dict[str, Any]):
    try:
        telefone = payload.get('phone')
        
        # Extração segura do texto
        texto_msg = ""
        if 'text' in payload and isinstance(payload['text'], dict):
            texto_msg = payload['text'].get('message', '')
        elif 'text' in payload:
            texto_msg = str(payload['text'])
            
        if not texto_msg: return

        is_group = payload.get('isGroup', False)
        from_me = payload.get('fromMe', False)

        # Ignora mensagens enviadas por mim ou grupos
        if from_me or is_group: return

        logger.info(f"📩 Recebido de {telefone}: {texto_msg}")
        
        # Gera resposta com IA
        resposta = gerar_resposta_ia(telefone, texto_msg)
        
        # Envia de volta
        await enviar_resposta(telefone, resposta)

    except Exception as e:
        logger.error(f"❌ ERRO LÓGICA: {e}")

# --- WEBHOOK ---
@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        # Ignora status de entrega (SENT, READ, etc)
        if body.get('status') in ['SENT', 'DELIVERED', 'READ']: 
            return Response(status_code=200)
            
        background_tasks.add_task(processar_mensagem, body)
        return Response(status_code=200)
    except Exception:
        return Response(status_code=200)

@app.get("/")
def health():
    return {"status": "online", "agent": "Angela - Sunlux", "version": "v8-ai-enabled"}
