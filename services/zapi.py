import os
import requests

INSTANCE_ID = os.getenv("ZAPI_INSTANCE")
TOKEN = os.getenv("ZAPI_TOKEN")
CLIENT_TOKEN = os.getenv("CLIENTE_TOKEN")

def send_message(phone, text):
    url = f"https://api.z-api.io/instances/{INSTANCE_ID}/token/{TOKEN}/send-text"
    payload = {
        "phone": phone,
        "message": text
    }
    headers = {"Client-Token": CLIENT_TOKEN}
    requests.post(url, json=payload, headers=headers)
