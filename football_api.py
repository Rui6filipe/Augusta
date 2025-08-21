import os
from dotenv import load_dotenv
import diskcache as dc
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

# Note on caching:
# Some endpoints (get_team_standings, get_match_result, get_fixture_events, get_player_stats, get_fixture_odds) are NOT cached.
# This is because users may expect real-time or near real-time data for these endpoints (e.g., live scores, stats, or events).
#
# A possible solution: only cache data for past seasons (not the current season),
# and always fetch fresh data for the current season. This would reduce API calls for historical queries
# while keeping live data accurate.
#
# For better scalability and real-time needs, consider using a distributed cache like Redis, 
# which supports cache invalidation and sharing across multiple servers.

# Persistent cache stored in ./cache folder
_cache = dc.Cache("cache")

def cache_get(key: str):
    """
    Get cached value if not expired (diskcache handles expiration).
    """
    value = _cache.get(key)
    return value

def cache_set(key: str, value, ttl: int):
    """
    Store value in cache with expiration.
    """
    _cache.set(key, value, expire=ttl)


def normalize_key(s: str) -> str:
    """
    Key normalization for cache safety.
    """
    return str(s).strip().lower().replace(" ", "_")


def fetch_from_api(url, headers, params, timeout=5):
    """
    Fetch data from the API using requests with a simple timeout.
    """
    try:
        r = requests.get(url, headers=headers, params=params, timeout=timeout)
        return r.json()
    except Exception as e:
        return {"error": str(e), "response": []}


def search_team(name: str):
    """
    Search for a team by name.
    """
    cache_key = f"team:{normalize_key(name)}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    url = f"{FOOTBALL_API_URL}/teams"
    params = {"search": name}
    data = fetch_from_api(url, HEADERS, params)
    if data and not data.get("error") and data.get("response"):
        cache_set(cache_key, data, 30 * 24 * 3600)  # 30 days
    return data

def get_team_standings(league_id: int, season: int):
    """
    Get the standings for a specific league and season.
    """
    url = f"{FOOTBALL_API_URL}/standings"
    params = {"league": league_id, "season": season}
    data = fetch_from_api(url, HEADERS, params)
    return data

def get_match_result(team1: str, team2: str, season: int, league_id: int):
    """
    Search for a specific match result.
    """
    url = f"{FOOTBALL_API_URL}/fixtures/headtohead"
    params = {"h2h": f"{team1}-{team2}", "season": season}
    if league_id is not None:
        params["league"] = league_id
    data = fetch_from_api(url, HEADERS, params)
    return data

def get_team_fixtures(team_id: int, season: int, from_date: str = None, to_date: str = None):
    """
    Get fixtures for a team by date range.
    """
    cache_key = f"fixtures:{team_id}:{season}:{normalize_key(from_date) if from_date else ''}:{normalize_key(to_date) if to_date else ''}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{FOOTBALL_API_URL}/fixtures"
    params = {"team": team_id, "season": season}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    data = fetch_from_api(url, HEADERS, params)
    if data and not data.get("error") and data.get("response"):
        cache_set(cache_key, data, 86400)  # 1 day
    return data

def get_fixture_predictions(fixture_id: int):
    """
    Get pre-match predictions for a given fixture.
    """
    cache_key = f"predictions:{fixture_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{FOOTBALL_API_URL}/predictions"
    params = {"fixture": fixture_id}
    data = fetch_from_api(url, HEADERS, params)
    if data and not data.get("error") and data.get("response"):
        cache_set(cache_key, data, 300)  # 5 minutes
    return data
    
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
    data = fetch_from_api(url, HEADERS, params)
    return data


def get_player_profiles(lastname: str, page: int = 1):
    """
    Fetch players by last name using the /players/profiles endpoint.
    """
    cache_key = f"player_profiles:{normalize_key(lastname)}:{page}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    url = f"{FOOTBALL_API_URL}/players/profiles"
    params = {"search": lastname, "page": page}
    data = fetch_from_api(url, HEADERS, params)
    if data and not data.get("error") and data.get("response"):
        cache_set(cache_key, data, 604800)  # 1 week
    return data

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
    data = fetch_from_api(url, HEADERS, params)
    return data

def get_coach(coach_id: int = None, team_id: int = None, search: str = None):
    """
    Fetch coach information by coach ID, team ID, or name search.
    """
    cache_key = f"coach:{coach_id}:{team_id}:{normalize_key(search) if search else ''}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    url = f"{FOOTBALL_API_URL}/coachs"
    params = {}
    if coach_id:
        params["id"] = coach_id
    if team_id:
        params["team"] = team_id
    if search:
        params["search"] = search
    data = fetch_from_api(url, HEADERS, params)
    if data and not data.get("error") and data.get("response"):
        cache_set(cache_key, data, 7 * 24 * 3600)  # 7 days
    return data

def get_venue(search: str = None, venue_id: int = None):
    """
    Fetch venue information by ID, search string, or city.
    """
    # Cache: 30 days
    cache_key = f"venue:{venue_id}:{normalize_key(search) if search else ''}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    url = f"{FOOTBALL_API_URL}/venues"
    params = {}
    if search:
        params["search"] = search
    if venue_id:
        params["id"] = venue_id
    data = fetch_from_api(url, HEADERS, params)
    if data and not data.get("error") and data.get("response"):
        cache_set(cache_key, data, 30 * 24 * 3600) # 30 days
    return data


def get_fixture_odds(fixture_id: int):
    """
    Fetch betting odds for a specific fixture.
    Optionally filter by bookmaker or bet type (rarely needed for main chatbot use cases).
    """
    url = f"{FOOTBALL_API_URL}/odds"
    params = {"fixture": fixture_id}
    data = fetch_from_api(url, HEADERS, params)
    return data