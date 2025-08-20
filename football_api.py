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
