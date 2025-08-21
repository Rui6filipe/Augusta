import json
import os
from dotenv import load_dotenv
from guard import guard_query
from openai import OpenAI
from datetime import datetime
from intent_handlers import (
    handle_team_standing_intent,
    handle_match_result_intent,
    handle_team_fixtures_intent,
    handle_match_events_intent,
    handle_player_stats_intent
)

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def extract_intent(user_input: str) -> dict:
    """
    Uses an LLM to extract one or more structured football intents from the user's input string.
    Returns a dictionary (single intent) or a list of dictionaries (multiple intents), each with intent type and relevant fields for downstream handling.
    """
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_season = f"{now.year}/{now.year+1}" if now.month >= 8 else f"{now.year-1}/{now.year}"
    schema_description = f"""
    You must return a JSON object with these fields for each intent:
    - intent: one of [\"get_team_standing\", \"get_match_result\", \"get_match_events\", \"get_team_fixtures\", \"get_player_stats\"]
    - player: string (official name of player as listed in major football databases, normalized to contain only ASCII alphanumeric characters and spaces, no accents or special characters; or null if not relevant)
    - team1: string (official name of first team mentioned as listed in major football databases, or null if not relevant)
    - team2: string (official name of a possible second team mentioned as listed in major football databases, or null if not relevant)
    - season: string (e.g. "2022/2023", "2024"), or null if not given. Resolve relative season references (e.g., "época passada", "last season", "época atual", "this season") to the correct season string based on the current football season (which is {current_season}).
    - event: string or list of strings, game event(s), one or more of [\"goal\", \"card\", \"subst\", \"var\", \"incident\"], or null if not relevant
    - stat: string or list of strings, player stat(s), one or more of [\"goals.total\", \"goals.assists\", \"games.appearences\", \"games.minutes\", \"shots.on\", \"passes.key\", \"passes.accuracy\", \"dribbles.success\", \"cards.yellow\", \"cards.red\"], or null if not relevant
    - competition: string (e.g. \"Primeira Liga\", \"Premier League\", \"La Liga\", \"Bundesliga\", \"Serie A\", \"Ligue 1\", \"Eredivisie\", \"UEFA Champions League\", \"UEFA Europa League\", \"UEFA Europa Conference League\"), or null if not specified by the user
    - fixture_type: string (\"hardest\" for hardest games, \"easiest\" for easiest games), or null if not relevant
    - fixture_period: an object with two fields, \"start\" and \"end\", both ISO datetime strings (e.g. \"2025-08-20T00:00:00\"), or null if not relevant. Take into account the current day is {current_date}.

    If the user asks about multiple events (e.g., goals and cards) for the same match, or multiple stats for the same player/season, return a single intent with a list for the relevant field (event or stat).
    Only return multiple intent objects if the user is asking about truly different things (e.g., different matches, teams, players, seasons, competitions, fixture types, or fixture periods).
    Otherwise, return a single intent object.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract structured football intents. Always return JSON or a JSON array only. "
                    "If the user asks about different matches, teams, players, seasons, competitions, fixture types, or fixture periods, you MUST return a separate intent object for each unique combination. "
                    "Never merge requests for different seasons, competitions, fixture types, or fixture periods into a single intent. "
                    "Be strict: if any of these fields differ, split into multiple intents."
                )
            },
            {"role": "user", "content": f"{schema_description}\n\nUser query: {user_input}"}
        ],
        temperature=0
    )

    # Parse JSON safely
    try:
        result = json.loads(response.choices[0].message.content)
    except Exception:
        result = {}

    # Fill defaults for each intent
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
    # Handle case where LLM returns a dict with an 'intents' key (list of intents)
    if isinstance(result, dict) and "intents" in result and isinstance(result["intents"], list):
        return [{**defaults, **intent} for intent in result["intents"]]
    elif isinstance(result, list):
        return [{**defaults, **intent} for intent in result]
    else:
        return {**defaults, **result}


def handle_intent(intent: dict):
    """
    Maps the parsed intent dictionary (or list of dictionaries) to the appropriate handler function(s).
    Returns the result(s) from the handler(s), which may be a dictionary, list of dictionaries, or error message(s).
    """
    handlers = {
        "get_team_standing": handle_team_standing_intent,
        "get_match_result": handle_match_result_intent,
        "get_team_fixtures": handle_team_fixtures_intent,
        "get_match_events": handle_match_events_intent,
        "get_player_stats": handle_player_stats_intent,
    }
    def handle_one(i):
        return handlers.get(i.get("intent"), lambda x: "Ainda não sei responder a esse tipo de pergunta.")(i)
    if isinstance(intent, list):
        return [handle_one(i) for i in intent]
    else:
        return handle_one(intent)
    

def generate_response(user_input, data):
    """
    Uses an LLM to generate a natural language answer in Portuguese based on the user input and structured data.
    Returns a plain text string suitable for terminal output.
    """
    import json
    prompt = f"Pergunta do utilizador: {user_input}\nAqui estão todos os dados necessários para a resposta (em JSON): {json.dumps(data, ensure_ascii=False)}\nResponde de forma clara e natural em português, somando e agrupando os dados se fizer sentido, e respondendo à pergunta do utilizador. Nunca uses Markdown nem asteriscos."
    # Call LLM to generate the final answer
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Responde sempre em português, de forma clara e natural, e nunca uses Markdown nem asteriscos."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    return response.choices[0].message.content.strip()


def main():
    """
    Main loop for the football chatbot. Handles user input, intent extraction, data retrieval, and response generation.
    Runs until the user types an exit command.
    """
    print("\n🤖 Chatbot de Futebol iniciado! (escreva 'sair' para terminar)\n")

    while True:
        user_input = input("Eu: ")
        print()  # Blank line after user input
        if user_input.lower() in ["sair", "exit", "quit"]:
            print("Chatbot: Até logo! ⚽\n")
            break

        # Guard
        guard_result = guard_query(user_input)
        if guard_result:
            print("Chatbot:", guard_result)
            print()
            continue

        # Intent extraction
        intent = extract_intent(user_input)
        print("DEBUG INTENT:", intent)
        print()

        # Handle intent and generate LLM response
        data = handle_intent(intent)
        print("DEBUG DATA:", data)
        print()
        answer = generate_response(user_input, data)
        print("Chatbot:", answer)
        print()

if __name__ == "__main__":
    main()
