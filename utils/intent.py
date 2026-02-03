def detect_intent(text):
    text = text.lower()
    if any(word in text for word in ["orçamento", "preço", "valor", "quanto custa"]):
        return "orcamento"
    return "atendimento"
