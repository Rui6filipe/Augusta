import football_api
import unicodedata


def get_league_info_from_competition(competition):
    """Given a competition name, returns (league_id, league_name) if found, else (None, None)."""
    if not competition:
        return None, None
    for _, league in football_api.LEAGUES.items():
        if competition.lower() == league["name"].lower():
            return league["id"], league["name"]
    return None, None

def handle_team_standing_intent(intent: dict):
    team_name = intent.get("team1")
    season = intent.get("season")
    competition = intent.get("competition")

    if not team_name:
        return "Não consegui identificar a equipa."

    if not season:
        season = "2025/2026"

    # Search team
    team_res = football_api.search_team(team_name)
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
    t2 = football_api.search_team(team2)
    if not t1.get("response") or not t2.get("response"):
        return "Não encontrei uma das equipas."

    id1 = t1["response"][0]["team"]["id"]
    id2 = t2["response"][0]["team"]["id"]

    # Map competition name to league id if specified

    league_id, comp_label = get_league_info_from_competition(competition)

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
            for f in fixtures_with_prob
        ]
    }


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



def handle_match_events_intent(intent: dict):
    team1 = intent.get("team1")
    team2 = intent.get("team2")
    season = intent.get("season")
    competition = intent.get("competition")
    event = intent.get("event")

    event_labels = {
        "goal": "Golos",
        "card": "Cartões",
        "subst": "Substituições",
        "var": "VAR",
        "incident": "Incidentes"
    }

    if not team1 or not team2:
        return "Não consegui identificar as equipas do jogo."

    if not season:
        season = "2025/2026"

    # Search teams to get IDs
    t1_res = football_api.search_team(team1)
    t2_res = football_api.search_team(team2)
    if not t1_res.get("response") or not t2_res.get("response"):
        return "Não encontrei uma das equipas."

    id1 = t1_res["response"][0]["team"]["id"]
    id2 = t2_res["response"][0]["team"]["id"]

    # Map competition name to league id if specified
    league_id, _ = get_league_info_from_competition(competition)

    # Get fixture id for the match
    fixtures_res = football_api.get_match_result(id1, id2, season.split("/")[0], league_id)
    if not fixtures_res.get("response"):
        return f"Não encontrei o jogo entre {team1} e {team2} em {season}."
    
    fixture_id = fixtures_res["response"][0]["fixture"]["id"]

    # Get events for that fixture
    events_res = football_api.get_fixture_events(fixture_id)
    events = events_res.get("response", [])

    # Support event as list or string (compact)
    event_types = event if isinstance(event, list) else [event] if isinstance(event, str) else []


    filtered_events = {}
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

    elif team_name:
        # Use team if no competition
        team_info = football_api.search_team(team_name)
        if not team_info.get("response"):
            return f"Não encontrei a equipa {team_name}."
        team_id = team_info["response"][0]["team"]["id"]
        search_res = football_api.get_player_stats(player_name=player_name, season=season_start, team=team_id)

    else:
        # Fallback → search by profiles using last name
        lastname = player_name.split()[-1]
        profiles_res = football_api.get_player_profiles(lastname)
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