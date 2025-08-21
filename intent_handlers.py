import football_api
import unicodedata

def get_league_info_from_competition(competition):
    """
    Given a competition name, returns (league_id, league_name) if found, else (None, None).
    """
    if not competition:
        return None, None
    for _, league in football_api.LEAGUES.items():
        if competition.lower() == league["name"].lower():
            return league["id"], league["name"]
    return None, None

def handle_team_standing_intent(intent: dict):
    """
    Handles the intent to retrieve a team's standing in a league or competition for a given season.
    If the user does not provide a season, the function assumes the current season (2025/2026).
    Returns a dictionary with team, season, competition, league, position, and country, or a user-friendly error message.
    """
    team_name = intent.get("team1")
    season = intent.get("season")
    competition = intent.get("competition")

    if not team_name:
        return "Não consegui identificar a equipa."

    if not season:
        season = "2025/2026"

    # Search team
    team_res = football_api.search_team(team_name)
    if "error" in team_res:
        return "Ocorreu um erro de rede ao aceder aos dados de futebol. Tente novamente mais tarde."
    if not team_res.get("response"):
        return f"Não encontrei a equipa {team_name}."

    team = team_res["response"][0]["team"]
    team_id = team["id"]
    country = team.get("country", "").lower()

    # Determine if user wants a European competition

    league_id, league_name = get_league_info_from_competition(competition)

    # If no league found from competition, default to national league
    if not league_id:
        league_id = football_api.LEAGUES.get(country, {}).get("id")
        league_name = football_api.LEAGUES.get(country, {}).get("name")

    # Get standings
    standings_res = football_api.get_team_standings(league_id, season.split("/")[0])
    if "error" in standings_res:
        return "Ocorreu um erro de rede ao aceder aos dados de futebol. Tente novamente mais tarde."
    if not standings_res.get("response"):
        return f"Não encontrei classificações para {team_name} em {season}."

    standings = standings_res["response"][0]["league"]["standings"][0]

    position = None
    for row in standings:
        if row["team"]["id"] == team_id:
            position = row["rank"]
            break

    return {
        "team": team_name,
        "season": season,
        "competition": competition,
        "league": league_name,
        "position": position,
        "country": country
    }


def handle_match_result_intent(intent: dict):
    """
    Handles the intent to retrieve the result of a match between two teams for a given season and competition.
    - If the user does not provide a season, the function assumes the current season (2025/2026).
    - If the user provides a competition, the function tries to map it to a league ID; if not found or not provided, the search is performed across all competitions.
    Returns a dictionary with match details or a user-friendly error message.
    """
    team1 = intent.get("team1")
    team2 = intent.get("team2")
    season = intent.get("season")
    competition = intent.get("competition")

    if not team1 or not team2:
        return "Não consegui identificar as equipas."

    if not season:
        season = "2025/2026"

    # Search teams to get IDs
    t1 = football_api.search_team(team1)
    if "error" in t1:
        return "Ocorreu um erro de rede ao aceder aos dados de futebol. Tente novamente mais tarde."
    t2 = football_api.search_team(team2)
    if "error" in t2:
        return "Ocorreu um erro de rede ao aceder aos dados de futebol. Tente novamente mais tarde."
    if not t1.get("response") or not t2.get("response"):
        return "Não encontrei uma das equipas."

    id1 = t1["response"][0]["team"]["id"]
    id2 = t2["response"][0]["team"]["id"]

    # Map competition name to league id if specified

    league_id, comp_label = get_league_info_from_competition(competition)

    # If no competition specified or not found, league_id remains None and will be omitted from API call
    match_res = football_api.get_match_result(id1, id2, season.split("/")[0], league_id)
    if "error" in match_res:
        return "Ocorreu um erro de rede ao aceder aos dados de futebol. Tente novamente mais tarde."
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

    return {
        "team1": team1,
        "team2": team2,
        "season": season,
        "competition": competition,
        "date": date,
        "home": home,
        "away": away,
        "goals_home": g1,
        "goals_away": g2,
        "competition_label": comp_label
    }


