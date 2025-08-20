import football_api

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

    if position is None:
        return f"Não encontrei a posição do {team_name} em {season} na {league_name or 'liga'}."
    
    return f"O {team_name} terminou em {position}º lugar na {league_name or 'liga'} na época {season}."



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

    if comp_label:
        return f"{date}: {home} {g1} - {g2} {away} ({comp_label})"
    else:
        return f"{date}: {home} {g1} - {g2} {away}"



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
        print(f"DEBUG WIN PROBABILITY for fixture {f['fixture']['id']} ({f['teams']['home']['name']} vs {f['teams']['away']['name']}): {prob}")
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

    # Filter by what user asked (compact)
    event_lower = event.lower()
    filtered = [e for e in events if e.get("type", "").lower() == event_lower]

    if not filtered:
        event_pt = event_labels.get(event_lower, event.capitalize())
        return f"Não encontrei {event_pt} no jogo {team1} vs {team2}."

    # Format result
    out = []
    for e in filtered:
        minute = e.get("time", {}).get("elapsed")
        player = e.get("player", {}).get("name")
        team_name = e.get("team", {}).get("name")
        detail = e.get("detail")
        out.append(f"- {minute}': {player} ({team_name}) - {detail}")

    event_pt = event_labels.get(event_lower, event.capitalize())
    
    return f"{event_pt} no jogo {team1} vs {team2}:\n"


def handle_player_stats_intent(intent: dict):
    player_name = intent.get("player")
    season = intent.get("season")
    stats_requested = intent.get("stat")

    stat_labels = {
        "goals.total": "Golos",
        "goals.assists": "Assistências",
        "games.appearences": "Jogos",
        "games.minutes": "Minutos jogados",
        "shots.on": "Remates à baliza",
        "passes.key": "Passes-chave",
        "passes.accuracy": "Precisão de passe",
        "dribbles.success": "Dribles com sucesso",
        "cards.yellow": "Cartões amarelos",
        "cards.red": "Cartões vermelhos"
    }

    if not player_name:
        return "Não consegui identificar o jogador."

    # Default to current season if none given
    if not season:
        season = "2025/2026"
    season_start = int(season.split("/")[0])

    # Search player
    search_res = football_api.get_players(player_name=player_name)
    if not search_res.get("response"):
        return f"Não encontrei o jogador {player_name}."

    player = search_res["response"][0]["player"]
    player_id = player["id"]

    # Get stats for player and season
    stats_res = football_api.get_players(player_id=player_id, season=season_start)
    if not stats_res.get("response"):
        return f"Não encontrei estatísticas para {player_name} na época {season}."

    stats = stats_res["response"][0]["statistics"][0]  # usually one main entry

    # Flatten first league/team stats (API gives a list)
    statistics = stats[0].get("statistics", [])[0] if stats[0].get("statistics") else {}

    # Filter only requested stats
    out = []
    for stat in stats_requested:
        # assume stat is normalized by LLM (like "goals.total", "passes.key", "shots.on")
        keys = stat.split(".")
        value = statistics
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, None)
            else:
                value = None
        label = stat_labels.get(stat, stat)
        if value is not None:
            out.append(f"- {label}: {value}")
        else:
            out.append(f"- {label}: não disponível")

    return f"Estatísticas de {player_name} em {season}:\n" + "\n".join(out)