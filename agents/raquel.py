from services.zapi import send_message

class RaquelAgent:

    def notify(self, phone, message):
        response = (
            "Olá! 😊\n\n"
            "Sou a Raquel, do setor comercial da SUNLUX Energia.\n"
            "Vou entender sua necessidade e te ajudar com a melhor solução fotovoltaica."
        )
        send_message(phone, response)
