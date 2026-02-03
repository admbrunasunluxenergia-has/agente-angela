import os
import requests
from fastapi import FastAPI, Request
from openai import OpenAI

app = FastAPI()

# Variáveis
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ZAPI_INSTANCE = os.getenv("ZAPI_INSTANCE") or os.getenv("INSTÂNCIA_ZAPI") or "3E1F5556754D707D83290A427663C12F"
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")

client = OpenAI(api_key=OPENAI_API_KEY)

def send_whatsapp_message(phone: str, message: str):
    """Envia mensagem via Z-API"""
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"
    headers = {"Content-Type": "application/json", "Client-Token": ZAPI_TOKEN}
    payload = {"phone": phone, "message": message}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        print(f"✅ Mensagem enviada para {phone}")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar: {e}")
        return False

@app.get("/")
def root():
    return {"status": "online"}

@app.post("/webhook")
async def webhook(request: Request):
    """Recebe mensagem e responde"""
    data = await request.json()
    
    phone = data.get("phone")
    text_obj = data.get("text", {})
    message_text = text_obj.get("message") if isinstance(text_obj, dict) else str(text_obj)
    from_me = data.get("fromMe", False)
    is_group = data.get("isGroup", False)
    
    # Ignora grupos e mensagens próprias
    if not phone or not message_text or from_me or is_group:
        return {"status": "ignored"}
    
    # Processa com OpenAI
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é Ângela, atendente da SUNLUX ENERGIA. Seja breve e profissional."},
                {"role": "user", "content": message_text}
            ]
        )
        response_text = completion.choices[0].message.content
        
        # Envia resposta
        send_whatsapp_message(phone, response_text)
        
        return {"status": "ok"}
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        return {"status": "error", "detail": str(e)}
