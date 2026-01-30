import os
import json
import requests
from fastapi import FastAPI, Request
from datetime import datetime
import psycopg2

# ===============================
# CONFIGURAÇÕES
# ===============================

OPENAI_API_KEY = os.getenv("OPEN_IA")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_INSTANCE = os.getenv("ZAPI_INSTANCE_ID")
CLICKUP_TOKEN = os.getenv("CLICKUP_TOKEN")
CLICKUP_LIST_ATENDIMENTO = os.getenv("CLICKUP_LIST_ATENDIMENTO")
CLICKUP_LIST_FUNIL = os.getenv("CLICKUP_LIST_FUNIL")
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

# ===============================
# BANCO DE DADOS (MEMÓRIA)
# ===============================

def get_db():
    return psycopg2.connect(DATABASE_URL)

def salvar_historico(telefone, mensagem, agente):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS historico (
            id SERIAL PRIMARY KEY,
            telefone TEXT,
            agente TEXT,
            mensagem TEXT,
            data TIMESTAMP
        )
    """)
    cur.execute(
        "INSERT INTO historico (telefone, agente, mensagem, data) VALUES (%s,%s,%s,%s)",
        (telefone, agente, mensagem, datetime.now())
    )
    conn.commit()
    cur.close()
    conn.close()

# ===============================
# OPENAI
# ===============================

def perguntar_openai(system_prompt, user_message):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    }
    r = requests.post(url, headers=headers, json=body)
    return r.json()["choices"][0]["message"]["content"]

# ===============================
# AGENTE ÂNGELA (ORQUESTRADORA)
# ===============================

ANGELA_PROMPT = """
Você é Ângela, 28 anos, secretária executiva da SUNLUX Energia.
Você é educada, humana, clara e profissional.
Nunca diga que é robô ou inteligência artificial.

Função:
- Recepcionar clientes
- Entender o que a pessoa precisa
- Decidir se é atendimento técnico ou vendas
- Encaminhar internamente

Se o cliente falar de:
- orçamento, preço, proposta, energia solar → vendas
- problema, erro, inversor, fatura → suporte
"""

# ===============================
# AGENTE RAQUEL (VENDAS)
# ===============================

RAQUEL_PROMPT = """
Você é Raquel, consultora comercial da SUNLUX Energia.
Você fala como uma vendedora humana experiente.

Função:
- Prospecção ativa e receptiva
- Entender consumo, local, objetivo
- Conduzir para orçamento
- Agendar visita ou coleta de dados
Nunca diga que é robô.
"""

# ===============================
# CLICKUP
# ===============================

def criar_tarefa_clickup(lista_id, titulo, descricao):
    url = f"https://api.clickup.com/api/v2/list/{lista_id}/task"
    headers = {
        "Authorization": CLICKUP_TOKEN,
        "Content-Type": "application/json"
    }
    body = {
        "name": titulo,
        "description": descricao
    }
    requests.post(url, headers=headers, json=body)

# ===============================
# WHATSAPP (Z-API)
# ===============================

def enviar_whatsapp(telefone, mensagem):
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"
    body = {
        "phone": telefone,
        "message": mensagem
    }
    requests.post(url, json=body)

# ===============================
# WEBHOOK PRINCIPAL
# ===============================

@app.post("/webhook")
async def receber_mensagem(request: Request):
    data = await request.json()
    telefone = data.get("phone")
    mensagem = data.get("message")

    resposta_angela = perguntar_openai(ANGELA_PROMPT, mensagem)
    salvar_historico(telefone, mensagem, "Angela")

    if "venda" in resposta_angela.lower() or "orçamento" in resposta_angela.lower():
        resposta_raquel = perguntar_openai(RAQUEL_PROMPT, mensagem)
        salvar_historico(telefone, resposta_raquel, "Raquel")

        criar_tarefa_clickup(
            CLICKUP_LIST_FUNIL,
            f"Lead WhatsApp {telefone}",
            mensagem
        )

        enviar_whatsapp(telefone, resposta_raquel)
        return {"status": "encaminhado para vendas"}

    else:
        criar_tarefa_clickup(
            CLICKUP_LIST_ATENDIMENTO,
            f"Atendimento WhatsApp {telefone}",
            mensagem
        )

        enviar_whatsapp(telefone, resposta_angela)
        return {"status": "atendimento realizado"}

# ===============================
# HEALTHCHECK
# ===============================

@app.get("/")
def status():
    return {"status": "Agente Ângela online"}
