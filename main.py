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
    - player: string (official name of player as listed in major football databases, or null if not relevant)
    - team: string (official name of team as listed in major football databases, or null if not relevant)
    - season: string (e.g. "2022/2023", "2024"), or null if not given
    - stat: string (e.g. "golos", "assistências", "cartões"), or null if not relevant
    - match_date: string (YYYY-MM-DD) or null

    Note: The current football season is 2025/2026. If the user refers to relative seasons (e.g., "época passada", "last season", "época atual", "this season"), resolve them to the correct season string (e.g., "época passada" = "2024/2025", "época atual" = "2025/2026").
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
    
    if intent.get("intent") == "get_team_standing":
        team_name = intent.get("team")
        season = intent.get("season")

        if not team_name or not season:
            return "Não consegui identificar a equipa ou a época."

        # Search team
        team_res = football_api.search_team(team_name)
        if not team_res.get("response"):
            return f"Não encontrei a equipa {team_name}."

        team = team_res["response"][0]["team"]
        team_id = team["id"]
        country = team.get("country", "").lower()

        # Pick league
        league_id = football_api.LEAGUES.get(country, {}).get("id")
        if not league_id:
            return f"Ainda não tenho mapeamento de ligas para {country}."

        # Get standings
        standings_res = football_api.get_team_standings(league_id, season.split("/")[0])
        if not standings_res.get("response"):
            return f"Não encontrei classificações para {team_name} em {season}."

        standings = standings_res["response"][0]["league"]["standings"][0]

        position = None
        for row in standings:
            if row["team"]["id"] == team_id:
                position = row["rank"]
                break

        if position is None:
            return f"Não encontrei a posição do {team_name} em {season}."
        
        return f"O {team_name} terminou em {position}º lugar na época {season}."

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