def handle_team_fixtures_intent(intent: dict):
    """
    Handles the intent to retrieve a team's fixtures (matches) for a given season and period.
    - If the user does not provide a season, the function assumes the current season (2025/2026).
    - If fixture_period is not specified, all fixtures for the season are returned.
    - If fixture_type is not specified, all fixtures are returned sorted by date.
    - If fixture_type is "hardest" or "easiest", only fixtures with win probability are returned, sorted by lowest or highest win probability, respectively.
    Returns a dictionary with team, season, fixture type, fixture period, and a list of fixtures (with date, teams, league, and win probability), or a user-friendly error message.
    """
    team_name = intent.get("team1")
    season = intent.get("season")
    fixture_period = intent.get("fixture_period")
    fixture_type = intent.get("fixture_type")  # "hardest" or "easiest"

    if not team_name or not season:
        return "Não consegui identificar a equipa ou a época."

    # Search team
    team_res = football_api.search_team(team_name)
    if "error" in team_res:
        return "Ocorreu um erro de rede ao aceder aos dados de futebol. Tente novamente mais tarde."
    if not team_res.get("response"):
        return f"Não encontrei a equipa {team_name}."

    team = team_res["response"][0]["team"]
    team_id = team["id"]

    # Handle fixture_period: if not specified, fetch all fixtures for the season
    from_date, to_date = None, None
    if fixture_period and fixture_period.get("start") and fixture_period.get("end"):
        from_date = fixture_period["start"][:10]
        to_date = fixture_period["end"][:10]

    fixtures_res = football_api.get_team_fixtures(team_id, season.split("/")[0], from_date=from_date, to_date=to_date)
    if "error" in fixtures_res:
        return "Ocorreu um erro de rede ao aceder aos dados de futebol. Tente novamente mais tarde."
    fixtures = fixtures_res.get("response", [])
    if not fixtures:
        return f"Não encontrei jogos para o {team_name} em {season}."

    # Annotate fixtures with win probability (if available)
    for f in fixtures:
        prob = compute_difficulty(f, team_name)
        if prob is not None:
            f["win_probability"] = prob
        else:
            f["win_probability"] = None

    # Handle fixture_type: if not specified, return all fixtures sorted by date
    fixtures_to_return = fixtures
    if fixture_type == "hardest":
        fixtures_to_return = [f for f in fixtures if f["win_probability"] is not None]
        fixtures_to_return.sort(key=lambda x: x["win_probability"])
    elif fixture_type == "easiest":
        fixtures_to_return = [f for f in fixtures if f["win_probability"] is not None]
        fixtures_to_return.sort(key=lambda x: x["win_probability"], reverse=True)
    else:
        # No fixture_type: sort all fixtures by date
        fixtures_to_return.sort(key=lambda x: x["fixture"]["date"])

    if fixture_type in ("hardest", "easiest") and not fixtures_to_return:
        return f"Não há jogos com probabilidade prevista para o {team_name} em {season}."

    return {
        "team": team_name,
        "season": season,
        "fixture_type": fixture_type,
        "fixture_period": fixture_period,
        "fixtures": [
            {
                "date": f["fixture"]["date"],
                "home": f["teams"]["home"]["name"],
                "away": f["teams"]["away"]["name"],
                "league": f["league"]["name"],
                "win_probability": f.get("win_probability")
            }
            for f in fixtures_to_return
        ]
    }


def compute_difficulty(fixture, team_name):
    """
    Computes the win probability for the given team in a specific fixture using prediction data from the API.
    - If prediction data is unavailable or an error occurs, returns None.
    - team_name is matched against the home and away teams to select the correct probability.
    Returns a float between 0 and 1 representing the win probability, or None if not available.
    """
    fixture_id = fixture["fixture"]["id"]
    pred_res = football_api.get_fixture_predictions(fixture_id)
    if "error" in pred_res:
        return None
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



