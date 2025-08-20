import requests
from config import FOOTBALL_API_KEY, FOOTBALL_API_URL

HEADERS = {"x-apisports-key": FOOTBALL_API_KEY}

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
