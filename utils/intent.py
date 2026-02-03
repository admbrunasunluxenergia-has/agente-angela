def detect_intent(text):
    if not isinstance(text, str):
        return "atendimento"

    text = text.lower()

    palavras_orcamento = [
        "orçamento",
        "orcamento",
        "preço",
        "valor",
        "quanto custa",
        "proposta"
    ]

    for palavra in palavras_orcamento:
        if palavra in text:
            return "orcamento"

    return "atendimento"