def handle_match_events_intent(intent: dict):
    """
    Handles the intent to retrieve specific events (e.g., goals, cards, substitutions) from a match between two teams for a given season and competition.
    - If the user does not provide a season, the function assumes the current season (2025/2026).
    - If the user does not specify event types, no events are returned.
    - If the user provides a competition, the function tries to map it to a league ID; if not found or not provided, the search is performed across all competitions.
    - Returns a dictionary with teams, season, competition, event types, and filtered events, or a user-friendly error message.
    """
    team1 = intent.get("team1")
    team2 = intent.get("team2")
    season = intent.get("season")
    competition = intent.get("competition")
    event = intent.get("event")

    if not team1 or not team2:
        return "Não consegui identificar as equipas do jogo."

    if not season:
        season = "2025/2026"

    # Search teams to get IDs
    t1_res = football_api.search_team(team1)
    if "error" in t1_res:
        return "Ocorreu um erro de rede ao aceder aos dados de futebol. Tente novamente mais tarde."
    t2_res = football_api.search_team(team2)
    if "error" in t2_res:
        return "Ocorreu um erro de rede ao aceder aos dados de futebol. Tente novamente mais tarde."
    if not t1_res.get("response") or not t2_res.get("response"):
        return "Não encontrei uma das equipas."

    id1 = t1_res["response"][0]["team"]["id"]
    id2 = t2_res["response"][0]["team"]["id"]

    # Map competition name to league id if specified
    league_id, _ = get_league_info_from_competition(competition)

    # Get fixture id for the match
    fixtures_res = football_api.get_match_result(id1, id2, season.split("/")[0], league_id)
    if "error" in fixtures_res:
        return "Ocorreu um erro de rede ao aceder aos dados de futebol. Tente novamente mais tarde."
    if not fixtures_res.get("response"):
        return f"Não encontrei o jogo entre {team1} e {team2} em {season}."
    fixture_id = fixtures_res["response"][0]["fixture"]["id"]

    # Get events for that fixture
    events_res = football_api.get_fixture_events(fixture_id)
    if "error" in events_res:
        return "Ocorreu um erro de rede ao aceder aos dados de futebol. Tente novamente mais tarde."
    events = events_res.get("response", [])

    # Support event as list or string (compact)
    if event is None:
        # No event specified: return all events grouped by type
        event_types = sorted(set(e.get("type", "") for e in events if e.get("type")))
    else:
        event_types = event if isinstance(event, list) else [event] if isinstance(event, str) else []

    filtered_events = {}
    if not event_types:
        # No event types: return all events as a flat list
        filtered_events["all"] = [
            {
                "minute": e.get("time", {}).get("elapsed"),
                "team": e.get("team", {}).get("name"),
                "player": e.get("player", {}).get("name"),
                "detail": e.get("detail"),
                "type": e.get("type")
            }
            for e in events
        ]
    else:
        for ev in event_types:
            event_lower = ev.lower()
            filtered = [
                {
                    "minute": e.get("time", {}).get("elapsed"),
                    "team": e.get("team", {}).get("name"),
                    "player": e.get("player", {}).get("name"),
                    "detail": e.get("detail")
                }
                for e in events if e.get("type", "").lower() == event_lower
            ]
            filtered_events[ev] = filtered

    return {
        "team1": team1,
        "team2": team2,
        "season": season,
        "competition": competition,
        "event_types": event_types,
        "events": filtered_events
    }


