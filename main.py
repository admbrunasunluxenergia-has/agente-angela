import os
import logging
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# =========================
# CONFIGURAÇÕES
# =========================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_INSTANCE = os.getenv("ID_INSTÂNCIA_ZAPI")

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
ZAPI_SEND_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"

# =========================
# APP
# =========================

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# =========================
# ROTAS
# =========================

@app.get("/")
def status():
    return {"status": "Agente Ângela online"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        payload = await request.json()
        logging.info(f"Webhook recebido: {payload}")

        # Texto recebido
        message = payload.get("message", {})
        text = message.get("text", "").strip()
        phone = payload.get("phone")

        if not text or not phone:
            return JSONResponse(
                status_code=200,
                content={"ok": True, "info": "Mensagem ignorada"}
            )

        # =========================
        # OPENAI
        # =========================

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        openai_payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Você é Ângela, uma assistente educada, humana, clara e objetiva. "
                        "Responda mensagens do WhatsApp de forma natural."
                    )
                },
                {
                    "role": "user",
                    "content": text
                }
            ]
        }

        ai_response = requests.post(
            OPENAI_URL,
            headers=headers,
            json=openai_payload,
            timeout=30
        )

        ai_response.raise_for_status()
        ai_text = ai_response.json()["choices"][0]["message"]["content"]

        # =========================
        # ENVIAR RESPOSTA VIA Z-API
        # =========================

        zapi_payload = {
            "phone": phone,
            "message": ai_text
        }

        zapi_response = requests.post(
            ZAPI_SEND_URL,
            json=zapi_payload,
            timeout=30
        )

        zapi_response.raise_for_status()

        logging.info("Resposta enviada com sucesso")

        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "received": text,
                "response": ai_text
            }
        )

    except Exception as e:
        logging.error(f"Erro no webhook: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Erro interno"}
        )
