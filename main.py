from fastapi import FastAPI, Request
from agents.angela import AngelaAgent

app = FastAPI()
angela = AngelaAgent()

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    payload = await request.json()
    angela.process_message(payload)
    return {"status": "ok"}
