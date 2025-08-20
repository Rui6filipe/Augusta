import requests
from config import FOOTBALL_API_KEY, FOOTBALL_API_URL

LEAGUES = {
    "portugal": {"name": "Primeira Liga", "id": 94},
    "england": {"name": "Premier League", "id": 39},
    "spain": {"name": "La Liga", "id": 140},
    "germany": {"name": "Bundesliga", "id": 78},
    "italy": {"name": "Serie A", "id": 135},
    "france": {"name": "Ligue 1", "id": 61},
    "netherlands": {"name": "Eredivisie", "id": 88},
    # European competitions
    "ucl": {"name": "UEFA Champions League", "id": 2},
    "uel": {"name": "UEFA Europa League", "id": 3},
    "uecl": {"name": "UEFA Europa Conference League", "id": 848},
}

HEADERS = {"x-apisports-key": FOOTBALL_API_KEY}

def search_team(name: str):
    """Search for a team by name"""
    url = f"{FOOTBALL_API_URL}/teams"
    params = {"search": name}
    r = requests.get(url, headers=HEADERS, params=params)
    return r.json()

def get_team_standings(league_id: int, season: int):
    url = f"{FOOTBALL_API_URL}/standings"
    params = {"league": league_id, "season": season}
    r = requests.get(url, headers=HEADERS, params=params)
    return r.json()

def get_match_result(team1: str, team2: str, season: int, league_id: int):
    """Search for a specific match result"""
    url = f"{FOOTBALL_API_URL}/fixtures/headtohead"
    params = {"h2h": f"{team1}-{team2}", "season": season}
    if league_id is not None:
        params["league"] = league_id
    r = requests.get(url, headers=HEADERS, params=params)
    return r.json()

def get_team_fixtures(team_id: int, season: int, from_date: str = None, to_date: str = None):
    """Get fixtures for a team (next or last, or by date range)"""
    url = f"{FOOTBALL_API_URL}/fixtures"
    params = {"team": team_id, "season": season}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    r = requests.get(url, headers=HEADERS, params=params)
    return r.json()

def get_fixture_predictions(fixture_id: int):
    """Get pre-match predictions for a given fixture."""
    url = f"{FOOTBALL_API_URL}/predictions"
    params = {"fixture": fixture_id}
    r = requests.get(url, headers=HEADERS, params=params)
    
    try:
        return r.json()
    except Exception:
        return {"response": []}
    

def search_player(name: str, team: str = None):
    """Search for a player by name (and optionally team)"""
    url = f"{FOOTBALL_API_URL}/players"
    params = {"search": name}
    if team:
        params["team"] = team
    r = requests.get(url, headers=HEADERS, params=params)
    return r.json()

def get_player_stats(player_id: int, season: int):
    """Fetch player statistics for given season"""
    url = f"{FOOTBALL_API_URL}/players"
    params = {"id": player_id, "season": season}
    r = requests.get(url, headers=HEADERS, params=params)
    return r.json()