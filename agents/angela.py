import datetime
from services.openai_service import interpret_message
from services.clickup import create_task
from services.zapi import send_message
from utils.intent import detect_intent

class AngelaAgent:

    def process_message(self, payload):
        phone = payload["phone"]
        message = payload.get("text", "")
        media = payload.get("media")

        intent = detect_intent(message)

        greeting = self._greeting()
        response = (
            f"{greeting} 😊\n\n"
            "Sou a Ângela, recepcionista virtual da SUNLUX Energia.\n\n"
            "Vou registrar sua solicitação no nosso sistema e encaminhar "
            "ao setor responsável. Em breve retornaremos."
        )

        send_message(phone, response)

        description = f"""
Cliente: {phone}
Mensagem: {message}
Intenção detectada: {intent}
"""

        create_task(
            title=f"Atendimento WhatsApp - {phone}",
            description=description
        )

        if intent == "orcamento":
            from agents.raquel import RaquelAgent
            RaquelAgent().notify(phone, message)

    def _greeting(self):
        hour = datetime.datetime.now().hour
        if hour < 12:
            return "Bom dia"
        elif hour < 18:
            return "Boa tarde"
        return "Boa noite"

