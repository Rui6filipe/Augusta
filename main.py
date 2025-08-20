import json
from guard import guard_query
from config import OPENAI_API_KEY
from openai import OpenAI
from datetime import datetime
from intent_handlers import (
    handle_team_standing_intent,
    handle_match_result_intent,
    handle_team_fixtures_intent,
    handle_match_events_intent,
    handle_player_stats_intent
)

client = OpenAI(api_key=OPENAI_API_KEY)

def extract_intent(user_input: str) -> dict:
    current_date = datetime.now().strftime("%Y-%m-%d")
    schema_description = f"""
    You must return a JSON object with these fields:
    - intent: one of [\"get_team_standing\", \"get_match_result\", \"get_match_events\", \"get_team_fixtures\", \"get_player_stats\"]
    - player: string (official name of player as listed in major football databases, or null if not relevant)
    - team1: string (official name of first team mentioned as listed in major football databases, or null if not relevant)
    - team2: string (official name of a possible second team mentioned as listed in major football databases, or null if not relevant)
    - season: string (e.g. \"2022/2023\", \"2024\"), or null if not given
    - event: string or list of strings, game event(s), one or more of [\"goal\", \"card\", \"subst\", \"var\", \"incident\"], or null if not relevant
    - stat: string or list of strings, player stat(s), one or more of [\"goals.total\", \"goals.assists\", \"games.appearences\", \"games.minutes\", \"shots.on\", \"passes.key\", \"passes.accuracy\", \"dribbles.success\", \"cards.yellow\", \"cards.red\"], or null if not relevant
    - competition: string (e.g. \"Primeira Liga\", \"Premier League\", \"La Liga\", \"Bundesliga\", \"Serie A\", \"Ligue 1\", \"Eredivisie\", \"UEFA Champions League\", \"UEFA Europa League\", \"UEFA Europa Conference League\"), or null if not specified by the user
    - fixture_type: string (\"hardest\" for hardest games, \"easiest\" for easiest games), or null if not relevant
    - fixture_period: an object with two fields, \"start\" and \"end\", both ISO datetime strings (e.g. \"2025-08-20T00:00:00\"), or null if not relevant. Take into account the current day is {current_date}.
    
    Note: The current football season is 2025/2026. If the user refers to relative seasons (e.g., \"época passada\", \"last season\", \"época atual\", \"this season\"), resolve them to the correct season string (e.g., \"época passada\" = \"2024/2025\", \"época atual\" = \"2025/2026\").
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
        "team1": None,
        "team2": None,
        "season": None,
        "stat": None,
        "competition": None,
        "fixture_type": None,
        "fixture_period": None,
    }
    return {**defaults, **intent}


def handle_intent(intent: dict):
    """Map parsed intent to Football API by delegating to specific handler functions."""
    intent_type = intent.get("intent")
    if intent_type == "get_team_standing":
        return handle_team_standing_intent(intent)
    elif intent_type == "get_match_result":
        return handle_match_result_intent(intent)
    elif intent_type == "get_team_fixtures":
        return handle_team_fixtures_intent(intent)
    elif intent_type == "get_match_events":
        return handle_match_events_intent(intent)
    elif intent_type == "get_player_stats":
        return handle_player_stats_intent(intent)
    else:
        return "Ainda não sei responder a esse tipo de pergunta."
    

def main():
    print("🤖 Chatbot de Futebol iniciado! (escreva 'sair' para terminar)")

    while True:
        user_input = input("Eu: ")
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
