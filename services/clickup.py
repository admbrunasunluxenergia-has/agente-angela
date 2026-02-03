import os
import requests

CLICKUP_TOKEN = os.getenv("CLICKUP_TOKEN")
LIST_ID = os.getenv("CLICKUP_LIST_ATENDIMENTO")

def create_task(title, description):
    url = f"https://api.clickup.com/api/v2/list/{LIST_ID}/task"
    headers = {
        "Authorization": CLICKUP_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "name": title,
        "description": description
    }
    requests.post(url, json=payload, headers=headers)
