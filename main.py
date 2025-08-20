import json
from guard import guard_query
from config import OPENAI_API_KEY
from openai import OpenAI
import football_api

client = OpenAI(api_key=OPENAI_API_KEY)

def extract_intent(user_input: str) -> dict:
    schema_description = """
    You must return a JSON object with these fields:
    - intent: one of ["get_player_stats", "get_team_standing", "get_match_result", "get_match_events"]
    - player: string (name of player, or null if not relevant)
    - team: string (name of team, or null if not relevant)
    - season: string (e.g. "2022/2023", "2024"), or null if not given
    - stat: string (e.g. "golos", "assistências", "cartões"), or null if not relevant
    - match_date: string (YYYY-MM-DD) or null
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},  # ensures proper JSON
        messages=[
            {"role": "system", "content": "Extract structured football intents. Always return JSON only."},
            {"role": "user", "content": f"{schema_description}\n\nUser query: {user_input}"}
        ],
        temperature=0
    )

    # Parse JSON safely
    try:
        intent = json.loads(response.choices[0].message.content)
    except Exception:
        intent = {}

    # Fill defaults if missing
    defaults = {
        "intent": "unknown",
        "player": None,
        "team": None,
        "season": None,
        "stat": None,
        "match_date": None,
    }
    return {**defaults, **intent}




def handle_intent(intent: dict):
    """Map parsed intent to Football API"""

    return "Ainda não sei responder a esse tipo de pergunta."


def main():
    print("🤖 Chatbot de Futebol iniciado! (escreva 'sair' para terminar)")

    while True:
        user_input = input("Você: ")
        if user_input.lower() in ["sair", "exit", "quit"]:
            print("Chatbot: Até logo! ⚽")
            break

        # Guard
        guard_result = guard_query(user_input)
        if guard_result:
            print("Chatbot:", guard_result)
            continue

        # Intent extraction
        intent = extract_intent(user_input)
        print("DEBUG INTENT:", intent)

        # Handle intent
        answer = handle_intent(intent)
        print("Chatbot:", answer)

if __name__ == "__main__":
    main()