def handle_player_stats_intent(intent: dict):
    """
    Handles the intent to retrieve statistics for a specific player for a given season, competition, and/or team.
    - If the user does not provide a season, the function assumes the current season (2025/2026).
    - If the user provides a competition, the function tries to map it to a league ID; if not found or not provided, the search is performed by team (if provided) or by player name.
    - If the user provides a team name, the function searches for the player within that team for the given season.
    - If neither competition nor team is provided, the function searches by player name across all teams.
    - If multiple players match the query, the function asks for clarification.
    - If a team or competition is specified, the statistics returned are only for that team or competition; otherwise, the statistics are the sum across all teams/competitions for the player in that season.
    Returns a dictionary with player, season, team, competition, requested stats, and statistics, or a user-friendly error message.
    """

    player_name = intent.get("player")
    season = intent.get("season")
    stats_requested = intent.get("stat")
    competition = intent.get("competition")
    team_name = intent.get("team1")

    if not player_name:
        return "Não consegui identificar o jogador."

    # Default to current season if none given
    if not season:
        season = "2025/2026"
    season_start = int(season.split("/")[0])

    search_res = None
    player_id = None

    if competition:
        # Use league/competition
        league_id, _ = get_league_info_from_competition(competition)
        if not league_id:
            return f"Não reconheço a competição {competition}."
        search_res = football_api.get_player_stats(player_name=player_name, season=season_start, league=league_id)
        if "error" in search_res:
            return "Ocorreu um erro de rede ao aceder aos dados de futebol. Tente novamente mais tarde."

    elif team_name:
        # Use team if no competition
        team_info = football_api.search_team(team_name)
        if "error" in team_info:
            return "Ocorreu um erro de rede ao aceder aos dados de futebol. Tente novamente mais tarde."
        if not team_info.get("response"):
            return f"Não encontrei a equipa {team_name}."
        team_id = team_info["response"][0]["team"]["id"]
        search_res = football_api.get_player_stats(player_name=player_name, season=season_start, team=team_id)
        if "error" in search_res:
            return "Ocorreu um erro de rede ao aceder aos dados de futebol. Tente novamente mais tarde."

    else:
        # Fallback → search by profiles using last name
        lastname = player_name.split()[-1]
        profiles_res = football_api.get_player_profiles(lastname)
        if "error" in profiles_res:
            return "Ocorreu um erro de rede ao aceder aos dados de futebol. Tente novamente mais tarde."
        candidates = profiles_res.get("response", [])

        if not candidates:
            return f"Não encontrei o jogador {player_name}."

        # Try exact full-name match
        for c in candidates:
            if c["player"]["name"].lower() == player_name.lower():
                player_id = c["player"]["id"]
                break

        # If no exact match, pick the first candidate
        if not player_id and len(candidates) == 1:
            player_id = candidates[0]["player"]["id"]

        # If multiple candidates, ask for clarification (normalize accents, compare first/last names)
        if not player_id:
            # Compact normalization and first/last extraction
            norm = lambda s: ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if c.isalnum() or c.isspace())
            get_first_last = lambda name: (name.strip().split()[0], name.strip().split()[-1]) if name.strip() else ('','')
            query_first, query_last = get_first_last(norm(player_name))
            filtered = [c for c in candidates if get_first_last(norm(c["player"]["name"])) == (query_first, query_last)]
            if len(filtered) == 1:
                player_id = filtered[0]["player"]["id"]
            else:
                if filtered:
                    names = [c["player"]["name"] for c in filtered[:5]]
                else:
                    names = [c["player"]["name"] for c in candidates[:5]]
                return f"Encontrei vários jogadores chamados {lastname}: {', '.join(names)}. Qual deles pretende?"

        # Now get stats by player_id
        search_res = football_api.get_player_stats(player_id=player_id, season=season_start)
        if "error" in search_res:
            return "Ocorreu um erro de rede ao aceder aos dados de futebol. Tente novamente mais tarde."

    player_stats = search_res.get("response", []) if search_res else []
    if not player_stats:
        return f"Não encontrei estatísticas para {player_name} na época {season}."

    # Take first player
    player_data = player_stats[0]
    statistics = player_data.get("statistics", [])
    if not statistics:
        return f"Não encontrei estatísticas para {player_name} na época {season}."

    return {
        "player": player_name,
        "season": season,
        "team": team_name,
        "competition": competition,
        "stats_requested": stats_requested,
        "statistics": statistics
    }