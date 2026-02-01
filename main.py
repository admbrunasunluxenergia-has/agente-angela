import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from openai import OpenAI

# ===============================
# CONFIGURAÇÕES
# ===============================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Agente Ângela")

# ===============================
# STATUS (healthcheck)
# ===============================

@app.get("/")
def status():
    return {"status": "Agente Ângela online"}

# ===============================
# WEBHOOK PRINCIPAL
# ===============================

@app.post("/webhook")
async def webhook(request: Request):
    try:
        payload = await request.json()
        logging.info(f"Webhook recebido: {payload}")

        # 🔐 Tentando extrair texto da Z-API (sem quebrar)
        texto = (
            payload.get("message", {}).get("text")
            or payload.get("text")
            or payload.get("body")
            or "Olá"
        )

        remetente = (
            payload.get("from")
            or payload.get("sender")
            or "desconhecido"
        )

        # ===============================
        # CHAMADA DA IA
        # ===============================

        resposta_ia = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é Ângela, uma assistente virtual educada, clara, "
                        "objetiva e profissional. Responda mensagens de WhatsApp "
                        "de forma humana e acolhedora."
                    )
                },
                {
                    "role": "user",
                    "content": texto
                }
            ]
        )

        resposta = resposta_ia.choices[0].message.content

        logging.info(f"Resposta IA: {resposta}")

        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "from": remetente,
                "message_received": texto,
                "response": resposta
            }
        )

    except Exception as e:
        logging.error(f"Erro no webhook: {str(e)}")
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
                "error": str(e)
            }
        )
