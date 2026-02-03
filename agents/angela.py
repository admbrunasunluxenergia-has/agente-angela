from services.zapi import send_message
from services.clickup import create_task
from utils.intent import detect_intent
import datetime


class AngelaAgent:

    def process_message(self, payload: dict):
        """
        Processa qualquer evento recebido da Z-API
        de forma segura (texto, áudio, imagem, status etc.)
        """

        # Segurança absoluta
        if not isinstance(payload, dict):
            return

        phone = payload.get("phone") or payload.get("from")

        # Se não tiver telefone, não faz nada
        if not phone:
            return

        message_text = self._extract_text(payload)

        # Detecta intenção apenas se houver texto
        intent = detect_intent(message_text)

        greeting = self._greeting()

        response = (
            f"{greeting} 😊\n\n"
            "Sou a Ângela, recepcionista virtual da SUNLUX Energia.\n\n"
            "Recebi sua mensagem e vou registrá-la em nosso sistema "
            "e encaminhar ao setor responsável.\n\n"
            "Em breve retornaremos."
        )

        # Responde somente se houver mensagem do cliente
        send_message(phone, response)

        description = f"""
Telefone: {phone}
Mensagem: {message_text or '[Mensagem sem texto]'}
Intenção detectada: {intent}
Payload bruto:
{payload}
"""

        create_task(
            title=f"Atendimento WhatsApp - {phone}",
            description=description
        )

        if intent == "orcamento":
            from agents.raquel import RaquelAgent
            RaquelAgent().notify(phone, message_text)

    def _extract_text(self, payload: dict) -> str:
        """
        Extrai texto com segurança de QUALQUER formato da Z-API
        """

        message = payload.get("message")

        if isinstance(message, dict):
            # Texto simples
            if isinstance(message.get("text"), str):
                return message["text"]

            # Alguns payloads usam body
            if isinstance(message.get("body"), str):
                return message["body"]

        # Fallback
        return ""

    def _greeting(self):
        hour = datetime.datetime.now().hour
        if hour < 12:
            return "Bom dia"
        elif hour < 18:
            return "Boa tarde"
        return "Boa noite"
