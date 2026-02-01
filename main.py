from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

app = FastAPI()

# logger básico
logging.basicConfig(level=logging.INFO)


@app.get("/")
def status():
    return {"status": "Agente Ângela online"}


@app.post("/webhook")
async def webhook(request: Request):
    try:
        payload = await request.json()
        logging.info(f"Webhook recebido: {payload}")

        message = payload.get("message", {})
        text = message.get("text", "")
        sender = message.get("from", "desconhecido")

        if not text:
            return JSONResponse(
                status_code=200,
                content={"ok": True, "info": "Mensagem sem texto"}
            )

        resposta = f"Olá! Recebi sua mensagem: {text}"

        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "from": sender,
                "response": resposta
            }
        )

    except Exception as e:
        logging.error(f"Erro no webhook: {e}")
        return JSONResponse(
            status_code=200,
            content={"ok": False, "error": "Erro tratado"}
        )
