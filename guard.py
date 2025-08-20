SPORTS_COMING_SOON = ["basket", "basquetebol", "rugby", "fórmula 1", "formula 1"]
SPORTS_NOT_ALLOWED = ["tenis", "golf", "cricket", "hóquei"]

INJECTION_KEYWORDS = ["ignore previous", "system prompt", "api key", "hack"]

def check_sport(query: str) -> str | None:
    q = query.lower()
    if any(s in q for s in SPORTS_COMING_SOON):
        return "Esse desporto estará disponível em breve."
    if any(s in q for s in SPORTS_NOT_ALLOWED):
        return "Esse desporto não está disponível nesta aplicação."
    return None

def check_injection(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in INJECTION_KEYWORDS)

def guard_query(user_input: str) -> str | None:
    sport_msg = check_sport(user_input)
    if sport_msg:
        return sport_msg
    if check_injection(user_input):
        return "A sua pergunta não é válida para este chatbot."
    return None