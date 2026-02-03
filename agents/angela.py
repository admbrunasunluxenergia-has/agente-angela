class AngelaAgent:

    def process_message(self, payload):
        phone = payload.get("phone")

        message_text = ""

        # Z-API envia texto dentro de message.text
        if isinstance(payload.get("message"), dict):
            message_text = payload["message"].get("text", "")
        else:
            message_text = ""

        intent = detect_intent(message_text)

        greeting = self._greeting()

        response = (
            f"{greeting} 😊\n\n"
            "Sou a Ângela, recepcionista virtual da SUNLUX Energia.\n\n"
            "Recebi sua mensagem e vou registrá-la em nosso sistema "
            "e encaminhar ao setor responsável.\n\n"
            "Em breve retornaremos."
        )

        send_message(phone, response)

        description = f"""
Telefone: {phone}
Mensagem: {message_text}
Intenção detectada: {intent}
"""

        create_task(
            title=f"Atendimento WhatsApp - {phone}",
            description=description
        )

        if intent == "orcamento":
            from agents.raquel import RaquelAgent
            RaquelAgent().notify(phone, message_text)
