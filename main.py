import json
from guard import guard_query
from config import OPENAI_API_KEY
from openai import OpenAI
import football_api
from datetime import datetime

client = OpenAI(api_key=OPENAI_API_KEY)

def extract_intent(user_input: str) -> dict:
    current_date = datetime.now().strftime("%Y-%m-%d")
    schema_description = f"""
    You must return a JSON object with these fields:
    - intent: one of [\"get_player_stats\", \"get_team_standing\", \"get_match_result\", \"get_match_events\", \"get_team_fixtures\"]
    - player: string (official name of player as listed in major football databases, or null if not relevant)
    - team1: string (official name of first team mentioned as listed in major football databases, or null if not relevant)
    - team2: string (official name of a possible second team mentioned as listed in major football databases, or null if not relevant)
    - season: string (e.g. \"2022/2023\", \"2024\"), or null if not given
    - stat: string (e.g. \"golos\", \"assistências\", \"cartões\"), or null if not relevant)
    - match_date: string (YYYY-MM-DD) or null
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
        "match_date": None,
        "competition": None,
        "fixture_type": None,
        "fixture_period": None,
    }
    return {**defaults, **intent}


def handle_intent(intent: dict):
    """Map parsed intent to Football API"""
    
    if intent.get("intent") == "get_team_standing":
        team_name = intent.get("team1")
        season = intent.get("season")
        competition = intent.get("competition")

        if not team_name or not season:
            return "Não consegui identificar a equipa ou a época."

        # Search team
        team_res = football_api.search_team(team_name)
        if not team_res.get("response"):
            return f"Não encontrei a equipa {team_name}."

        team = team_res["response"][0]["team"]
        team_id = team["id"]
        country = team.get("country", "").lower()

        # Determine if user wants a European competition
        league_id = None
        league_name = None
        if competition:
            for key, league in football_api.LEAGUES.items():
                if competition.lower() == league["name"].lower():
                    league_id = league["id"]
                    league_name = league["name"]
                    break

        # If no league found from competition, default to national league
        if not league_id:
            league_id = football_api.LEAGUES.get(country, {}).get("id")
            league_name = football_api.LEAGUES.get(country, {}).get("name")

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
            return f"Não encontrei a posição do {team_name} em {season} na {league_name or 'liga'}."
        
        return f"O {team_name} terminou em {position}º lugar na {league_name or 'liga'} na época {season}."


    elif intent.get("intent") == "get_match_result":
        team1 = intent.get("team1")
        team2 = intent.get("team2")
        season = intent.get("season")
        competition = intent.get("competition")

        if not team1 or not team2 or not season:
            return "Não consegui identificar as equipas ou a época."

        # Search teams to get IDs
        t1 = football_api.search_team(team1)
        t2 = football_api.search_team(team2)
        if not t1.get("response") or not t2.get("response"):
            return "Não encontrei uma das equipas."

        id1 = t1["response"][0]["team"]["id"]
        id2 = t2["response"][0]["team"]["id"]

        # Map competition name to league id if specified
        league_id = None
        comp_label = ""
        if competition:
            for key, league in football_api.LEAGUES.items():
                if competition.lower() == league["name"].lower():
                    league_id = league["id"]
                    comp_label = league["name"]
                    break

        # If no competition specified or not found, league_id remains None and will be omitted from API call
        match_res = football_api.get_match_result(id1, id2, season.split("/")[0], league_id)
        if not match_res.get("response"):
            if competition:
                return f"Não encontrei resultados entre {team1} e {team2} em {season} para {competition}."
            else:
                return f"Não encontrei resultados entre {team1} e {team2} em {season}."

        match = match_res["response"][0]
        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]
        g1, g2 = match["goals"]["home"], match["goals"]["away"]
        date = match["fixture"]["date"][:10]

        if comp_label:
            return f"{date}: {home} {g1} - {g2} {away} ({comp_label})"
        else:
            return f"{date}: {home} {g1} - {g2} {away}"


    if intent.get("intent") == "get_team_fixtures":
        team_name = intent.get("team1")
        season = intent.get("season")
        fixture_period = intent.get("fixture_period")
        fixture_type = intent.get("fixture_type")  # "hardest" or "easiest"

        if not team_name or not season:
            return "Não consegui identificar a equipa ou a época."

        # Search team
        team_res = football_api.search_team(team_name)
        if not team_res.get("response"):
            return f"Não encontrei a equipa {team_name}."

        team = team_res["response"][0]["team"]
        team_id = team["id"]

        from_date, to_date = None, None
        if fixture_period and fixture_period.get("start") and fixture_period.get("end"):
            from_date = fixture_period["start"][:10]
            to_date = fixture_period["end"][:10]

        # Get fixtures in period
        fixtures_res = football_api.get_team_fixtures(team_id, season.split("/")[0], from_date=from_date, to_date=to_date)
        fixtures = fixtures_res.get("response", [])
        if not fixtures:
            return f"Não encontrei jogos para o {team_name} em {season}."


        # Annotate fixtures with win probability and filter out None values
        fixtures_with_prob = []
        for f in fixtures:
            prob = compute_difficulty(f, team_name)
            if prob is not None:
                f["win_probability"] = prob
                fixtures_with_prob.append(f)

        if not fixtures_with_prob:
            return f"Não há jogos com probabilidade prevista para o {team_name} em {season}."

        # Sort by difficulty (lower win probability = harder)
        reverse_sort = fixture_type == "easiest"
        fixtures_with_prob.sort(key=lambda x: x["win_probability"], reverse=reverse_sort)

        # Return the top fixture
        match = fixtures_with_prob[0]
        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]
        date = match["fixture"]["date"][:10]
        win_prob = match.get("win_probability", None)
        win_prob_pct = f"{win_prob*100:.0f}%" if win_prob is not None else "N/A"

        return f"{'Jogo mais difícil' if fixture_type=='hardest' else 'Jogo mais fácil'}: {date}: {home} vs {away} (probabilidade de vitória: {win_prob_pct})"
    
    return "Ainda não sei responder a esse tipo de pergunta."


def compute_difficulty(fixture, team_name):
    fixture_id = fixture["fixture"]["id"]
    pred_res = football_api.get_fixture_predictions(fixture_id)
    preds = pred_res.get("response", [])
    if not preds:
        return None  # No predictions, return None

    # Take first prediction object
    prediction = preds[0].get("predictions", {})
    percent = prediction.get("percent", {})
    home_team = fixture["teams"]["home"]["name"]
    away_team = fixture["teams"]["away"]["name"]
    team_prob_str = None
    if team_name.lower() == home_team.lower():
        team_prob_str = percent.get("home")
    elif team_name.lower() == away_team.lower():
        team_prob_str = percent.get("away")

    if not team_prob_str or not team_prob_str.endswith("%"):
        return None  # No probability available

    try:
        team_prob = float(team_prob_str.strip('%')) / 100.0
    except Exception:
        return None

    return team_prob
    

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
