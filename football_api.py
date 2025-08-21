import os
from dotenv import load_dotenv
import requests

load_dotenv()

FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY")
FOOTBALL_API_URL = os.environ.get("FOOTBALL_API_URL")

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
    """
    Search for a team by name.
    """
    url = f"{FOOTBALL_API_URL}/teams"
    params = {"search": name}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        return r.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {e}", "response": []}

def get_team_standings(league_id: int, season: int):
    """
    Get the standings for a specific league and season.
    """
    url = f"{FOOTBALL_API_URL}/standings"
    params = {"league": league_id, "season": season}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        return r.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {e}", "response": []}

def get_match_result(team1: str, team2: str, season: int, league_id: int):
    """
    Search for a specific match result.
    """
    url = f"{FOOTBALL_API_URL}/fixtures/headtohead"
    params = {"h2h": f"{team1}-{team2}", "season": season}
    if league_id is not None:
        params["league"] = league_id
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        return r.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {e}", "response": []}

def get_team_fixtures(team_id: int, season: int, from_date: str = None, to_date: str = None):
    """
    Get fixtures for a team by date range.
    """
    url = f"{FOOTBALL_API_URL}/fixtures"
    params = {"team": team_id, "season": season}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        return r.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {e}", "response": []}

def get_fixture_predictions(fixture_id: int):
    """
    Get pre-match predictions for a given fixture.
    """
    url = f"{FOOTBALL_API_URL}/predictions"
    params = {"fixture": fixture_id}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        return r.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {e}", "response": []}
    except Exception:
        return {"response": []}
    
def get_fixture_events(fixture_id: int, team_id: int = None, player_id: int = None):
    """
    Fetch events for a specific fixture.
    """
    url = f"{FOOTBALL_API_URL}/fixtures/events"
    params = {"fixture": fixture_id}
    if team_id:
        params["team"] = team_id
    if player_id:
        params["player"] = player_id
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        return r.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {e}", "response": []}


def get_player_profiles(lastname: str, page: int = 1):
    """
    Fetch players by last name using the /players/profiles endpoint.
    """
    url = f"{FOOTBALL_API_URL}/players/profiles"
    params = {"search": lastname, "page": page}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        return r.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {e}", "response": []}

def get_player_stats(player_name: str = None, player_id: int = None, season: int = None, league: int = None, team: int = None):
    """
    Fetch player statistics by name or ID, optionally filtered by season, league, or team.
    """
    url = f"{FOOTBALL_API_URL}/players"
    params = {}
    if player_name:
        params["search"] = player_name
    if player_id:
        params["id"] = player_id
    if season:
        params["season"] = int(season)
    if league:
        params["league"] = int(league)
    if team:
        params["team"] = int(team)
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        return r.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {e}", "response": []}