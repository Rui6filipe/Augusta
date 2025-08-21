import os
from dotenv import load_dotenv
import diskcache as dc
from multiprocessing import Process, Queue

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
# Some endpoints (get_team_standings, get_match_result, get_fixture_events, get_player_stats) are NOT cached.
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
    """Get cached value if not expired (diskcache handles expiration)."""
    value = _cache.get(key)
    return value

def cache_set(key: str, value, ttl: int):
    """Store value in cache with expiration."""
    _cache.set(key, value, expire=ttl)

# Key normalization for cache safety
def normalize_key(s: str) -> str:
    return str(s).strip().lower().replace(" ", "_")


# The requests library's timeout is not always strict (e.g., DNS hangs, network stalls),
# especially on Windows. Threads can't interrupt blocking C calls, so thread-based timeouts are unreliable.
# By using multiprocessing, we can forcefully terminate API calls that exceed our timeout, guaranteeing no call runs too long.

def _fetch_worker(url, headers, params, timeout, q):
    import requests
    try:
        r = requests.get(url, headers=headers, params=params, timeout=timeout)
        q.put(r.json())
    except Exception as e:
        q.put({"error": str(e), "response": []})

def fetch_with_hard_timeout(url, headers, params, timeout=3, total_timeout=5):
    q = Queue()
    p = Process(target=_fetch_worker, args=(url, headers, params, timeout, q))
    p.start()
    p.join(total_timeout)
    if p.is_alive():
        p.terminate()
        p.join()
        return {"error": f"Request timed out after {total_timeout} seconds", "response": []}
    return q.get()


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
    data = fetch_with_hard_timeout(url, HEADERS, params, timeout=3, total_timeout=5)
    cache_set(cache_key, data, 30 * 24 * 3600)  # 30 days
    return data

def get_team_standings(league_id: int, season: int):
    """
    Get the standings for a specific league and season.
    """
    url = f"{FOOTBALL_API_URL}/standings"
    params = {"league": league_id, "season": season}
    data = fetch_with_hard_timeout(url, HEADERS, params, timeout=3, total_timeout=5)
    return data

def get_match_result(team1: str, team2: str, season: int, league_id: int):
    """
    Search for a specific match result.
    """
    url = f"{FOOTBALL_API_URL}/fixtures/headtohead"
    params = {"h2h": f"{team1}-{team2}", "season": season}
    if league_id is not None:
        params["league"] = league_id
    data = fetch_with_hard_timeout(url, HEADERS, params, timeout=3, total_timeout=5)
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
    data = fetch_with_hard_timeout(url, HEADERS, params, timeout=3, total_timeout=5)
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
    data = fetch_with_hard_timeout(url, HEADERS, params, timeout=3, total_timeout=5)
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
    data = fetch_with_hard_timeout(url, HEADERS, params, timeout=3, total_timeout=5)
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
    data = fetch_with_hard_timeout(url, HEADERS, params, timeout=3, total_timeout=5)
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
    data = fetch_with_hard_timeout(url, HEADERS, params, timeout=3, total_timeout=5)
    return data