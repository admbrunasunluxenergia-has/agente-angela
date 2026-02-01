from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

# logger
logging.basicConfig(level=logging.INFO)

app = FastAPI()

@app.get("/")
def status():
    return {"status": "Agente Ângela online"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        payload = await request.json()
        logging.info(f"Webhook recebido: {payload}")

        mensagem = payload.get("message") or payload.get("mensagem")
        remetente = payload.get("from") or payload.get("de")

        if not mensagem:
            return JSONResponse(
                status_code=200,
                content={"ok": True, "info": "Mensagem vazia recebida"}
            )

        resposta = f"Olá! Recebi sua mensagem: {mensagem}"

        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "from": remetente,
                "resposta": resposta
            }
        )

    except Exception as e:
        logging.error(f"Erro no webhook: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "erro": str(e)}
        )
